"""掉线短信自动登录：管理器（状态机 / 冷却 / 并发锁 / 热生效）。

设计要点（务必保留，均为踩坑后的约束）：
1. 绝不阻塞 Coordinator 刷新链：等待用户填码是跨时间的两段式，
   发码走后台任务，验证由 text 实体写入时触发。
2. 不修改 coordinator.py：用 DataUpdateCoordinator 监听器感知每轮刷新后的
   data_mode，做到对上游文件零侵入。
3. 与 Coordinator 共用 hass.data[DOMAIN]["auth_lock"]：短信发码会
   initialize(force_new_uuid=True) 重建加密会话，若与 refresh_access_token
   交错会互相污染 _key_code / public_key。
4. 离线判定必须叠加「已完成至少一次刷新」（coordinator.data is not None）：
   coordinator._data_mode 初值就是 local_cache，否则 HA 每次启动都会误发短信。

日志级别约定（HA 日志面板会把自定义集成的 WARNING 及以上列为「此错误来自自定义集成」）：
  INFO    正常流程与预期内可恢复的情况（下发验证码、登录成功、手动触发、因网络不可达跳过自动发码等）
  WARNING 需要用户介入的用户侧失败（验证码错误、等待超时）——消耗了短信
  ERROR   连续失败达上限锁定
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Callable, Coroutine

from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState  # type: ignore[import-untyped]
from homeassistant.core import HomeAssistant, callback

from ..const import CONF_AUTH_TOKEN, CONF_LOGIN_ACCOUNT, DOMAIN
from .const import (
    CODE_RESEND_COOLDOWN_SECONDS,
    CODE_WAIT_TIMEOUT_SECONDS,
    CONF_AUTO_LOGIN,
    CONF_SMS_PHONE,
    DATA_AUTO_LOGIN,
    DATA_MODE_LOCAL_CACHE,
    ERROR_REASON_NETWORK,
    MAX_CONSECUTIVE_FAILURES,
    PHONE_PATTERN,
    AutoLoginState,
)
from .driver import (
    SmsLoginDriver,
    build_driver,
    driver_name,
    effective_account,
    phone_source,
)
from .naming import build_object_id

_LOGGER = logging.getLogger(__name__)

# 两次「成功登录」之间的最小间隔：防止服务端会话未即时生效时
# 每轮刷新（10 分钟）都重复发码。用户要求「登录成功后冷却重置」，
# 这里只约束「成功 → 立即又触发」的异常路径。
MIN_RELOGIN_INTERVAL_SECONDS = 600


def _mask_account(account: str) -> str:
    """手机号脱敏（日志不出现完整号码）。"""
    if len(account) >= 7:
        return f"{account[:3]}****{account[-3:]}"
    return "***" if account else "(未配置)"


def _iso(ts: float | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts).isoformat(timespec="seconds")


class AutoLoginManager:
    """掉线短信自动登录管理器（每个 ConfigEntry 一套）。"""

    def __init__(self, hass: HomeAssistant, entry: Any, coordinator: Any) -> None:
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self._db = getattr(coordinator, "db", None)

        self._enabled = bool(entry.data.get(CONF_AUTO_LOGIN, False))
        self._state = AutoLoginState.IDLE if self._enabled else AutoLoginState.DISABLED
        self._failures = 0
        self._last_code_sent_at: float | None = None
        self._wait_deadline: float | None = None
        self._last_error: str | None = None
        self._last_login_at: float | None = None
        self._retry_pending = False
        self._driver: SmsLoginDriver | None = None
        # 中转后端不可达时首次告警、后续降级为 DEBUG，避免每轮刷新刷屏
        self._send_fail_logged = False
        self._network_skip_logged = False
        # 记录是否观察到过离线，用于恢复到在线时清掉「认证已过期」的残留提示
        self._saw_offline = False

        self._entities: dict[str, Any] = {}
        self._tasks: set[asyncio.Task] = set()
        self._unsubs: list[Callable[[], None]] = []
        self._lock: asyncio.Lock | None = None
        self._timeout_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # 装配 / 卸载
    # ------------------------------------------------------------------

    async def async_setup(self) -> None:
        """装配监听（必须在平台转发之前调用，实体创建时要能取到管理器）。"""
        self._unsubs.append(self.coordinator.async_add_listener(self._handle_coordinator_update))
        # 旧版 HA 的 add_update_listener 可能不返回注销句柄，因此本回调内部
        # 额外做了「是否为当前管理器」判定，避免重载后旧实例继续生效（见 _is_current）
        unsub = self.entry.add_update_listener(self._async_handle_entry_update)
        if callable(unsub):
            self._unsubs.append(unsub)
        self.entry.async_on_unload(self._shutdown)
        _LOGGER.info(
            "[自动登录] 已装配：户号 %s，开关 %s，数据源 %s，实体 %s.%s_auto_login / %s.%s_code",
            build_object_id(self.entry, self.coordinator) or "未知",
            "开" if self._enabled else "关",
            driver_name(self.coordinator.api),
            "switch",
            build_object_id(self.entry, self.coordinator),
            "text",
            build_object_id(self.entry, self.coordinator),
        )

    @callback
    def _shutdown(self) -> None:
        """卸载：注销监听并取消后台任务（ConfigEntry.async_on_unload 回调）。"""
        for unsub in self._unsubs:
            try:
                unsub()
            except Exception:  # noqa: BLE001 注销失败不阻断卸载
                pass
        self._unsubs.clear()
        for task in list(self._tasks):
            task.cancel()
        self._tasks.clear()
        store = self.hass.data.get(DOMAIN)
        if isinstance(store, dict):
            entry_store = store.get(self.entry.entry_id)
            if isinstance(entry_store, dict) and entry_store.get(DATA_AUTO_LOGIN) is self:
                entry_store.pop(DATA_AUTO_LOGIN, None)
        _LOGGER.debug("[自动登录] 已卸载")

    def _spawn(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
        """创建后台任务并登记（卸载时统一取消）。"""
        task = self.hass.async_create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def _auth_lock(self) -> asyncio.Lock:
        """复用集成全局认证锁（与 Coordinator 的 token 刷新串行化）。"""
        store = self.hass.data.setdefault(DOMAIN, {})
        lock = store.get("auth_lock")
        if lock is None:
            lock = asyncio.Lock()
            store["auth_lock"] = lock
        return lock

    # ------------------------------------------------------------------
    # 实体注册
    # ------------------------------------------------------------------

    @callback
    def add_entity(self, entity: Any, kind: str) -> None:
        """实体 async_added_to_hass 时注册。"""
        self._entities[kind] = entity

    @callback
    def remove_entity(self, entity: Any, kind: str) -> None:
        """实体移除时注销。"""
        if self._entities.get(kind) is entity:
            self._entities.pop(kind, None)

    @callback
    def _notify_entities(self) -> None:
        for entity in list(self._entities.values()):
            if getattr(entity, "hass", None) is None:
                continue
            entity.async_write_ha_state()

    # ------------------------------------------------------------------
    # 对外状态
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self._enabled

    @callback
    def _rest_state(self) -> AutoLoginState:
        """回到待命状态（开关关闭时为 disabled，开关开启时为 idle）。"""
        return AutoLoginState.IDLE if self._enabled else AutoLoginState.DISABLED

    @property
    def state(self) -> AutoLoginState:
        return self._state

    @property
    def sms_phone(self) -> str:
        """用户指定的短信接收手机号（空 = 跟随登录账号）。"""
        return str(self.entry.data.get(CONF_SMS_PHONE) or "").strip()

    @property
    def effective_phone(self) -> str:
        """当前实际用于接收短信的号码（明文，仅内部使用）。"""
        return effective_account(self.coordinator.api, self.entry)

    async def async_set_sms_phone(self, value: str) -> None:
        """设置短信接收手机号（空字符串 = 恢复跟随登录账号）。"""
        phone = (value or "").strip()
        if phone and not PHONE_PATTERN.fullmatch(phone):
            raise ValueError("手机号格式不正确：应为 11 位、以 1 开头的数字；留空表示跟随登录账号")
        if phone == self.sms_phone:
            return
        self.hass.config_entries.async_update_entry(
            self.entry, data={**self.entry.data, CONF_SMS_PHONE: phone}
        )
        _LOGGER.info(
            "[自动登录] 短信接收手机号已%s",
            f"设置为 {_mask_account(phone)}" if phone else "清空（改为跟随登录账号）",
        )
        # 号码变了：上一次的验证码已发往旧号码，作废当前等待窗口并放开冷却，便于立即重新触发
        if self._state == AutoLoginState.WAITING_CODE:
            self._cancel_wait_timeout()
            self._driver = None
            self._wait_deadline = None
            self._state = self._rest_state()
            self._clear_code_entity()
        self._last_code_sent_at = None
        self._last_error = None
        self._notify_entities()

    @callback
    def snapshot(self) -> dict[str, Any]:
        """实体附加属性（便于自动化与排障）。"""
        now = time.time()
        if self._last_code_sent_at:
            remaining = max(0.0, CODE_RESEND_COOLDOWN_SECONDS - (now - self._last_code_sent_at))
        else:
            remaining = 0.0
        return {
            "status": self._state.value,
            "data_source": driver_name(self.coordinator.api),
            "data_mode": self.coordinator.data_mode,
            "offline_reason": self.coordinator.last_error_reason,
            "sms_phone": _mask_account(self.effective_phone),
            "sms_phone_source": phone_source(self.entry),
            "consecutive_failures": self._failures,
            "failure_limit": MAX_CONSECUTIVE_FAILURES,
            "cooldown_remaining": round(remaining, 1),
            "wait_deadline": _iso(self._wait_deadline),
            "last_error": self._last_error,
            "last_login_at": _iso(self._last_login_at),
        }

    # ------------------------------------------------------------------
    # 开关
    # ------------------------------------------------------------------

    async def async_set_enabled(self, enabled: bool) -> None:
        """开关状态变更（实体调用 / 选项流改动统一入口）。"""
        if enabled == self._enabled:
            return
        self._enabled = enabled
        self._persist_enabled(enabled)

        if enabled:
            # 关→开即视为用户授权重试：清零失败计数并解锁
            self._failures = 0
            self._last_error = None
            self._retry_pending = False
            self._send_fail_logged = False
            self._network_skip_logged = False
            self._state = AutoLoginState.IDLE
            _LOGGER.info("[自动登录] 开关已开启：离线时将自动下发短信验证码")
            self._notify_entities()
            self._evaluate()
        else:
            for task in list(self._tasks):
                task.cancel()
            self._tasks.clear()
            self._timeout_task = None
            self._driver = None
            self._retry_pending = False
            self._wait_deadline = None
            self._state = AutoLoginState.DISABLED
            self._clear_code_entity()
            _LOGGER.info("[自动登录] 开关已关闭")
            self._notify_entities()

    def _persist_enabled(self, enabled: bool) -> None:
        """写入 ConfigEntry.data（options 会被现有选项流整体覆盖，不能用）。"""
        data = {**self.entry.data, CONF_AUTO_LOGIN: enabled}
        self.hass.config_entries.async_update_entry(self.entry, data=data)

    async def _async_handle_entry_update(self, _hass: HomeAssistant, entry: Any) -> None:
        """选项流等外部改动开关时同步状态（自身写入会因值相同而直接返回）。"""
        if not self._is_current():
            return
        value = bool(entry.data.get(CONF_AUTO_LOGIN, False))
        if value == self._enabled:
            return
        await self.async_set_enabled(value)

    @callback
    def _is_current(self) -> bool:
        """当前实例是否为 hass.data 中登记的管理器（未登记视为装配中，允许）。"""
        store = self.hass.data.get(DOMAIN)
        if isinstance(store, dict):
            entry_store = store.get(self.entry.entry_id)
            if isinstance(entry_store, dict):
                return entry_store.get(DATA_AUTO_LOGIN) is self
        return True

    # ------------------------------------------------------------------
    # 触发与发码
    # ------------------------------------------------------------------

    @callback
    def _handle_coordinator_update(self) -> None:
        """每轮刷新结束后评估是否需要自动登录。"""
        if not self._is_current():
            return
        self._evaluate()

    @callback
    def _evaluate(self) -> None:
        # 在线态收尾（与开关无关）：
        #   1. 清空验证码输入框 —— 已恢复在线说明本次登录不再需要，
        #      残留的旧码会在下次登录时被当作新码提交，必须清掉；
        #   2. 作废进行中的登录会话（等待窗口 / 驱动引用）；
        #   3. 离线→在线的那一刻，顺带清掉认证失效留下的持久通知。
        if self.coordinator.data is not None:
            if self.coordinator.data_mode == DATA_MODE_LOCAL_CACHE:
                self._saw_offline = True
            else:
                self._async_abort_login_session("已恢复在线（网络模式）")
                if self._saw_offline:
                    self._saw_offline = False
                    self._async_dismiss_auth_notification()
        if not self._enabled:
            return
        if self._state in (
            AutoLoginState.REQUESTING,
            AutoLoginState.WAITING_CODE,
            AutoLoginState.VERIFYING,
            AutoLoginState.LOCKED,
        ):
            return
        # 未完成过任何刷新时 data_mode 仍是初值 local_cache，不能据此判定离线
        if self.coordinator.data is None:
            return
        if self.coordinator.data_mode != DATA_MODE_LOCAL_CACHE:
            self._retry_pending = False
            self._send_fail_logged = False
            self._network_skip_logged = False
            return
        # 离线原因为网络/中转后端不可达（network_error）时，短信登录同样不可能成功
        # （发码请求也走该中转），自动触发直接跳过；只能等网络恢复后按「短信登录」按钮
        # 手动触发。此判定只影响自动触发，手动按钮不受限制。
        if self.coordinator.last_error_reason == ERROR_REASON_NETWORK:
            if not self._network_skip_logged:
                _LOGGER.info(
                    "[自动登录] 本次离线原因为网络/中转后端不可达（network_error），"
                    "短信登录同样无法成功，已跳过自动发码；网络恢复后可按「短信登录」按钮手动触发"
                )
                self._network_skip_logged = True
            self._retry_pending = False
            return
        # 成功登录后短时间内不重复发码（服务端会话未即时生效时的兜底）
        if self._last_login_at and time.time() - self._last_login_at < MIN_RELOGIN_INTERVAL_SECONDS:
            _LOGGER.debug("[自动登录] 距上次登录成功不足 %d 秒，暂不重复处理", MIN_RELOGIN_INTERVAL_SECONDS)
            return
        if self._in_cooldown():
            # 仅「发码失败」需要按冷却自动重试；等码超时/验证失败交由下轮刷新
            if self._retry_pending:
                self._schedule_retry()
            return
        self._start_send()

    @callback
    def _in_cooldown(self) -> bool:
        if not self._last_code_sent_at:
            return False
        return (time.time() - self._last_code_sent_at) < CODE_RESEND_COOLDOWN_SECONDS

    @callback
    def _schedule_retry(self) -> None:
        if not self._enabled or self._state == AutoLoginState.LOCKED:
            return
        delay = max(1.0, CODE_RESEND_COOLDOWN_SECONDS - (time.time() - (self._last_code_sent_at or 0)))
        self._spawn(self._async_retry_after(delay))

    async def _async_retry_after(self, delay: float) -> None:
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        self._evaluate()

    @callback
    def _start_send(self, *, manual: bool = False) -> None:
        self._state = AutoLoginState.REQUESTING
        self._notify_entities()
        self._spawn(self._async_send_code(manual=manual))

    async def _async_send_code(self, *, manual: bool = False) -> None:
        # 现场构造驱动：Coordinator 可能已按数据库路由热切换数据源
        driver = build_driver(self.coordinator.api, self.entry, self._db)
        account = driver.account
        if not account:
            self._record_failure(
                "未找到接收短信的手机号（可在「短信接收手机号」实体中指定）",
                retry=False,
                counts=False,
            )
            return
        if not PHONE_PATTERN.fullmatch(account):
            # 用户可立即处理：95598 的 loginAccount 未必是机主手机号
            _LOGGER.warning(
                "[自动登录] 当前接收短信的号码「%s」不是 11 位手机号，很可能收不到短信；"
                "请在 text.%s_phone（短信接收手机号）中指定该账号绑定的手机号",
                _mask_account(account),
                build_object_id(self.entry, self.coordinator) or "户号",
            )
        try:
            async with self._auth_lock():
                _LOGGER.info(
                    "[自动登录] %s，向 %s 下发短信验证码（数据源 %s）",
                    "手动触发短信登录" if manual else "检测到离线（本地缓存模式）",
                    _mask_account(account),
                    driver.name,
                )
                await driver.async_request_code()
        except Exception as err:  # noqa: BLE001 网络/接口异常均按失败退避
            # 未真正发出短信（多为中转后端不可达），不计入失败配额，等下一轮刷新再试；
            # 日志只在首次告警，避免后端长时间不可达时刷屏
            if self._send_fail_logged:
                _LOGGER.debug("[自动登录] 下发验证码失败: %s", err)
            else:
                # 未消耗短信、多为网络不可达（真实网络问题由 client/coordinator 另行告警），
                # 因此用 INFO，避免在 HA 日志面板被列为「自定义集成错误」
                _LOGGER.info(
                    "[自动登录] 下发验证码失败（未消耗短信，不计入失败次数）: %s", err
                )
                self._send_fail_logged = True
            self._record_failure(f"下发验证码失败: {err}", retry=False, counts=False)
            return

        if self.coordinator.data_mode != DATA_MODE_LOCAL_CACHE:
            # 发码期间已恢复在线（例如用户同时在集成页完成了重新认证）：
            # 本次登录不再需要，直接作废，避免验证码框残留与无意义的 5 分钟等待
            self._last_code_sent_at = time.time()
            self._driver = None
            self._state = self._rest_state()
            _LOGGER.info("[自动登录] 发码期间已恢复在线（网络模式），本次登录作废")
            self._notify_entities()
            return

        self._driver = driver
        self._last_code_sent_at = time.time()
        self._wait_deadline = time.time() + CODE_WAIT_TIMEOUT_SECONDS
        self._retry_pending = False
        self._send_fail_logged = False
        self._network_skip_logged = False
        self._last_error = None
        self._state = AutoLoginState.WAITING_CODE
        _LOGGER.info(
            "[自动登录] 验证码已下发，请在 %d 分钟内于验证码实体中填入（%d 分钟后自动清空）",
            CODE_WAIT_TIMEOUT_SECONDS // 60,
            CODE_WAIT_TIMEOUT_SECONDS // 60,
        )
        self._notify_entities()
        self._arm_wait_timeout()

    @callback
    def _arm_wait_timeout(self) -> None:
        """（重）装上等待填码超时任务，避免旧窗口提前清空输入框。"""
        self._cancel_wait_timeout()
        self._timeout_task = self._spawn(self._async_wait_timeout())

    @callback
    def _cancel_wait_timeout(self) -> None:
        if self._timeout_task is not None:
            self._timeout_task.cancel()
            self._timeout_task = None

    async def _async_wait_timeout(self) -> None:
        """等待填码超时：清空输入框并计一次失败。"""
        try:
            await asyncio.sleep(CODE_WAIT_TIMEOUT_SECONDS)
        except asyncio.CancelledError:
            return
        self._timeout_task = None
        if self._state != AutoLoginState.WAITING_CODE:
            return
        self._state = self._rest_state()
        self._wait_deadline = None
        self._driver = None
        _LOGGER.warning("[自动登录] 等待验证码超时，已清空验证码输入框")
        self._clear_code_entity()
        # 不计入下一个冷却窗口的自动重试：交由下一轮刷新（10 分钟节拍）再评估
        self._record_failure("等待验证码超时", retry=False)

    async def async_manual_login(self) -> None:
        """按钮：手动触发一次短信登录。

        规则：仅离线（本地缓存模式）且已完成过刷新时生效；在线点击不触发（只记录原因）；
        与开关状态无关（开关关闭时也能手动触发）；手动触发视为用户显式授权，
        会清零失败计数并解除锁定，但仍受 60 秒冷却约束，且不会重复下发已在下发的验证码。
        """
        if self.coordinator.data is None:
            self._last_error = "尚未完成数据刷新，请稍后再试"
            _LOGGER.info("[自动登录] 手动触发被忽略：%s", self._last_error)
            self._notify_entities()
            return
        if self.coordinator.data_mode != DATA_MODE_LOCAL_CACHE:
            self._last_error = "当前为在线状态（网络模式），无需短信登录"
            _LOGGER.info("[自动登录] 手动触发被忽略：当前在线，无需短信登录")
            self._notify_entities()
            return
        if self._state in (AutoLoginState.REQUESTING, AutoLoginState.VERIFYING):
            self._last_error = "正在处理中，请稍候…"
            _LOGGER.info("[自动登录] 手动触发被忽略：已有一个登录请求在处理中")
            self._notify_entities()
            return
        if self._state == AutoLoginState.WAITING_CODE:
            self._last_error = "验证码已下发，请在验证码实体中填入"
            _LOGGER.info("[自动登录] 手动触发被忽略：验证码已下发，等待填写")
            self._notify_entities()
            return
        if self._in_cooldown():
            remain = int(
                CODE_RESEND_COOLDOWN_SECONDS - (time.time() - (self._last_code_sent_at or 0))
            ) + 1
            self._last_error = f"操作过于频繁，请 {remain} 秒后再试"
            _LOGGER.info("[自动登录] 手动触发被忽略：%s", self._last_error)
            self._notify_entities()
            return

        # 手动触发视为用户显式授权：清零失败计数并解除锁定
        # （不校验 last_error_reason：网络可能是刚恢复的，由用户自行判断是否值得一试）
        self._failures = 0
        self._last_error = None
        self._retry_pending = False
        self._send_fail_logged = False
        self._network_skip_logged = False
        _LOGGER.info(
            "[自动登录] 手动按钮触发短信登录（户号 %s）",
            build_object_id(self.entry, self.coordinator) or "未知",
        )
        self._start_send(manual=True)

    # ------------------------------------------------------------------
    # 验证
    # ------------------------------------------------------------------

    async def async_submit_code(self, code: str) -> None:
        """text 实体写入验证码后由实体调用（值已经过 strip）。"""
        if not code:
            return
        if self._state == AutoLoginState.LOCKED:
            _LOGGER.info("[自动登录] 连续失败已达上限处于锁定状态，忽略本次输入（关→开开关或按按钮可解锁）")
            self._clear_code_entity()
            return
        # 注意：不校验开关状态 —— 手动按钮触发时开关可能处于关闭，只要确实下发过
        # 验证码（存在进行中的驱动）就允许提交；开关被关闭会清空驱动，从而落到下面分支
        if self._state != AutoLoginState.WAITING_CODE or self._driver is None:
            _LOGGER.info(
                "[自动登录] 当前不在等待验证码状态（%s），已忽略并清空本次输入", self._state.value
            )
            self._clear_code_entity()
            self._notify_entities()
            return

        driver = self._driver
        self._cancel_wait_timeout()
        self._state = AutoLoginState.VERIFYING
        self._wait_deadline = None
        self._notify_entities()

        try:
            async with self._auth_lock():
                outcome = await driver.async_verify(code)
        except Exception as err:  # noqa: BLE001 校验失败按用户要求清空输入并保留窗口
            self._record_failure(f"验证码校验失败: {err}", retry=False)
            self._clear_code_entity()
            if self._state != AutoLoginState.LOCKED:
                self._state = AutoLoginState.WAITING_CODE
                self._wait_deadline = time.time() + CODE_WAIT_TIMEOUT_SECONDS
                self._arm_wait_timeout()
            self._notify_entities()
            return

        await self._async_apply_login(outcome, driver)

    async def _async_apply_login(self, outcome: Any, driver: SmsLoginDriver) -> None:
        """热生效：落库 → 客户端状态 → ConfigEntry → 立即刷新（不重载集成）。"""
        login_account = str(
            outcome.data_updates.get("login_account") or driver.account or ""
        )
        try:
            if outcome.db_payload and self._db and login_account:
                await self._db.async_save_auth(login_account, outcome.db_payload)
            if outcome.api_state:
                self.coordinator.api.load_auth_state(**outcome.api_state)
            if outcome.data_updates:
                self.hass.config_entries.async_update_entry(
                    self.entry, data={**self.entry.data, **outcome.data_updates}
                )
            # 认证已恢复：清除「需要重新认证 / 修复」的界面提示与残留通知
            self._async_clear_reauth_state()
        except Exception as err:  # noqa: BLE001 热生效失败不吞掉：记录并提示
            self._record_failure(f"登录成功但热生效失败: {err}", retry=False, counts=False)
            self._clear_code_entity()
            self._state = self._rest_state()
            self._notify_entities()
            return

        self._failures = 0
        self._last_error = None
        self._last_login_at = time.time()
        self._last_code_sent_at = None
        self._wait_deadline = None
        self._retry_pending = False
        self._send_fail_logged = False
        self._driver = None
        self._state = self._rest_state()
        self._clear_code_entity()
        self._notify_entities()
        _LOGGER.info(
            "[自动登录] 短信自动登录成功，已热生效（数据源 %s，户号 %s）",
            driver.name,
            build_object_id(self.entry, self.coordinator) or "未知",
        )
        # 立即刷新，把「电费数据模式」切回网络模式
        await self.coordinator.async_request_refresh()

    # ------------------------------------------------------------------
    # 失败处理
    # ------------------------------------------------------------------

    @callback
    def _record_failure(self, message: str, *, retry: bool, counts: bool = True) -> None:
        """记录一次失败。

        counts=False 表示「未真正消耗短信」的失败（发码请求本身失败、无手机号、
        热生效异常）：不计入 3 次配额，否则中转后端短暂不可达就会把自动登录锁死。
        """
        self._last_error = message
        self._retry_pending = retry
        # 本次尝试占用冷却窗口，避免同一轮内重复发码
        self._last_code_sent_at = time.time()
        if not counts:
            self._state = self._rest_state()
            _LOGGER.debug("[自动登录] %s（未消耗短信，不计入失败次数）", message)
            self._notify_entities()
            return
        self._failures += 1
        if self._failures >= MAX_CONSECUTIVE_FAILURES:
            self._state = AutoLoginState.LOCKED
            self._retry_pending = False
            _LOGGER.error(
                "[自动登录] 连续 %d 次失败，已停止自动下发短信（关闭再打开开关或按下「短信登录」按钮可重新启用）。最后错误: %s",
                self._failures,
                message,
            )
        else:
            self._state = self._rest_state()
            _LOGGER.warning(
                "[自动登录] %s（连续失败 %d/%d）",
                message,
                self._failures,
                MAX_CONSECUTIVE_FAILURES,
            )
        self._notify_entities()
        if retry and self._state != AutoLoginState.LOCKED:
            self._evaluate()

    # ------------------------------------------------------------------
    # 会话收尾（在线态 / 登录成功后的界面清理）
    # ------------------------------------------------------------------

    @callback
    def _async_abort_login_session(self, reason: str) -> None:
        """作废进行中的登录会话：取消等待窗口、丢弃驱动引用、清空验证码输入框。

        幂等：没有进行中的会话时只做清空验证码（空值时直接返回）。
        注意 VERIFYING / REQUESTING 状态不动：那两条链路正在进行中，
        分别由 async_submit_code 与 _async_send_code 自行收尾（见发码后在线判定）。
        """
        had_session = self._state == AutoLoginState.WAITING_CODE or self._driver is not None
        self._cancel_wait_timeout()
        self._driver = None
        self._wait_deadline = None
        self._retry_pending = False
        if self._state == AutoLoginState.WAITING_CODE:
            self._state = self._rest_state()
        if had_session:
            _LOGGER.info("[自动登录] %s，已作废本次登录会话", reason)
            self._notify_entities()
        self._clear_code_entity()


    @callback
    def _async_dismiss_auth_notification(self) -> None:
        """关闭 Coordinator 在认证失效时创建的持久通知（notification_id 与其保持一致）。"""
        self.hass.async_create_task(
            self.hass.services.async_call(
                "persistent_notification",
                "dismiss",
                {"notification_id": f"{DOMAIN}_auth_error_{self.entry.entry_id}"},
                blocking=False,
            )
        )

    @callback
    def _async_clear_reauth_state(self) -> None:
        """清除「需要重新认证 / 修复」的界面提示。

        热生效不重载条目，Coordinator 之前触发的重新认证流程（coordinator.py 的
        entry.async_start_reauth）与持久通知会一直挂着，导致 HA 设置页顶部持续提示。
        因此登录成功后主动收尾：
          1. 终止本条目待处理的重新认证流程；
          2. 关闭认证失效的持久通知；
          3. 清掉 reauth_active_* 去重标志（配置流程与卸载流程使用）；
          4. 条目状态异常时补一次重载，确保界面回到正常态。
        """
        try:
            flows = self.hass.config_entries.flow.async_progress_by_handler(DOMAIN)
        except Exception as err:  # noqa: BLE001 流程查询失败不影响登录结果
            _LOGGER.debug("[自动登录] 读取待处理流程失败: %s", err)
            flows = []
        for flow in flows:
            context = flow.get("context") or {}
            if context.get("source") != SOURCE_REAUTH:
                continue
            if context.get("entry_id") != self.entry.entry_id:
                continue
            try:
                self.hass.config_entries.flow.async_abort(flow.get("flow_id"))
                _LOGGER.info("[自动登录] 已终止本条目待处理的重新认证流程，清除界面提示")
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("[自动登录] 终止重新认证流程失败: %s", err)

        self._async_dismiss_auth_notification()

        store = self.hass.data.get(DOMAIN)
        if isinstance(store, dict):
            for key in self._reauth_flag_keys():
                if store.pop(key, None) is not None:
                    _LOGGER.debug("[自动登录] 已清除重新认证标志位 %s", key)

        if self.entry.state is not ConfigEntryState.LOADED:
            _LOGGER.info(
                "[自动登录] 条目状态为 %s，安排一次重载以恢复界面", self.entry.state
            )
            self.hass.config_entries.async_schedule_reload(self.entry.entry_id)

    def _reauth_flag_keys(self) -> list[str]:
        """config_flow / __init__ 使用的重新认证去重标志键（两种口径都清）。"""
        keys = ["reauth_active_default"]
        token = str(self.entry.data.get(CONF_AUTH_TOKEN) or "")
        if token:
            keys.append(f"reauth_active_{token}")
        account = str(
            self.entry.data.get(CONF_LOGIN_ACCOUNT)
            or getattr(self.coordinator.api, "_login_account", None)
            or ""
        )
        if account:
            keys.append(f"reauth_active_{account}")
        return keys

    # ------------------------------------------------------------------
    # 验证码输入框
    # ------------------------------------------------------------------

    @callback
    def _clear_code_entity(self) -> None:
        entity = self._entities.get("code")
        if entity is None:
            return
        clear = getattr(entity, "async_clear_value", None)
        if callable(clear):
            clear()


__all__ = ["AutoLoginManager", "MIN_RELOGIN_INTERVAL_SECONDS"]
