const template = document.createElement('template');
template.innerHTML = `
  <style>
    .electricity-card {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      background: var(--card-bg);
      border-radius: 16px;
      padding: 4px 8px;;
      color: #333333;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
      max-width: 500px;
      margin: 0 auto;
      transition: background 0.3s ease;
    }

    .header {
      display: flex;
      flex-direction: column; /* 纵向布局，让元素上下排列 */
      justify-content: flex-start;
      align-items: stretch; /* 让子元素横向伸展 */
      margin: 0;
      padding: 4px 0 4px 0;
      gap: 3px; /* 元素之间的间距 */
    }

    .user-info {
      font-size: 15px;
      font-weight: 600;
      color: #333;
      text-align: center;
      width: 100%;
    }

    .user-info.hidden {
      display: none;
    }

    .multi-user-info {
      display: flex;
      position: relative;
      align-items: center;
      gap: 0;
      margin: 0 -8px; /* 抵消父容器的左右内边距，让丝带横向贯穿 */
      padding: 0;
      background: transparent; /* 去掉背景色 */
      border-radius: 0;
      width: calc(100% + 16px); /* 增加宽度来抵消左右内边距 */
      overflow-x: auto; /* 允许横向滚动 */
      justify-content: space-around;
      border-bottom: 1px solid var(--button-primary-transparent); /* 底部增加一条分隔线 */
      padding-bottom: 5px; /* 为分隔线增加一些间距 */
    }

    .multi-user-info.hidden {
      display: none; /* 隐藏时 */
    }

    /* 向上发光的横条指示器 */
    .slider-indicator {
      position: absolute;
      height: 3px; /* 横条高度 */
      bottom: 0; /* 位于底部 */
      left: 0;
      width: 80px; /* 默认宽度，会被 JS 覆盖 */
      background: linear-gradient(to top, var(--button-color-active), transparent);
      border-radius: 3px 3px 0 0;
      transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                  width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      z-index: 1;
      pointer-events: none;
      box-shadow: 0 -4px 12px var(--button-color-active); /* 向上发光效果 */
    }

    .user-block {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      background: transparent;
      padding: 0px 0px;
      min-width: 50px;
      cursor: pointer;
      transition: all 0.3s ease;
      z-index: 2;
      opacity: 0.5; /* 默认低亮度 */
      user-select: none;
      flex-shrink: 0;
      border-radius: 8px;
    }

    .user-block.active {
      opacity: 1; /* 高亮显示 */
    }

    .user-block.active .user-block-balance {
      color: var(--button-color-active); /* 选中项使用主题色 */
      text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }

    .user-block.active .user-block-name {
      color: var(--button-color-active);
      font-weight: 600;
    }

    .user-block:hover {
      opacity: 0.8; /* hover 时稍微提高亮度 */
    }

    .user-block-balance {
      font-size: 14px;
      font-weight: 700;
      color: var(--card-value-color);
      margin-bottom: -6px;
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
      transition: all 0.3s ease;
    }

    .user-block-name {
      font-size: 10px;
      color: var(--text-color);
      opacity: 0.85;
      font-weight: 500;
      transition: all 0.3s ease;
    }

    .balance-section {
      text-align: left;
      padding: 3px 0px 0px 0px;
      background: var(--card-button-bg)
      border-radius: 12px;
      backdrop-filter: blur(5px);
    }

    .balance-label-container {
      display: flex;
      flex-direction: row;
      align-items: center;
      gap: 6px;
    }

    .balance-amount-wrapper {
      position: relative;
      display: inline-block;
    }

    .pay-count-badge {
      position: absolute;
      top: 3px;
      right: -38px;
      font-size: 8px;
      font-weight: 600;
      color: var(--card-bg);
      background: var(--text-color);
      padding: 0 4px;
      border-radius: 8px;
      line-height: 1.4;
      z-index: 2;
    }

    .balance-icon {
      width: 16px;
      height: 16px;
      opacity: 0.8;
      color: var(--svg-icon-color);
    }

    .balance-label {
      font-size: 14px;
      opacity: 0.8;
      margin-bottom: 0px;
      order: 0;
      font-weight: 600;
    }

    .price-label-container {
      display: flex;
      align-items: center;
      gap: 4px;
      margin-right: 2px;
    }

    .price-icon {
      width: 14px;
      height: 14px;
      opacity: 0.8;
      color: var(--svg-icon-color);
    }

    .balance-price-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr 1fr;
      align-items: flex-start;
      margin-bottom: -6px;
      order: 2;
      gap: 5px;
    }
    
    .balance-item {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 0px;
      min-width: 0;
      grid-row: span 2;
    }

    .balance-amount {
      left: 20px;
      font-size: 28px;
      font-weight: 700;
      color: #ff5722;
      display: flex;
      align-items: baseline;
      text-shadow: 0 2px 4px rgba(255, 87, 34, 0.2);
      letter-spacing: -0.5px;
      position: relative;
      overflow: hidden;
    }

    /* 45度角白色光带扫过动画 */
    .balance-amount::before {
      content: '';
      position: absolute;
      top: -50%;
      left: -50%;
      width: 200%;
      height: 200%;
      background: linear-gradient(
        45deg,
        transparent 30%,
        rgba(255, 255, 255, 0.4) 50%,
        transparent 70%
      );
      transform: rotate(45deg);
      animation: lightSweep 2s infinite;
    }

    @keyframes lightSweep {
      0% {
        transform: rotate(45deg) translateX(-100%);
      }
      100% {
        transform: rotate(45deg) translateX(100%);
      }
    }

    .balance-unit {
      font-size: 14px;
      opacity: 0.8;
      margin-left: 4px;
      color: var(--button-color);
    }

    .electricity-price-display {
      display: flex;
      align-items: center;
      font-size: 16px;
      font-weight: 600;
      color: #2196f3;
      background: var(--card-button-bg);
      padding: 3px 4px;
      border-radius: 8px;
      flex: 1;
      justify-content: flex-start;
      min-width: 0;
    }

    .remaining-days-display {
      display: flex;
      align-items: center;
      font-size: 16px;
      font-weight: 600;
      color: #2196f3;
      background: var(--card-button-bg);
      padding: 3px 6px;
      border-radius: 8px;
      flex: 1;
      justify-content: flex-start;
      min-width: 0;
    }

    .price-label {
      font-size: 12px;
      opacity: 0.7;
      margin-right: 0px;
      font-weight: normal;
    }

    .price-value {
      color: #2196f3;
      font-weight: 700;
      text-shadow: 0 1px 2px rgba(33, 150, 243, 0.2);
    }

    .price-unit {
      font-size: 11px;
      opacity: 0.8;
      margin-left: 2px;
      color: var(--button-color);
      margin-top: 2px;
    }

    .date-info {
      font-size: 9px;
      opacity: 0.7;
      margin-top: -11px;
      margin-left: 20px;
      touch-action: manipulation;
      -webkit-touch-callout: none;
      -webkit-user-select: none;
      user-select: none;
    }

    .data-date-info {
      display: inline-block;
      font-size: 9px;
      opacity: 0.7;
      margin-top: 0px;
      margin-left: 20px;
      touch-action: manipulation;
      -webkit-touch-callout: none;
      -webkit-user-select: none;
      user-select: none;
    }

    .relative-date-info {
      display: inline-block;
      font-size: 10px;
      padding: 2px 4px;
      border-radius: 3px;
      margin-left: 4px;
      font-weight: 800;
      color: white;
      vertical-align: middle;
      height: 11px;
      line-height: 12px;
    }

    .relative-date-today {
      background: #4CAF50;
    }

    .relative-date-yesterday {
      background: #FF9800;
    }

    .relative-date-day-before-yesterday {
      background: #2196F3;
    }

    .relative-date-other {
      background: #F44336;
    }

    /* 在现有的.tier-indicator样式中添加 */
    .tier-indicator {
      position: relative;
      padding: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      margin: 5px 0 0 0;
      justify-content: space-between;
    }

    /* 添加一个内层容器，用于限制阶梯图的实际宽度 */
    .tier-indicator-container {
      position: relative;
      width: 100%;
      max-width: 420px; 
      margin: 0 auto;
    }
    .tier-label {
      font-size: 14px;
      margin-bottom: 15px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      width: 100%;
    }

    .tier-label-left {
      display: flex;
      align-items: center;
      gap: 6px;
      font-weight: 600;
      max-width: 200px;
    }

    .tier-label-right {
      font-size: 10px;
      opacity: 0.8;
      text-align: right;
      margin-left: auto;
      flex-shrink: 0;
      width: auto;
      min-width: 120px;
    }

    .tiers-container {
      display: flex;
      align-items: flex-end;
      margin-bottom: 10px;
      position: relative;
      justify-content: center;
      gap: 2px;
      z-index: 2;
    }

    .tier {
      position: relative;
      flex: 1;
      min-height: 40px;
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
      max-width: 140px;
      top: 13px;
      transition: top 0.3s ease;
    }

    .tier-block {
      position: relative;
      height: 15px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0 8px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: 600;
      color: #333;
      text-align: center;
      line-height: 1.2;
      z-index: 1;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      transition: all 0.3s ease;
      overflow: hidden;
      white-space: nowrap; /* 防止文字换行 */
    }

    /* 第一阶梯样式 - 右侧尖箭头，左侧直角 */
    .tier-1 .tier-block {
      background-color: rgb(85, 197, 147);
      /* 路径：左上 -> 右上折点 -> 右尖端 -> 右下折点 -> 左下 */
      clip-path: polygon(0% 0%, calc(100% - 12px) 0%, 100% 50%, calc(100% - 12px) 100%, 0% 100%);
      margin-right: -10px;
    }

    /* 第二阶梯样式 - 右侧尖箭头，左侧内凹箭头 */
    .tier-2 .tier-block {
      background-color: rgb(248, 195, 55);
      /* 路径：左上 -> 右上折点 -> 右尖端 -> 右下折点 -> 左下 -> 左侧内凹点 */
      clip-path: polygon(0% 0%, calc(100% - 12px) 0%, 100% 50%, calc(100% - 12px) 100%, 0% 100%, 12px 50%);
      margin: 0 -10px;
    }

    /* 第三阶梯样式 - 右侧直角，左侧内凹箭头 */
    .tier-3 .tier-block {
      background-color: rgb(247, 147, 53);
      /* 路径：左上 -> 右上 -> 右下 -> 左下 -> 左侧内凹点 */
      clip-path: polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%, 12px 50%);
      margin-left: -10px;
    }

    /* 红色竖线指示器 - 放在tiers-container中，与current-indicator相同的定位基准 */
    .red-line-indicator {
      position: absolute;
      top: 13px;
      left: 0;
      width: 3px;
      height: 15px;
      background-color: #ff0000;
      z-index: 2;
      box-shadow: 0 0 3px rgba(255, 0, 0, 0.7);
      transform: translateX(-50%);
    }

    /* 水波纹涟漪动画效果 */
    .red-line-indicator::before,
    .red-line-indicator::after {
      content: '';
      position: absolute;
      top: 50%;
      left: 50%;
      width: 3px;
      height: 15px;
      background-color: #ff0000;
      border-radius: 2px;
      transform: translate(-50%, -50%);
      animation: ripple 2s infinite;
    }

    .red-line-indicator::after {
      animation-delay: 1s;
    }

    @keyframes ripple {
      0% {
        width: 3px;
        height: 15px;
        opacity: 1;
        box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.7);
      }
      50% {
        opacity: 0.7;
      }
      100% {
        width: 25px;
        height: 35px;
        opacity: 0;
        box-shadow: 0 0 0 8px rgba(255, 0, 0, 0);
      }
    }

    .current-indicator-clone {
      position: absolute;
      top: -18px;
      transform: translateX(-50%);
      z-index: 2;
      pointer-events: none;
      visibility: visible !important;
    }

    .current-indicator-clone:after {
      content: '';
      position: absolute;
      bottom: -4px;
      left: 50%;
      transform: translateX(-50%);
      width: 0;
      height: 0;
      border-left: 4px solid transparent;
      border-right: 4px solid transparent;
      border-top: 4px solid;
    }

    .current-indicator-clone.tier-1:after {
      border-top-color: rgb(85, 197, 147);
    }

    .current-indicator-clone.tier-2:after {
      border-top-color: rgb(248, 195, 55);
    }

    .current-indicator-clone.tier-3:after {
      border-top-color: rgb(247, 147, 53);
    }

    .tier.current .tier-block {
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
      filter: brightness(1.05);
    }

    .tier-content {
      margin-top: 2px;
      text-align: center;
      font-size: 11px;
      color: var(--button-color);
      line-height: 1.3;
      padding: 6px 4px;
      border-radius: 4px;
      position: relative;
      overflow: hidden;
      z-index: 0;
      transition: all 0.3s ease;
    }

    .tier-content.hidden {
      display: none;
    }

    .tier-title {
      font-weight: 600;
      margin-bottom: 2px;
      color: #444;
    }

    .tier-range {
      margin-bottom: 2px;
    }

    .tier-price {
      font-weight: 500;
    }

    .tier-1 .tier-price {
      color: rgb(85, 197, 147);
    }

    .tier-2 .tier-price {
      color: rgb(248, 195, 55);
    }

    .tier-3 .tier-price {
      color: rgb(247, 147, 53);
    }

    .current-indicator {
      position: absolute;
      top: -18px;
      left: 50%;
      transform: translateX(-50%);
      background-color: #ff5722;
      color: white;
      padding: 3px 5px;
      border-radius: 10px;
      font-size: 11px;
      font-weight: 600;
      white-space: nowrap;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
      z-index: 2;
      display: flex;
      align-items: center;
      gap: 4px;
      pointer-events: none; /* 防止遮挡点击事件 */
      --arrow-offset: 0px;
      min-width: 0;
      /* 确保指示器不会超出容器边界 */
      max-width: calc(100% - 16px); /* 左右各保留8px边距 */
      overflow: visible;
    }

    /* 根据当前阶梯设置背景色 */
    .current-indicator.tier-1 {
      background-color: rgb(85, 197, 147);
    }

    .current-indicator.tier-2 {
      background-color: rgb(248, 195, 55);
    }

    .current-indicator.tier-3 {
      background-color: rgb(247, 147, 53);
    }

    .indicator-arrow {
      position: absolute;
      top: 7px;
      width: 0;
      height: 0;
      border-left: 4px solid transparent;
      border-right: 4px solid transparent;
      border-top: 4px solid;
      z-index: 2;
      transform: translateX(-50%);
    }

    .tier-1 .indicator-arrow {
      border-top-color: rgb(85, 197, 147);
    }

    .tier-2 .indicator-arrow {
      border-top-color: rgb(248, 195, 55);
    }

    .tier-3 .indicator-arrow {
      border-top-color: rgb(247, 147, 53);
    }

    .data-container {
      display: flex;
      flex-direction: row;
      gap: 6px; /* 进一步减少间距 */
      margin-bottom: 10px;
      margin-top: 20px;
      transition: margin-top 0.3s ease;
    }

    /* 当tier-content隐藏时，data-container向上移动 */
    .data-container.compact {
      margin-top: 0px;
    }

    /* 统一的统计区域样式 */
    .current-month-stats,
    .month-stats,
    .year-stats {
      flex: 1;
      background: var(--card-button-bg);
      border-radius: 12px;
      padding: 3px;
      backdrop-filter: blur(5px);
      position: relative;
    }

    .current-month-stats {
      min-width: 100px;
    }

    .month-stats,
    .year-stats {
      min-width: 100px;
    }

    /* 统一的标签样式 */
    .month-label,
    .year-label {
      font-size: 12px;
      opacity: 0.8;
      margin-bottom: 2px;
      display: flex;
      align-items: center;
      gap: 3px;
    }

    .trend-arrow {
      position: absolute;
      top: 8px;
      right: 8px;
      font-size: 10px;
      font-weight: 700;
      line-height: 1;
      z-index: 1;
    }

    .trend-arrow.up {
      color: #f44336;
    }

    .trend-arrow.down {
      color: #4CAF50;
    }

    /* 统一的网格样式 */
    .month-grid,
    .year-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0px;
      margin-bottom: 4px; /* 添加底部边距为分时条留空间 */
    }

    /* 统一的统计项样式 */
    .month-stat,
    .year-stat {
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    /* 统一的数值样式 */
    .month-stat-value,
    .year-stat-value {
      font-size: 12px;
      font-weight: 600;
      color: var(--usage-color);
      display: flex;
      align-items: baseline;
    }

    /* 统一的单位样式 */
    .month-stat-unit,
    .year-stat-unit {
      font-size: 10px;
      opacity: 0.8;
      margin-left: 2px;
    }

    .year-stat-value.yellow {
      color: var(--money-color);
    }

    .year-stat-value.green {
      color: var(--usage-color);
    }

    .year-stat-unit {
      font-size: 10px;
      opacity: 0.8;
      margin-left: 2px;
    }

    .time-distribution-bar {
      width: 100%;
      height: 15px;
      background: rgba(255, 255, 255, 0.2);
      border-radius: 3px;
      overflow: hidden;
      display: flex;
      margin-top: -4px;
      position: relative; 
    }

    .time-distribution-bar.empty {
      display: none; /* 当没有数据时隐藏 */
    }

    .time-distribution-bar.hidden {
      display: none; /* 当配置为不显示时隐藏 */
    }

    .time-segment {
      height: 100%;
      transition: all 0.3s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      overflow: hidden;
      font-size: 9px;
      font-weight: 600;
      color: white; 
      text-shadow: 1px 1px 1px rgba(0, 0, 0, 0.5);
      min-width: 20px;
    }

    /* 各分时用电背景色 */
  .time-segment-peak {
    background: linear-gradient(90deg, #FF9800, #F57C00); /* 峰 - 橙色渐变 */
  }

  .time-segment-normal {
    background: linear-gradient(90deg, #2196F3, #1976D2); /* 平 - 蓝色渐变 */
  }

  .time-segment-valley {
    background: linear-gradient(90deg, #4CAF50, #388E3C); /* 谷 - 绿色渐变 */
  }

  .time-segment-tip {
    background: linear-gradient(90deg, #F44336, #D32F2F); /* 尖 - 红色渐变 */
  }

    /* 分时用电标签 - 移除前面的颜色点 */
    .time-labels {
      display: flex;
      justify-content: space-between;
      font-size: 9px;
      color: var(--button-color);
      margin-top: 2px;
      opacity: 0.8;
      position: relative;
    }

    .time-labels.empty {
      display: none; /* 当没有数据时隐藏 */
    }

    .time-labels.hidden {
      display: none; /* 当配置为不显示时隐藏 */
    }

    .time-label {
      display: flex;
      flex-direction: column; /* 改为垂直布局 */
      align-items: center;
      text-align: center;
      width: 100%; /* 每个标签占满可用空间 */
    }

    /* 移除时间点样式 */
    .time-dot {
      display: none; /* 隐藏颜色点 */
    }

    /* 分时用电分布标签（在data-container中） */
    .time-distribution-labels {
      display: flex;
      justify-content: space-between;
      font-size: 9px;
      color: var(--button-color);
      margin-top: 2px;
      opacity: 0.8;
      position: relative;
      width: 100% !important;
      height: auto !important;
      margin-left: 0 !important;
    }
    
    /* 隐藏分时用电标签 */
    .time-distribution-labels.hidden {
      display: none !important;
    }

    .time-distribution-labels.empty {
      display: none; /* 当没有数据时隐藏 */
    }

    .time-distribution-labels span {
      position: static !important;
      white-space: nowrap;
      transform: none !important;
      flex: 1;
      text-align: center;
      box-sizing: border-box;
    }

    .icon {
      width: 16px;
      height: 16px;
      opacity: 0.7;
      color: var(--svg-icon-color);
    }

    .tier-icon {
      width: 14px;
      height: 14px;
      color: var(--svg-icon-color);
    }

    /* 应用主题变量到主卡片 */
    .electricity-card {
      background: var(--card-bg);
      color: var(--card-name-color);
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
      position: relative;
      overflow: hidden;
    }

    /* 背景图标基础样式 */
    .electricity-card::before {
      content: '';
      position: absolute;
      top: 150px;
      left: 39%;
      transform: translate(-50%, -50%);
      width: 150px;
      height: 150px;
      opacity: 0.08;
      color: var(--text-color, #333);
      background-repeat: no-repeat;
      background-position: center;
      background-size: contain;
      pointer-events: none;
      z-index: 1;
    }

    /* 当multiclass只有一个时，背景图标的top值改为110px */
    .electricity-card.single-class::before {
      top: 110px;
    }

    /* 电力背景图标 - 高压电塔 */
    .electricity-card.bg-ele::before {
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='currentColor' d='M8.28,5.45L6.5,4.55L7.76,2H16.23L17.5,4.55L15.72,5.44L15,4H9L8.28,5.45M18.62,8H14.09L13.3,5H10.7L9.91,8H5.38L4.1,10.55L5.89,11.44L6.62,10H17.38L18.1,11.45L19.89,10.56L18.62,8M17.77,22H15.7L15.46,21.1L12,15.9L8.53,21.1L8.3,22H6.23L9.12,11H11.19L10.83,12.35L12,14.1L13.16,12.35L12.81,11H14.88L17.77,22M11.4,15L10.5,13.65L9.32,18.13L11.4,15M14.68,18.12L13.5,13.64L12.6,15L14.68,18.12Z'/%3E%3C/svg%3E");
    }

    /* 燃气背景图标 - 火 */
    .electricity-card.bg-gas::before {
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='currentColor' d='M17.66 11.2C17.43 10.9 17.15 10.64 16.89 10.38C16.22 9.78 15.46 9.35 14.82 8.72C13.33 7.26 13 4.85 13.95 3C13 3.23 12.17 3.75 11.46 4.32C8.87 6.4 7.85 10.07 9.07 13.22C9.11 13.32 9.15 13.42 9.15 13.55C9.15 13.77 9 13.97 8.8 14.05C8.57 14.15 8.33 14.09 8.14 13.93C8.08 13.88 8.04 13.83 8 13.76C6.87 12.33 6.69 10.28 7.45 8.64C5.78 10 4.87 12.3 5 14.47C5.06 14.97 5.12 15.47 5.29 15.97C5.43 16.57 5.7 17.17 6 17.7C7.08 19.43 8.95 20.67 10.96 20.92C13.1 21.19 15.39 20.8 17.03 19.32C18.86 17.66 19.5 15 18.56 12.72L18.43 12.46C18.22 12 17.66 11.2 17.66 11.2M14.5 17.5C14.22 17.74 13.76 18 13.4 18.1C12.28 18.5 11.16 17.94 10.5 17.28C11.69 17 12.4 16.12 12.61 15.23C12.78 14.43 12.46 13.77 12.33 13C12.21 12.26 12.23 11.63 12.5 10.94C12.69 11.32 12.89 11.7 13.13 12C13.9 13 15.11 13.44 15.37 14.8C15.41 14.94 15.43 15.08 15.43 15.23C15.46 16.05 15.1 16.95 14.5 17.5H14.5Z'/%3E%3C/svg%3E");
    }

    /* 水背景图标 - 水滴 */
    .electricity-card.bg-water::before {
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='currentColor' d='M12,20A6,6 0 0,1 6,14C6,10 12,3.25 12,3.25C12,3.25 18,10 18,14A6,6 0 0,1 12,20Z'/%3E%3C/svg%3E");
    }

    /* 更新文本颜色 */
    .user-info {
      color: var(--card-name-color);
    }

    .balance-label, .price-label, .date-info, .tier-label-left, .tier-label-right,
    .tier-range, .month-label, .year-label, .month-stat-unit, .year-stat-unit {
      color: var(--text-color);
    }

    .balance-amount {
      color: var(--card-value-color);
    }

    .electricity-price-display .price-value,
    .remaining-days-display .price-value {
      color: var(--card-value-color);
    }

    .month-stat-value.green {
      color: var(--usage-color);
    }

    .month-stat-value.yellow {
      color: var(--money-color);
    }

    .year-stat-value {
      color: var(--usage-color);
    }

    /* 更新统计区域背景 */
    .current-month-stats, .month-stats, .year-stats {
      background: var(--card-button-bg);
    }

    /* 更新分时用电条背景 */
    .time-distribution-bar {
      background: var(--button-primary-transparent);
    }

    /* 更新阶梯内容背景色 */
    .tier-1 .tier-content {
      background: linear-gradient(to bottom, rgba(85, 197, 147, 0.2) 0%, rgba(85, 197, 147, 0.05) 100%);
    }

    .tier-2 .tier-content {
      background: linear-gradient(to bottom right, rgba(248, 195, 55, 0.2) 0%, rgba(248, 195, 55, 0.05) 100%);
    }

    .tier-3 .tier-content {
      background: linear-gradient(to bottom right, rgba(247, 147, 53, 0.2) 0%, rgba(247, 147, 53, 0.05) 100%);
    }

    /* ==================== 日历视图样式 ==================== */
    .calendar-view {
      width: 97%;
      padding: 8px;
      margin-top: 23px;
      min-height: 355px;
      animation: fadeIn 0.3s ease;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* 切换用户时的卡片过渡动画 */
    .electricity-card.switching {
      animation: cardSwitchOut 0.3s ease forwards;
    }

    .electricity-card.switching-in {
      animation: cardSwitchIn 0.4s ease forwards;
    }

    @keyframes cardSwitchOut {
      0% {
        opacity: 1;
        transform: scale(1) translateY(0);
      }
      100% {
        opacity: 0;
        transform: scale(0.98) translateY(-5px);
      }
    }

    @keyframes cardSwitchIn {
      0% {
        opacity: 0;
        transform: scale(0.98) translateY(5px);
      }
      100% {
        opacity: 1;
        transform: scale(1) translateY(0);
      }
    }

    .calendar-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
      font-size: 12px;
      padding: 0;
      flex-wrap: nowrap;
      gap: 8px;
    }

    .calendar-tabs {
      display: flex;
      gap: 5px;
      flex: 1;
    }

    .cal-tab-btn {
      padding: 0 4px;
      border: 1px solid var(--button-color);
      border-radius: 4px;
      background: var(--card-button-bg);
      cursor: pointer;
      font-size: 12px;
      color: var(--text-color);
      white-space: nowrap;
      transition: all 0.2s;
      height: 25px;
    }

    .cal-tab-btn:hover {
      border-color: var(--button-color-active);
      color: var(--button-color-active);
      background: var(--button-primary-transparent);
    }

    .cal-tab-btn.active {
      background: var(--button-color-active);
      color: var(--card-bg);
      border-color: var(--button-color-active);
      box-shadow: 0 0 0 1px var(--button-color-active);
    }

    .calendar-controls {
      display: flex;
      gap: 5px;
      align-items: center;
      white-space: nowrap;
      flex: 1;
      justify-content: flex-end;
      min-width: 0;
    }

    .calendar-back-control {
      display: flex;
      align-items: center;
    }

    .cal-control-btn {
      padding: 0 4px;
      border: 1px solid var(--button-color);
      border-radius: 4px;
      background: var(--card-button-bg);
      cursor: pointer;
      font-size: 12px;
      color: var(--text-color);
      transition: all 0.2s;
      height: 25px;
    }

    .cal-control-btn:hover {
      border-color: var(--button-color-active);
      color: var(--button-color-active);
      background: var(--button-primary-transparent);
    }

    .cal-control-btn.active {
      background: var(--button-color-active);
      color: var(--card-bg);
      border-color: var(--button-color-active);
      box-shadow: 0 0 0 1px var(--button-color-active);
    }

    .cal-control-select {
      background: var(--card-button-bg);
      color: var(--text-color);
      border: 1px solid var(--button-color);
      border-radius: 4px;
      padding: 0;
      cursor: pointer;
      height: 25px;
      min-width: 48px;
      font-size: 11px;
      text-align: center;
    }

    .cal-control-select:hover {
      border-color: var(--button-color-active);
    }

    .cal-control-select:focus {
      outline: none;
      border-color: var(--card-button-bg);
      background: var(--card-bg);
      color: var(--text-color);
      box-shadow: 0 0 0 1px var(--button-color-active);
    }

    .calendar-grid {
      display: grid;
      grid-template-columns: repeat(7, minmax(0, 1fr));
      gap: 0;
      font-size: 0.7em;
      background: transparent;
      border: 2px solid var(--calendar-line-color);
      margin-bottom: 5px;
    }

    .day-of-week {
      text-align: center;
      font-weight: bold;
      padding: 4px;
      border-bottom: 2px solid var(--calendar-line-color);
      font-size: 11px;
      color: var(--text-color);
    }
    .day-of-week:not(:last-child) {
      border-right: 2px solid var(--calendar-line-color);
    }

    .calendar-day {
      position: relative;
      padding: 4px;
      background: rgba(0, 0, 0, 0);
      min-height: 30px;
      border-bottom: 2px solid var(--calendar-line-color);
      cursor: pointer;
      transition: all 0.2s;
    }

    .calendar-day:not(:nth-child(7n)) {
      border-right: 2px solid var(--calendar-line-color);
    }

    .calendar-day.has-date {
      background: var(--calendar-line-color);
    }

    .calendar-day.today {
      background: rgba(128, 164, 255, 0.3) !important;
    }

    .calendar-day.future-date {
      opacity: 0.4;
      cursor: not-allowed !important;
      background: rgba(128, 128, 128, 0.1) !important;
    }

    .calendar-day.future-date .date-circle {
      background: rgba(128, 128, 128, 0.3) !important;
      color: rgba(128, 128, 128, 0.6) !important;
    }

    /* 预计使用天数进度条 */
    .usage-progress-bar {
      position: absolute;
      bottom: 0;
      left: 0;
      width: 100%;
      height: 3px;
      background: #4CAF50;
      z-index: 5;
      pointer-events: none;
      box-shadow: 0 0 4px rgba(76, 175, 80, 0.5);
    }
    
    /* 当月用电量最大和最小的单元格背景色 - 最高优先级 */
    .calendar-day.has-date.max-usage-day {
      background: #f88988 !important;
    }
    
    .calendar-day.has-date.min-usage-day {
      background: #3eb370 !important;
    }
    
    /* 确保最大/最小用量样式优先于today样式 */
    .calendar-day.has-date.today.max-usage-day {
      background: #f88988 !important;
    }
    
    .calendar-day.has-date.today.min-usage-day {
      background: #3eb370 !important;
    }

    .date-circle {
      background: var(--date-circle-bg, rgba(220, 53, 69, 1));
      color: var(--date-circle-color, white);
      border-radius: 50%;
      width: 16px;
      height: 16px;
      line-height: 18px;
      display: flex;
      align-items: center;
      justify-content: center;
      position: absolute;
      top: 2px;
      left: 2px;
      font-size: 10px;
    }

    .device-history-marker {
      position: absolute;
      top: 2px;
      right: 2px;
      font-size: 9px;
      font-weight: bold;
      color: var(--date-circle-color);
      background: var(--date-circle-bg);
      width: 12px;
      height: 12px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 2;
    }

    /* 统一的日历数据值样式 */
    .data-value,
    .calc-value {
      padding: 0px 2px;
      border-radius: 3px;
      margin-left: 10%;
      margin-right: 10%;
      font-size: 10px;
      width: 80%;
      text-align: center;
      display: inline-block;
    }

    .data-value {
      background: var(--usage-color);
      color: black;
      margin-top: 12px;
    }

    .calc-value {
      background: var(--money-color);
      color: white;
      margin-top: 1px;
    }

    .calendar-stats {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      padding: 0;
      flex-wrap: nowrap;
    }

    .calendar-stat-item {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .stat-label {
      font-weight: bold;
      color: var(--secondary-text);
    }

    .stat-value {
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: bold;
    }

    .kwh-value {
      background-color: var(--usage-color);
      color: black;
    }

    .cost-value {
      background-color: var(--money-color);
      color: white;
    }

    /* 暗色主题下的日历样式 */

    /* ==================== 模态框样式 ==================== */
    .day-modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      animation: fadeIn 0.2s ease;
      backdrop-filter: blur(4px);
      -webkit-backdrop-filter: blur(4px);
    }

    .day-modal-content {
      position: relative;
      background: var(--card-bg);
      border-radius: 12px;
      padding: 5px 10px 10px 10px;
      max-width: 450px;
      width: 90%;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8);
      animation: scaleIn 0.3s ease;
      color: var(--text-color);
      /* 使用 transform 进行居中定位 */
      transform: scale(0.9);
      opacity: 0;
      transition: transform 0.3s ease, opacity 0.3s ease;
    }
    
    .day-modal-overlay[style*="display: flex"] .day-modal-content {
      transform: scale(1);
      opacity: 1;
    }

    @keyframes slideUp {
      from {
        opacity: 0;
        transform: translateY(20px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .day-modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 5px;
      padding-bottom: 0px;
      border-bottom: 2px solid rgba(0, 0, 0, 0.1);
    }

    .day-modal-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-color);
    }

    .day-modal-close {
      background: none;
      border: none;
      font-size: 28px;
      color: var(--text-color);
      cursor: pointer;
      line-height: 1;
      padding: 0;
      width: 30px;
      height: 30px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      transition: background 0.2s;
    }

    .day-modal-close:hover {
      background: rgba(0, 0, 0, 0.1);
    }

    /* 饼图区域样式 - 日用电详情 */
    .pie-chart-section {
      display: flex;
      flex-direction: column;
      background: var(--card-button-bg);
      border-radius: 8px;
      flex: 1;
      min-width: 0;
      height: 235px;
    }

    /* 饼图区域样式 - 缴费历史弹窗 */
    .pay-history-pie-chart-section {
      display: flex;
      flex-direction: column;
      background: var(--card-button-bg);
      border-radius: 8px;
      flex: 1;
      min-width: 0;
      height: 235px;
    }

    .pie-chart-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-color);
      margin-left: 15px;
    }

    .pie-chart-content {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      flex: 1;
      min-height: 0;
    }

    .pie-chart-container {
      width: 100%;
      height: 205px;
      position: relative;
      top: -7px;
    }

    .usage-stats {
      flex: 0 0 35%;
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: -20px;
    }

    .usage-stat-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 3px 3px;
      background: var(--button-primary-transparent);
      border-radius: 6px;
      border-left: 4px solid;
    }

    .usage-stat-label {
      font-weight: 600;
      font-size: 11px;
      color: var(--text-color);
    }

    .usage-stat-value {
      font-weight: bold;
      font-size: 11px;
      color: var(--text-color);
    }

    .valley-stat {
      border-left-color: #4CAF50;
    }

    .peak-stat {
      border-left-color: #FF9800;
    }

    .normal-stat {
      border-left-color: #2196F3;
    }

    .sharp-stat {
      border-left-color: #F44336;
    }

    .total-stat {
      border-left-color: #804AFF;
      background: rgba(128, 74, 255, 0.1) !important;
    }

    /* 设备轨道样式 - 来自device-replay-card.js */
    .timeline-aligner {
      display: grid;
      grid-template-columns: 67px 80px 1fr;
      align-items: center;
      margin-top: 10px;
      gap: 2px;
    }

    .timeline-aligner-spacer {
      width: 100px;
      flex-shrink: 0;
    }

    .timeline-aligner-spacer-2 {
      width: 60px;
      flex-shrink: 0;
    }

    .timeline-aligner-content {
      flex-grow: 1;
      margin-left: 0;
      width: 299px;
    }

    #timeline-container {
      margin-top: 10px;
      background: var(--card-button-bg);
      border-radius: 8px;
      padding: 10px;
    }

    .device-track {
      display: grid;
      grid-template-columns: 60px 85px 1fr;
      align-items: center;
      margin-bottom: 8px;
      height: 12px;
      width: 100%;
      gap: 2px;
      align-content: center;
    }

    .device-label {
      width: 100px;
      font-size: 12px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-right: 10px;
      padding: 0px 0px;
      border-radius: 4px;
      color: var(--button-color-active);
      flex-shrink: 0;
      text-align: left;
      box-sizing: border-box;
    }

    .power-usage-container {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 4px;
      font-size: 10px; /* 固定字体大小，不从配置读取 */
      font-weight: 600;
      white-space: nowrap;
      font-family: 'Courier New', monospace;
      transform-origin: center;
    }

    /* 统一的设备功率/时长样式 */
    .power-usage,
    .usage-duration,
    .power-usage-estimate {
      text-align: center;
      font-size: 10px;
      min-width: 40px;
      padding: 0px 0px;
      border-radius: 3px;
      font-weight: 600;
    }

    .power-usage {
      background: var(--usage-color);
      color: #000000;
    }

    .power-usage-estimate {
      background: #38b48b;
      color: #000000;
    }

    .usage-duration {
      background: var(--money-color);
      color: white;
    }

    /* 合计行样式 */
    .total-row {
      display: grid;
      grid-template-columns: 60px 85px 1fr;
      align-items: center;
      margin-top: 10px;
      padding-top: 8px;
      border-top: 1px solid var(--button-primary-transparent);
      font-weight: 600;
      font-size: 11px;
      color: var(--text-color);
      height: 12px;
      width: 100%;
      gap: 2px;
      align-content: center;
    }

    .total-label {
      width: 100px;
      font-size: 11px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-right: 10px;
      padding: 0px 0px;
      border-radius: 4px;
      color: var(--button-color-active);
      flex-shrink: 0;
      text-align: left;
      box-sizing: border-box;
    }

    .total-value {
      text-align: center;
      font-size: 10px;
      min-width: 40px;
      padding: 2px 4px;
      border-radius: 3px;
      font-weight: 600;
      background: var(--button-primary-transparent);
      color: var(--text-color);
    }

    /* timeline-aligner 中的 time-labels（绝对定位版本） */
    .timeline-aligner .time-labels {
      position: relative;
      width: 106%;
      height: 10px;
      margin-top: -5px;
      margin-left: -10px;
      font-size: 9px;
      color: var(--text-color);
      font-weight: 400;
    }

    .timeline-aligner .time-labels span {
      position: absolute;
      top: 0;
      white-space: nowrap;
      box-sizing: border-box;
      transform: translateX(-50%);
      font-weight: 400;
    }

    .timeline-aligner .time-labels span:nth-child(1) {
      left: 0%;
      transform: translateX(0%);
    }
    .timeline-aligner .time-labels span:nth-child(2) { left: 33.333%; }
    .timeline-aligner .time-labels span:nth-child(3) { left: 66.666%; }
    .timeline-aligner .time-labels span:nth-child(4) {
      left: 100%;
      transform: translateX(-100%);
    }



    .track-bar-wrapper {
      flex-grow: 1;
      position: relative;
      height: 15px;
      background: rgba(0,0,0,0.05);
      border-radius: 4px;
      cursor: pointer;
      margin-right: 0;
    }

    .track-bar {
      width: 100%;
      height: 15px;
      position: relative;
    }

    .track-fill {
      position: absolute;
      height: 15px;
      top: 0;
      opacity: 0.7;
      border-radius: 2px;
      transition: opacity 0.2s;
    }

    .track-fill.active {
      opacity: 1;
      box-shadow: 0 0 4px rgba(0,0,0,0.3);
      z-index: 2;
    }

    @keyframes stripe-move {
      from { background-position: 0 0; }
      to { background-position: 1rem 0; }
    }

    @keyframes rainbow-glow {
      0% { box-shadow: 0 0 6px 2px rgba(255, 0, 0, 0.8), 0 0 12px 4px rgba(255, 165, 0, 0.6); }
      14% { box-shadow: 0 0 6px 2px rgba(255, 165, 0, 0.8), 0 0 12px 4px rgba(255, 255, 0, 0.6); }
      28% { box-shadow: 0 0 6px 2px rgba(255, 255, 0, 0.8), 0 0 12px 4px rgba(0, 128, 0, 0.6); }
      42% { box-shadow: 0 0 6px 2px rgba(0, 128, 0, 0.8), 0 0 12px 4px rgba(0, 255, 255, 0.6); }
      57% { box-shadow: 0 0 6px 2px rgba(0, 255, 255, 0.8), 0 0 12px 4px rgba(0, 0, 255, 0.6); }
      71% { box-shadow: 0 0 6px 2px rgba(0, 0, 255, 0.8), 0 0 12px 4px rgba(128, 0, 128, 0.6); }
      85% { box-shadow: 0 0 6px 2px rgba(128, 0, 128, 0.8), 0 0 12px 4px rgba(255, 0, 0, 0.6); }
      100% { box-shadow: 0 0 6px 2px rgba(255, 0, 0, 0.8), 0 0 12px 4px rgba(255, 165, 0, 0.6); }
    }

    .track-fill.on-going {
      background-image: linear-gradient(45deg,rgba(255,255,255,.15) 25%,transparent 25%,transparent 50%,rgba(255,255,255,.15) 50%,rgba(255,255,255,.15) 75%,transparent 75%,transparent);
      background-size: 1rem 1rem;
      animation: stripe-move 1s linear infinite, rainbow-glow 8s linear infinite;
    }

    /* 正在运行事件列表项的动画样式 */
    #tooltip-events-list .on-going-event {
      position: relative;
      background-image: linear-gradient(45deg, rgba(255,255,255,0.1) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.1) 75%, transparent 75%, transparent);
      background-size: 0.8rem 0.8rem;
      animation: stripe-move 1.5s linear infinite;
      border-left: 3px solid var(--button-color-active);
      padding-left: 8px;
    }

    #tooltip-events-list .on-going-event::before {
      content: "●";
      position: absolute;
      left: -12px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--button-color-active);
      font-size: 8px;
      animation: pulse 1.5s infinite;
    }

    @keyframes pulse {
      0% { opacity: 1; }
      50% { opacity: 0.3; }
      100% { opacity: 1; }
    }

    /* 设备事件提示框样式 - 已移除，使用JavaScript动态创建的样式 */

    /* 缴费历史模态框样式 */
    .pay-history-top-section {
      display: flex;
      gap: 10px;
      margin-bottom: 10px;
      align-items: stretch;
      height: 140px;
    }

    .pay-history-summary {
      display: flex;
      justify-content: space-evenly;
      background: var(--card-button-bg);
      border-radius: 8px;
      width: 25%;
      flex-shrink: 0;
      flex-direction: column;
      height: 130px;
    }

    .pay-history-item {
      text-align: center;
    }

    .pay-history-label {
      font-size: 12px;
      color: var(--text-color);
      opacity: 0.8;
    }

    .pay-history-value {
      font-size: 18px;
      font-weight: 700;
      color: var(--card-value-color);
    }

    .pay-history-list {
      max-height: 350px;
      overflow-y: auto;
      padding-right: 5px;
    }

    .pay-history-list::-webkit-scrollbar {
      width: 6px;
    }

    .pay-history-list::-webkit-scrollbar-track {
      background: var(--button-primary-transparent);
      border-radius: 3px;
    }

    .pay-history-list::-webkit-scrollbar-thumb {
      background: var(--button-color);
      border-radius: 3px;
    }

    .pay-record {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 5px 15px;
      background: var(--card-button-bg);
      border-radius: 6px;
      margin-bottom: 8px;
      border-left: 3px solid var(--money-color);
      transition: all 0.2s ease;
    }

    .pay-record:hover {
      background: var(--button-primary-transparent);
      transform: translateX(3px);
    }

    .pay-record-left {
      flex: 1;
    }

    .pay-record-time {
      font-size: 12px;
      color: var(--text-color);
      opacity: 0.7;
      margin-bottom: 1px;
    }

    .pay-record-source {
      font-size: 11px;
      color: white;
      opacity: 1;
      padding: 2px 6px;
      border-radius: 4px;
      display: inline-block;
    }

    /* 支付宝 - 蓝色 */
    .pay-record-source.alipay {
      background: #1677FF;
    }

    /* 微信 - 绿色 */
    .pay-record-source.wechat {
      background: #52C41A;
    }

    /* 网上国网 - 深蓝色 */
    .pay-record-source.sgcc-online {
      background: #14806E;
    }

    /* 电e宝 - 金色 */
    .pay-record-source.eebao {
      background: #FAAD14;
    }

    /* 社会网点 - 橙色 */
    .pay-record-source.outlet {
      background: #FA8C16;
    }

    /* 银行卡 - 紫色 */
    .pay-record-source.bank {
      background: #9C27B0;
    }

    /* 其他 - 灰色 */
    .pay-record-source.other {
      background: #8C8C8C;
    }

    /* 默认 - 青色 */
    .pay-record-source.default {
      background: #13C2C2;
    }

    .pay-record-cost {
      font-size: 16px;
      font-weight: 700;
      color: var(--money-color);
    }

    .pay-record-cost::before {
      content: '¥';
      font-size: 12px;
      margin-right: 2px;
    }

    .no-pay-history {
      text-align: center;
      padding: 40px 20px;
      color: var(--text-color);
      opacity: 0.7;
    }

    .no-pay-history-icon {
      font-size: 48px;
      margin-bottom: 10px;
    }

    .no-pay-history-text {
      font-size: 14px;
    }

    .no-pay-history-subtext {
      font-size: 12px;
      margin-top: 5px;
      opacity: 0.7;
    }

    /* 年视图和月视图样式 */
    #year-content, #month-content {
      display: flex;
      flex-direction: column;
      height: calc(400px - 50px);
    }

    .year-chart-container {
      margin-bottom: 0px;
      background: var(--stat-bg);
      border-radius: 8px;
      padding: 7px;
      display: flex;
      flex-direction: column;
      flex: 1;
      height: 100%;
    }

    .chart-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-color);
      margin-bottom: 4px;
      text-align: center;
      flex-shrink: 0;
      margin-top: -15px;
    }

    .month-labels-container {
      display: flex;
      justify-content: center;
      gap: 2px;
      margin-bottom: 0px;
      flex-shrink: 0;
    }

    .month-label-item {
      font-size: 11px;
      color: #666;
      text-align: center;
      flex: 1;
      max-width: 30px;
    }

    .year-filter {
      display: flex;
      justify-content: space-evenly;
      gap: 2px;
      flex-shrink: 0;
      flex-wrap: wrap;
    }

    .year-filter#day-filter {
      gap: 3px;
    }

    .year-filter#year-year-filter {
      margin-bottom: 8px;
    }

    .year-filter-main {
      display: flex;
      justify-content: center;
      gap: 5px;
      margin-bottom: 8px;
      flex-shrink: 0;
    }

    .year-filter-years {
      display: flex;
      justify-content: space-evenly;
      gap: 1px;
      flex-shrink: 0;
      flex-wrap: wrap;
    }

    .day-filter-main {
      display: flex;
      justify-content: center;
      gap: 5px;
      margin-bottom: 8px;
      flex-shrink: 0;
    }

    .day-filter-years {
      display: flex;
      justify-content: space-evenly;
      gap: 5px;
      flex-shrink: 0;
      flex-wrap: wrap;
    }

    .year-tag {
      padding: 2px 2px;
      border: 1px solid var(--button-color-active);
      border-radius: 16px;
      background: transparent;
      color: var(--button-color);
      font-size: 12px;
      cursor: pointer;
      transition: all 0.2s ease;
      white-space: nowrap;
    }

    .year-tag:hover {
      background: var(--button-primary-transparent);
    }

    .year-tag.active {
      background: var(--button-color-active);
      color: var(--button-active-text-color);
    }

    .month-tag {
      padding: 1px 1px;
      border: 1px solid var(--button-color);
      border-radius: 6px;
      background: transparent;
      color: var(--button-color);
      font-size: 12px;
      cursor: pointer;
      transition: all 0.2s ease;
      white-space: nowrap;
      width: 16px;
      margin-top: 5px;
      text-align: center;
    }

    .month-tag:hover {
      background: var(--button-primary-transparent);
    }

    .month-tag.active {
      background: var(--button-color-active);
      color: var(--card-bg);
    }

    .chart-wrapper {
      width: 100%;
      flex: 1;
      min-height: 270px;
    }
  </style>

  <div class="electricity-card">
    <div class="header">
      <div class="user-info" id="user-info">用电信息</div>
      <div class="multi-user-info" id="multi-user-info">
        <div class="slider-indicator" id="slider-indicator">
          <div class="spotlight-core"></div>
        </div>
        <div class="user-block active" data-index="0">
          <div class="user-block-balance">¥128.50</div>
          <div class="user-block-name">用户A</div>
        </div>
        <div class="user-block" data-index="1">
          <div class="user-block-balance">¥256.30</div>
          <div class="user-block-name">用户B</div>
        </div>
        <div class="user-block" data-index="2">
          <div class="user-block-balance">¥89.20</div>
          <div class="user-block-name">用户C</div>
        </div>
      </div>
    </div>

    <div class="balance-section">
      <div class="balance-price-row">
        <div class="balance-item">
          <div class="balance-label-container">
            <svg class="balance-icon" viewBox="0 0 24 24">
              <path fill="var(--svg-icon-color)" d="M2,5H22V20H2V5M20,18V7H4V18H20M17,8A2,2 0 0,0 19,10V15A2,2 0 0,0 17,17H7A2,2 0 0,0 5,15V10A2,2 0 0,0 7,8H17M17,13V12C17,10.9 16.33,10 15.5,10C14.67,10 14,10.9 14,12V13C14,14.1 14.67,15 15.5,15C16.33,15 17,14.1 17,13M15.5,11A0.5,0.5 0 0,1 16,11.5V13.5A0.5,0.5 0 0,1 15.5,14A0.5,0.5 0 0,1 15,13.5V11.5A0.5,0.5 0 0,1 15.5,11M13,13V12C13,10.9 12.33,10 11.5,10C10.67,10 10,10.9 10,12V13C10,14.1 10.67,15 11.5,15C12.33,15 13,14.1 13,13M11.5,11A0.5,0.5 0 0,1 12,11.5V13.5A0.5,0.5 0 0,1 11.5,14A0.5,0.5 0 0,1 11,13.5V11.5A0.5,0.5 0 0,1 11.5,11M8,15H9V10H8L7,10.5V11.5L8,11V15Z" />
            </svg>
            <span class="balance-label" id="balance-label">账户余额</span>
          </div>
          <div class="balance-amount-wrapper">
            <div class="balance-amount">
              ¥<span id="balance">0.00</span>
              <span class="balance-unit"></span>
            </div>
            <span class="pay-count-badge" id="pay-count-badge"></span>
          </div>
        </div>
        <div class="price-display electricity-price-display">
          <div class="price-label-container">
            <svg class="price-icon" viewBox="0 0 24 24">
              <path fill="var(--svg-icon-color)" d="M7,15H9C9,16.08 10.37,17 12,17C13.63,17 15,16.08 15,15C15,13.9 13.96,13.5 11.76,12.97C9.64,12.44 7,11.78 7,9C7,7.21 8.47,5.69 10.5,5.18V3H13.5V5.18C15.53,5.69 17,7.21 17,9H15C15,7.92 13.63,7 12,7C10.37,7 9,7.92 9,9C9,10.1 10.04,10.5 12.24,11.03C14.36,11.56 17,12.22 17,15C17,16.79 15.53,18.31 13.5,18.82V21H10.5V18.82C8.47,18.31 7,16.79 7,15Z" />
            </svg>
            <span class="price-label">电价:</span>
          </div>
          <span class="price-value" id="electricity-price">0.4983</span>
          <span class="price-unit"></span>
        </div>
        <!-- 新增：剩余天数显示 -->
        <div class="price-display remaining-days-display">
          <div class="price-label-container">
            <svg class="price-icon" viewBox="0 0 24 24">
              <path fill="var(--svg-icon-color)" d="M16,11.78L20.24,4.45L21.97,5.45L16.74,14.5L10.23,10.75L5.46,19H22V21H2V3H4V17.54L9.5,8L16,11.78Z" />
            </svg>
            <span class="price-label">预计用:</span>
          </div>
          <span class="price-value" id="remaining-days">0</span>
          <span class="price-unit">天</span>
          <span class="price-unit" id="remaining-days-date"></span>
        </div>
      </div>
      <div class="date-info" id="date">更新时间 --</div>
      <div class="data-date-info" id="data-date">数据:--</div>
      <div class="relative-date-info" id="relative-date"></div>
    </div>

    <div class="tier-indicator">
      <div class="tier-label">
        <div class="tier-label-left">
          <svg class="icon tier-icon" viewBox="0 0 24 24">
            <path fill="var(--svg-icon-color)" d="M19,3H5C3.9,3 3,3.9 3,5V19C3,20.1 3.9,21 5,21H19C20.1,21 21,20.1 21,19V5C21,3.9 20.1,3 19,3M19,19H5V5H19V19M7,12H9V17H7V12M11,7H13V17H11V7M15,10H17V17H15V10Z" />
          </svg>
          用电阶梯
        </div>
        <div class="tier-label-right" id="tier-period">阶梯周期: 07.01-06.30</div>
      </div>
    </div>
    
    <!-- 添加一个内层容器，用于限制阶梯图的实际宽度 -->
    <div class="tier-indicator-container">
      <div class="tiers-container" id="tiers-container">
        <div class="tier tier-1" id="tier-1">
          <div class="tier-block" id="tier-1-block">第一阶梯</div>
          <div class="tier-content">
            <div class="tier-range" id="tier-1-range"></div>
            <div class="tier-price" id="tier-1-price"></div>
          </div>
        </div>
        
        <div class="tier tier-2" id="tier-2">
          <div class="tier-block" id="tier-2-block">第二阶梯</div>
          <div class="tier-content">
            <div class="tier-range" id="tier-2-range"></div>
            <div class="tier-price" id="tier-2-price"></div>
          </div>
        </div>
        
        <div class="tier tier-3" id="tier-3">
          <div class="tier-block" id="tier-3-block">第三阶梯</div>
          <div class="tier-content">
            <div class="tier-range" id="tier-3-range"></div>
            <div class="tier-price" id="tier-3-price"></div>
          </div>
        </div>
        
        <div class="current-indicator" id="current-indicator">
          <span id="current-tier">❶</span><span id="current-usage">0</span>
        </div>
        <div class="indicator-arrow" id="indicator-arrow"></div>
      </div>
    </div>
        <div class="data-container" id="data-container">
      <!-- 本月用电 -->
      <div class="current-month-stats" data-type="current-month">
        <span class="trend-arrow" id="month-trend-arrow"></span>
        <div class="month-label">
          <svg class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" width="12" height="12">
            <path d="M512 1018C232.5 1018 6 791.5 6 512S232.5 6 512 6s506 226.5 506 506-226.5 506-506 506z m0-973.1C254 44.9 44.9 254 44.9 512S254 979.1 512 979.1 979.1 770 979.1 512 770 44.9 512 44.9zM395.2 862.3L473 589.8H278.5l350.3-428.2L551 434.1h194.6L395.2 862.3z" fill="var(--svg-icon-color)"></path>
          </svg>
          本月用电
        </div>
        
        <div class="month-grid">
          <div class="month-stat">
            <div class="month-stat-value green">
              <span id="current-month-electricity">0</span>
              <span class="month-stat-unit" id="current-month-ele-unit"></span>
            </div>
          </div>
          
          <div class="month-stat">
            <div class="month-stat-value yellow">
              <span id="current-month-cost">0</span>
              <span class="month-stat-unit" id="current-month-cost-unit"></span>
            </div>
          </div>
        </div>
        
        <!-- 本月分时用电条 -->
        <div class="time-distribution-bar" id="current-month-distribution"></div>
        <div class="time-distribution-labels" id="current-month-labels"></div>
      </div>

      <!-- 上月用电 -->
      <div class="month-stats" data-type="last-month">
        <span class="trend-arrow" id="last-month-trend-arrow"></span>
        <div class="month-label">
          <svg class="icon" viewBox="0 0 24 24">
            <path fill="var(--svg-icon-color)" d="M19,19V8H5V19H19M16,1H18V3H19A2,2 0 0,1 21,5V19A2,2 0 0,1 19,21H5C3.89,21 3,20.1 3,19V5C3,3.89 3.89,3 5,3H6V1H8V3H16V1M7,10H9V12H7V10M15,10H17V12H15V10M11,14H13V16H11V14M15,14H17V16H15V14Z"/>
          </svg>
          上月用电
        </div>
        
        <div class="month-grid">
          <div class="month-stat">
            <div class="month-stat-value">
              <span id="last-month-electricity">0</span>
              <span class="month-stat-unit" id="last-month-ele-unit"></span>
            </div>
          </div>
          
          <div class="month-stat">
            <div class="month-stat-value yellow">
              <span id="last-month-cost">0</span>
              <span class="month-stat-unit" id="last-month-cost-unit"></span>
            </div>
          </div>
        </div>
        
        <!-- 上月分时用电条 -->
        <div class="time-distribution-bar" id="last-month-distribution"></div>
        <div class="time-distribution-labels" id="last-month-labels"></div>
      </div>

      <!-- 年度累计 -->
      <div class="year-stats" data-type="year">
        <span class="trend-arrow" id="year-trend-arrow"></span>
        <div class="year-label">
          <svg class="icon" viewBox="0 0 24 24">
            <path fill="var(--svg-icon-color)" d="M9,10V12H7V10H9M13,10V12H11V10H13M17,10V12H15V10H17M19,3A2,2 0 0,1 21,5V19A2,2 0 0,1 19,21H5C3.89,21 3,20.1 3,19V5A2,2 0 0,1 5,3H6V1H8V3H16V1H18V3H19M19,19V8H5V19H19M9,14V16H7V14H9M13,14V16H11V14H13M17,14V16H15V14H17Z"/>
          </svg>
          <span id="current-year">2025</span>年用电
        </div>
        
        <div class="year-grid">
          <div class="year-stat">
            <div class="year-stat-value green">
              <span id="year-electricity">0</span>
              <span class="year-stat-unit" id="year-ele-unit"></span>
            </div>
          </div>
          
          <div class="year-stat">
            <div class="year-stat-value yellow">
              <span id="year-cost">0</span>
              <span class="year-stat-unit" id="year-cost-unit"></span>
            </div>
          </div>
        </div>
        
        <!-- 年度分时用电条 -->
        <div class="time-distribution-bar" id="year-distribution"></div>
        <div class="time-distribution-labels" id="year-labels"></div>
      </div>
    </div>

    <!-- 日历视图（默认隐藏） -->
    <div class="calendar-view" id="calendar-view" style="display: none;">
      <!-- 选项卡和控制区域 -->
    <div class="calendar-header">
      <div class="calendar-tabs">
        <button class="cal-tab-btn" data-view="year">年</button>
        <button class="cal-tab-btn" data-view="month">月</button>
        <button class="cal-tab-btn" data-view="day">日</button>
        <button class="cal-tab-btn active" data-view="calendar">日历</button>
      </div>
      <div class="calendar-controls">
        <button class="cal-control-btn" id="current-month-btn">本月</button>
        <select id="cal-year-select" class="cal-control-select">
          <!-- 年份选项动态生成 -->
        </select>
        <select id="cal-month-select" class="cal-control-select">
          <option value="1">1月</option>
          <option value="2">2月</option>
          <option value="3">3月</option>
          <option value="4">4月</option>
          <option value="5">5月</option>
          <option value="6">6月</option>
          <option value="7">7月</option>
          <option value="8">8月</option>
          <option value="9">9月</option>
          <option value="10">10月</option>
          <option value="11">11月</option>
          <option value="12">12月</option>
        </select>
      </div>
      <div class="calendar-back-control">
        <button class="cal-control-btn" id="back-to-main">返回</button>
      </div>
    </div>

      <!-- 日历视图内容 -->
      <div id="calendar-content">
        <!-- 日历网格 -->
        <div class="calendar-grid" id="calendar-grid">
          <div class="day-of-week">周一</div>
          <div class="day-of-week">周二</div>
          <div class="day-of-week">周三</div>
          <div class="day-of-week">周四</div>
          <div class="day-of-week">周五</div>
          <div class="day-of-week">周六</div>
          <div class="day-of-week">周日</div>
          <!-- 日期单元格动态生成 -->
        </div>

        <!-- 统计信息 -->
        <div class="calendar-stats">
          <div class="calendar-stat-item">
            <span class="stat-label">月用量：</span>
            <span class="stat-value kwh-value" id="cal-month-usage">0</span>
            <span class="stat-value cost-value" id="cal-month-cost">¥0</span>
          </div>
          <div class="calendar-stat-item">
            <span class="stat-label">年用量：</span>
            <span class="stat-value kwh-value" id="cal-year-usage">0</span>
            <span class="stat-value cost-value" id="cal-year-cost">¥0</span>
          </div>
        </div>
      </div>

      <!-- 年视图内容（默认隐藏） -->
      <div id="year-content" style="display: none;">
        <!-- 年度电费与用电量组合图 -->
        <div class="year-chart-container">
          <div class="chart-title">年度电费与用电量趋势</div>
          <div class="year-filter-main" id="year-filter-main"></div>
          <div class="year-filter-years" id="year-filter-years"></div>
          <div class="chart-wrapper" id="year-combo-chart"></div>
        </div>
        <!-- 日用电热力图（默认隐藏） -->
        <div class="year-chart-container" id="year-heatmap-container" style="display: none;">
          <div class="chart-title">日用电热力图</div>
          <div class="month-labels-container">
            <div class="month-label-item">1</div>
            <div class="month-label-item">2</div>
            <div class="month-label-item">3</div>
            <div class="month-label-item">4</div>
            <div class="month-label-item">5</div>
            <div class="month-label-item">6</div>
            <div class="month-label-item">7</div>
            <div class="month-label-item">8</div>
            <div class="month-label-item">9</div>
            <div class="month-label-item">10</div>
            <div class="month-label-item">11</div>
            <div class="month-label-item">12</div>
          </div>
          <div class="chart-wrapper" id="year-heatmap-chart"></div>
        </div>

        <!-- 年度累计动态排名柱状图（默认隐藏） -->
        <div class="year-chart-container" id="bar-racing-container" style="display: none; flex: none; height: auto !important;">
          <div class="chart-title">年度累计用电排名</div>
          <div style="display: flex; gap: 5px; justify-content: center; align-items: center; margin-bottom: 4px;">
            <button id="bar-racing-mode-day-btn" class="year-tag active">按日累积</button>
            <button id="bar-racing-mode-month-btn" class="year-tag">按月累积</button>
            <button id="bar-racing-play-btn" class="year-tag active">播放</button>
            <button id="bar-racing-speed-btn" class="year-tag">速度 x1</button>
          </div>
          <div id="bar-racing-timeline" style="padding: 0 10px; margin-bottom: 4px;">
            <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-color); opacity: 0.45; margin-bottom: 3px;">
              <span>1月</span><span>2月</span><span>3月</span><span>4月</span><span>5月</span><span>6月</span><span>7月</span><span>8月</span><span>9月</span><span>10月</span><span>11月</span><span>12月</span>
            </div>
            <div style="position: relative; height: 5px; background: rgba(200,200,200,0.1); border-radius: 3px; overflow: visible;">
              <div id="bar-racing-progress" style="position: absolute; left: 0; top: 0; height: 5px; width: 0%; background: linear-gradient(90deg, rgb(85, 197, 147), rgb(248, 195, 55), rgb(247, 147, 53)); border-radius: 3px; opacity: 0.5; transition: width 3s cubic-bezier(0.25, 0.1, 0.25, 1);"></div>
              <div id="bar-racing-marker" style="position: absolute; top: -4px; background: linear-gradient(135deg, var(--card-value-color, #ff5722), #ff7043); border-radius: 20px; left: 0%; transition: left 3s cubic-bezier(0.25, 0.1, 0.25, 1); box-shadow: 0 0 0 2px rgba(255,255,255,0.9), 0 0 8px var(--card-value-color, #ff5722); z-index: 10; padding: 0 5px; height: 11px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 9px; font-weight: 600; white-space: nowrap; pointer-events: none; transform: translateX(-50%); line-height: 1;">
                <span id="bar-racing-date">1.1</span>
              </div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: -4px;">
              <span style="width: 1px; height: 3px; background: rgba(150,150,150,0.3);"></span>
              <span style="width: 1px; height: 3px; background: rgba(150,150,150,0.3);"></span>
              <span style="width: 1px; height: 3px; background: rgba(150,150,150,0.3);"></span>
              <span style="width: 1px; height: 3px; background: rgba(150,150,150,0.3);"></span>
              <span style="width: 1px; height: 3px; background: rgba(150,150,150,0.3);"></span>
              <span style="width: 1px; height: 3px; background: rgba(150,150,150,0.35);"></span>
              <span style="width: 1px; height: 3px; background: rgba(150,150,150,0.35);"></span>
              <span style="width: 1px; height: 3px; background: rgba(150,150,150,0.35);"></span>
              <span style="width: 1px; height: 3px; background: rgba(150,150,150,0.35);"></span>
              <span style="width: 1px; height: 3px; background: rgba(150,150,150,0.35);"></span>
              <span style="width: 1px; height: 3px; background: rgba(150,150,150,0.35);"></span>
              <span style="width: 1px; height: 3px; background: rgba(150,150,150,0.35);"></span>
            </div>
          </div>
          <div class="chart-wrapper" id="bar-racing-chart"></div>
        </div>
      </div>

      <!-- 月视图内容（默认隐藏） -->
      <div id="month-content" style="display: none;">
        <!-- 月度电费与用电量组合图 -->
        <div class="year-chart-container">
          <div class="chart-title">月度电费与用电量趋势</div>
          <div class="year-filter" id="month-year-filter"></div>
          <div class="chart-wrapper" id="month-combo-chart"></div>
        </div>
      </div>

      <!-- 日视图内容（默认隐藏） -->
      <div id="day-content" style="display: none;">
        <!-- 日用电详情组合图 -->
        <div class="year-chart-container">
          <div class="chart-title">日用电详情</div>
          <div class="day-filter-main" id="day-filter-main"></div>
          <div class="day-filter-years" id="day-filter-years"></div>
          <div class="chart-wrapper" id="day-combo-chart"></div>
          <!-- 未来月份提示文字 -->
          <div class="future-month-message" id="future-month-message" style="display: none; text-align: center; padding: 60px 20px; font-size: 16px; color: var(--card-value-color); font-style: italic; line-height: 1.8;">
            愿为期之可待，化北辰以恒明，引千帆而向曙。
          </div>
        </div>
      </div>
    </div>

    <!-- 日详情模态框 -->
    <div class="day-modal-overlay" id="day-modal" style="display: none;">
      <div class="day-modal-content">
        <div class="day-modal-header">
          <div class="day-modal-title" id="day-modal-title">用电详情</div>
          <button class="day-modal-close" id="day-modal-close">×</button>
        </div>
        <div id="day-modal-body">
          <!-- 动态内容 -->
        </div>
      </div>
    </div>

    <!-- 缴费历史模态框 -->
    <div class="day-modal-overlay" id="pay-history-modal" style="display: none;">
      <div class="day-modal-content">
        <div class="day-modal-header">
          <div class="day-modal-title" id="pay-history-title">缴费历史</div>
          <button class="day-modal-close" id="pay-history-close">×</button>
        </div>
        <div id="pay-history-body">
          <!-- 动态内容 -->
        </div>
      </div>
    </div>

    <!-- 设备事件提示框（移到根级别，不受模态框影响） -->
    <div id="event-tooltip">
      <strong id="tooltip-device-name"></strong>
      <ul id="tooltip-events-list"></ul>
    </div>
  </div>
`;

// ECharts 加载函数 - 优先加载本地，本地失败则从CDN加载
function loadECharts() {
  if (window._echartsLoadPromise) {
    return window._echartsLoadPromise;
  }

  window._echartsLoadPromise = new Promise((resolve, reject) => {
    // 如果ECharts已加载，直接返回
    if (typeof echarts !== 'undefined') {
      resolve(echarts);
      return;
    }

    // 尝试加载本地echarts.min.js
    const localScript = document.createElement('script');
    localScript.src = '/local/echarts.min.js';
    
    localScript.onload = () => {
      if (typeof echarts !== 'undefined') {
       // console.log('✓ ECharts 从本地加载成功');
        resolve(echarts);
      } else {
        console.warn('✗ 本地ECharts加载成功但全局变量未定义，尝试CDN...');
        loadFromCDN(resolve, reject);
      }
    };

    localScript.onerror = () => {
      console.warn('✗ 本地ECharts加载失败，尝试CDN...');
      loadFromCDN(resolve, reject);
    };

    document.head.appendChild(localScript);
  });

  return window._echartsLoadPromise;
}

// 从CDN加载ECharts
function loadFromCDN(resolve, reject) {
  const cdnScript = document.createElement('script');
  cdnScript.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js';
  
  cdnScript.onload = () => {
    if (typeof echarts !== 'undefined') {
      console.log('✓ ECharts 从CDN加载成功');
      resolve(echarts);
    } else {
      reject(new Error('ECharts CDN加载后全局变量未定义'));
    }
  };

  cdnScript.onerror = () => {
    reject(new Error('ECharts CDN加载失败'));
  };

  document.head.appendChild(cdnScript);
}

class ElectricityInfoCard extends HTMLElement {
  // =================================== 统一数据格式转换方法 ========================================
  
  /**
   * 安全转换数值，处理字符串、null、undefined
   */
  safeParseFloat(value, defaultValue = 0) {
    if (value === null || value === undefined || value === '') {
      return defaultValue;
    }
    const num = parseFloat(value);
    return isNaN(num) ? defaultValue : num;
  }
  
  /**
   * 计算并显示相对日期（今天、昨天、前天、x天前）
   */
  updateRelativeDate(dateStr, lastData = null) {
    if (!this.relativeDateEl || !dateStr || dateStr === '--') {
      return;
    }

    // 解析日期
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) {
      this.relativeDateEl.textContent = '';
      this.relativeDateEl.className = 'relative-date-info';
      return;
    }

    // 获取今天的日期（去除时间部分）
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // 获取数据日期（去除时间部分）
    const dataDate = new Date(date);
    dataDate.setHours(0, 0, 0, 0);

    // 计算天数差
    const diffTime = today.getTime() - dataDate.getTime();
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    let text = '';
    let className = 'relative-date-info';

    if (diffDays === 0) {
      text = '今天';
      className += ' relative-date-today';
    } else if (diffDays === 1) {
      text = '昨天';
      className += ' relative-date-yesterday';
    } else if (diffDays === 2) {
      text = '前天';
      className += ' relative-date-day-before-yesterday';
    } else if (diffDays > 2) {
      text = `${diffDays}天前`;
      className += ' relative-date-other';
    } else {
      // 未来日期（不应该出现）
      text = '';
      className = 'relative-date-info';
    }

    // 如果有最后一组数据，追加显示
    if (lastData) {
      const usage = parseFloat(lastData.total_usage);
      const cost = parseFloat(lastData.total_amount);
      const unit = lastData.unit || '';
      if (!isNaN(usage) && usage > 0) {
        text += ` ${usage} ${unit}`;
        if (!isNaN(cost) && cost > 0) {
          text += `  ┃  ¥ ${cost}`;
        }
      }
    }

    this.relativeDateEl.textContent = text;
    this.relativeDateEl.className = className;
  }

  /**
   * 从原始daylist条目中提取最后一天的数据（统一格式）
   */
  _extractLastDayRawData(rawItem, mapping) {
    if (!rawItem) return null;
    const usageField = mapping.usage || (this.utilityType === 'ele' ? 'dayEleNum' : null);
    const amountField = mapping.amount || (this.utilityType === 'ele' ? 'dayEleCost' : null);
    const usage = usageField ? this.safeParseFloat(rawItem[usageField]) : this.safeParseFloat(rawItem.dayEleNum);
    const amount = amountField ? this.safeParseFloat(rawItem[amountField]) : this.safeParseFloat(rawItem.dayEleCost);
    return {
      total_usage: usage,
      total_amount: amount,
      unit: rawItem.unit || this.getUnitByUtilityType(this.utilityType)
    };
  }
  
  /**
   * 根据 utility_type 获取单位
   */
  getUnitByUtilityType(utilityType) {
    switch (utilityType) {
      case 'ele':
        return '°';
      case 'water':
        return 't';
      case 'gas':
        return 'm³';
      default:
        return '°'; // 默认使用电的单位
    }
  }
  
  /**
   * 根据 utility_type 更新动态文本
   */
  updateDynamicTexts(utilityType) {
    // 定义文本映射
    const textMap = {
      ele: {
        priceLabel: '电单价:',
        monthCurrent: '本月用电',
        monthLast: '上月用电',
        year: '年用电',
        tierLabel: '用电阶梯',
        chartTitleYear: '年度电费与用电量趋势',
        chartTitleMonth: '月度电费与用电量趋势',
        chartTitleDay: '日用电详情',
        chartTitleHeatmap: '日用电热力图',
        dayModalTitle: '用电详情',
        pieChartTitle: '用电分布'
      },
      water: {
        priceLabel: '水单价:',
        monthCurrent: '本月用水',
        monthLast: '上月用水',
        year: '年用水',
        tierLabel: '用水阶梯',
        chartTitleYear: '年度水费与用水量趋势',
        chartTitleMonth: '月度水费与用水量趋势',
        chartTitleDay: '日用水详情',
        chartTitleHeatmap: '日用水热力图',
        dayModalTitle: '用水详情',
        pieChartTitle: '用水分布'
      },
      gas: {
        priceLabel: '气单价:',
        monthCurrent: '本月用气',
        monthLast: '上月用气',
        year: '年用气',
        tierLabel: '用气阶梯',
        chartTitleYear: '年度天然气费与用气量趋势',
        chartTitleMonth: '月度天然气费与用气量趋势',
        chartTitleDay: '日用气详情',
        chartTitleHeatmap: '日用气热力图',
        dayModalTitle: '用气详情',
        pieChartTitle: '用气分布'
      }
    };
    
    // 存储文本映射为实例属性，供其他方法使用
    this.textMap = textMap[utilityType] || textMap.ele;
    
    const texts = this.textMap;
    
    // 1. 更新价格标签
    if (this.priceLabelEl) {
      this.priceLabelEl.textContent = texts.priceLabel;
    }
    
    // 2. 更新月份标签
    if (this.monthLabels && this.monthLabels.length >= 2) {
      // 清除第一个月份标签的所有文本节点，然后添加新文本
      const textNodes0 = Array.from(this.monthLabels[0].childNodes).filter(node => 
        node.nodeType === Node.TEXT_NODE
      );
      textNodes0.forEach(node => node.remove());
      this.monthLabels[0].appendChild(document.createTextNode(texts.monthCurrent));
      
      // 清除第二个月份标签的所有文本节点，然后添加新文本
      const textNodes1 = Array.from(this.monthLabels[1].childNodes).filter(node => 
        node.nodeType === Node.TEXT_NODE
      );
      textNodes1.forEach(node => node.remove());
      this.monthLabels[1].appendChild(document.createTextNode(texts.monthLast));
    }
    
    // 3. 更新年度标签
    if (this.yearLabels && this.yearLabels.length > 0) {
      // 清除所有文本节点（保留 span#current-year 元素）
      const textNodes = Array.from(this.yearLabels[0].childNodes).filter(node => 
        node.nodeType === Node.TEXT_NODE
      );
      textNodes.forEach(node => node.remove());
      
      // 只添加文本部分，不包含年份（年份由 span#current-year 提供）
      this.yearLabels[0].appendChild(document.createTextNode(texts.year));
    }
    
    // 4. 更新阶梯标签
    if (this.tierLabelLeftEl) {
      // 清除所有文本节点
      const textNodes = Array.from(this.tierLabelLeftEl.childNodes).filter(node => 
        node.nodeType === Node.TEXT_NODE
      );
      textNodes.forEach(node => node.remove());
      
      // 添加新文本
      this.tierLabelLeftEl.appendChild(document.createTextNode(texts.tierLabel));
    }
    
    // 5. 更新图表标题
    const chartTitles = this.shadowRoot.querySelectorAll('.chart-title');
    chartTitles.forEach((titleEl) => {
      if (titleEl) {
        if (titleEl.textContent.includes('年度') && titleEl.textContent.includes('趋势')) {
          titleEl.textContent = texts.chartTitleYear;
        } else if (titleEl.textContent.includes('月度') && titleEl.textContent.includes('趋势')) {
          titleEl.textContent = texts.chartTitleMonth;
        } else if (titleEl.textContent.includes('日') && titleEl.textContent.includes('详情')) {
          titleEl.textContent = texts.chartTitleDay;
        } else if (titleEl.textContent.includes('日') && titleEl.textContent.includes('热力图')) {
          titleEl.textContent = texts.chartTitleHeatmap;
        }
      }
    });
  }

  /**
   * 初始化多户滑动条
   */
  setupMultiUserBar() {
    if (!this.multiUserInfoEl) return;
    
    // 根据是否显示多用户条来设置样式
    if (this.showMultiUserBar) {
      this.multiUserInfoEl.classList.remove('hidden');
    } else {
      this.multiUserInfoEl.classList.add('hidden');
      return;
    }
    
    // 清空现有的用户块
    this.multiUserInfoEl.innerHTML = '';
    
    // 重新创建滑块指示器
    const sliderIndicator = document.createElement('div');
    sliderIndicator.className = 'slider-indicator';
    sliderIndicator.id = 'slider-indicator';
    this.multiUserInfoEl.appendChild(sliderIndicator);
    this.sliderIndicatorEl = sliderIndicator;
    
    // 创建用户块
    const userKeys = Object.keys(this.multiClassConfig);
    userKeys.forEach((key, index) => {
      const config = this.multiClassConfig[key];
      const userBlock = document.createElement('div');
      userBlock.className = `user-block ${index === this.currentUserIndex ? 'active' : ''}`;
      userBlock.dataset.index = index;
      
      // 创建余额显示（初始显示'--'，加载后更新）
      const balanceDiv = document.createElement('div');
      balanceDiv.className = 'user-block-balance';
      balanceDiv.textContent = '--';
      balanceDiv.dataset.entity = config.entity ? config.entity.split(',')[0].trim() : '';
      
      // 创建名称显示（格式：{info}_{类型中文}）
      const nameDiv = document.createElement('div');
      nameDiv.className = 'user-block-name';
      const utilityType = config.utility_type || 'ele';
      const typeName = this.getUtilityTypeName(utilityType);
      const infoValue = config.info || key; // 使用 config.info 作为前缀，如果没有则使用 key
      nameDiv.textContent = `${infoValue}_${typeName}`;
      
      userBlock.appendChild(balanceDiv);
      userBlock.appendChild(nameDiv);
      
      // 添加点击事件
      userBlock.addEventListener('click', () => {
        this.switchUser(index);
      });
      
      this.multiUserInfoEl.appendChild(userBlock);
    });
    
    // 初始化所有用户的余额显示
    this.updateAllUsersBalance();

    // 更新滑块位置
    this.userBlocks = this.multiUserInfoEl.querySelectorAll('.user-block');

    // 确保当前用户块的 active 状态正确设置（首次进入卡片时）
    if (this.userBlocks.length > 0 && this.currentUserIndex < this.userBlocks.length) {
      // 使用 requestAnimationFrame 确保 DOM 已经渲染完成
      requestAnimationFrame(() => {
        // 先移除所有用户块的 active 类
        this.userBlocks.forEach(block => block.classList.remove('active'));
        // 为当前用户块添加 active 类
        this.userBlocks[this.currentUserIndex].classList.add('active');
        // 更新滑块位置
        this.updateSliderPosition();
      });
    } else {
      // 如果没有用户块，直接更新滑块位置
      this.updateSliderPosition();
    }
  }
  
  // 获取utility_type对应的中文名称
  getUtilityTypeName(utilityType) {
    const typeMap = {
      'ele': '电费',
      'gas': '燃气',
      'water': '水费'
    };
    return typeMap[utilityType] || '未知';
  }
  
  // 根据utility_type更新背景图标
  updateCardBackgroundIcon(utilityType) {
    if (!this.electricityCardEl) return;
    
    // 先移除所有背景图标类
    this.electricityCardEl.classList.remove('bg-ele', 'bg-gas', 'bg-water');
    
    // 根据utility_type添加对应的背景图标类
    if (utilityType === 'ele') {
      this.electricityCardEl.classList.add('bg-ele');
    } else if (utilityType === 'gas') {
      this.electricityCardEl.classList.add('bg-gas');
    } else if (utilityType === 'water') {
      this.electricityCardEl.classList.add('bg-water');
    }
  }
  
  // 更新滑块位置
  updateSliderPosition() {
    if (!this.sliderIndicatorEl || !this.userBlocks || this.userBlocks.length === 0) return;

    const activeBlock = this.userBlocks[this.currentUserIndex];
    if (activeBlock) {
      // 使用 requestAnimationFrame 确保 DOM 已渲染
      requestAnimationFrame(() => {
        const offsetLeft = activeBlock.offsetLeft;
        const offsetWidth = activeBlock.offsetWidth;

        // 确保获取到了有效的尺寸（宽度大于0）
        if (offsetWidth > 0) {
          this.sliderIndicatorEl.style.left = `${offsetLeft}px`;
          this.sliderIndicatorEl.style.width = `${offsetWidth}px`;
        } else {
          // 如果首次渲染时宽度为0，等待下一帧再尝试
          requestAnimationFrame(() => {
            const retryOffsetLeft = activeBlock.offsetLeft;
            const retryOffsetWidth = activeBlock.offsetWidth;
            this.sliderIndicatorEl.style.left = `${retryOffsetLeft}px`;
            this.sliderIndicatorEl.style.width = `${retryOffsetWidth}px`;
          });
        }
      });
    }
  }
  
  // 确保当前用户块的 active 状态正确设置
  ensureCurrentUserActive() {
    if (!this.userBlocks || this.userBlocks.length === 0) return;
    
    // 确保当前用户索引在有效范围内
    if (this.currentUserIndex < 0 || this.currentUserIndex >= this.userBlocks.length) {
      this.currentUserIndex = 0;
    }
    
    // 先移除所有用户块的 active 类
    this.userBlocks.forEach(block => block.classList.remove('active'));
    
    // 为当前用户块添加 active 类
    this.userBlocks[this.currentUserIndex].classList.add('active');
    
    // 更新滑块位置
    this.updateSliderPosition();
  }

  /**
   * 切换用户（完整流程）
   */
  switchUser(index) {
    if (index === this.currentUserIndex) return;
    
    const blocks = Array.from(this.userBlocks);
    if (!blocks[index]) return;
    
    // 【关闭】隐藏日历/关闭模态框/销毁图表/清空动态内容
    this.closeAllUI();
    
    // 【重置】卡片回到最初状态
    this.resetCardState();
    
    // 【动画】卡片淡出效果
    if (this.electricityCardEl) {
      this.electricityCardEl.classList.add('switching');
      this.electricityCardEl.classList.remove('switching-in');
    }
    
    // 等待淡出动画完成（300ms）
    setTimeout(() => {
      // 【切换配置】加载新户的配置
      this.currentUserIndex = index;
      this.initializeCurrentUserConfig();
      
      // 添加 active 类到当前块
      blocks.forEach(block => block.classList.remove('active'));
      blocks[index].classList.add('active');
      
      // 更新滑块位置
      this.updateSliderPosition();
      
      // 【动画】卡片淡入效果
      if (this.electricityCardEl) {
        this.electricityCardEl.classList.remove('switching');
        this.electricityCardEl.classList.add('switching-in');
      }
      
      // 等待淡入动画完成（400ms）后移除动画类
      setTimeout(() => {
        if (this.electricityCardEl) {
          this.electricityCardEl.classList.remove('switching-in');
        }
      }, 400);
      
      // 【加载数据】加载新用户的数据（重要：切换用户后必须重新加载数据）
      // 等待数据加载完成后再更新显示，确保 standardData 已切换到新用户数据
      this.loadDataForCurrentUser().then(() => {
        // 数据加载完成后再更新余额显示
        this.updateBalanceDisplay();
        
        // 应用当前用户的隐藏配置
        this.applyHiddenConfig();
        
        // 【更新显示】数据加载完成后更新卡片
        this.updateCard();
        
        // 【重要】如果当前在日历视图，重新渲染日历以确保设备历史数据标记正确显示
        if (this.isCalendarView) {
          this.updateCalendar();
        }
      });
    });
  }
  
  // 关闭所有UI元素
  closeAllUI() {
    // 如果当前是日历视图，调用 hideCalendarView() 来完整关闭
    if (this.isCalendarView) {
      this.hideCalendarView();
    }
    
    // 关闭模态框
    this.closeAllModals();
    
    // 销毁图表实例（但不销毁ECharts本身）
    this.destroyCharts();
    
    // 清除阶梯指示器的动态元素（重要：切换用户时必须清除旧指示器）
    if (this.tiersContainerEl) {
      // 移除红色竖线指示器
      const redLines = this.tiersContainerEl.querySelectorAll('.red-line-indicator');
      redLines.forEach(line => line.remove());
      
      // 移除倒三角指示器
      const triangles = this.tiersContainerEl.querySelectorAll('.current-indicator-triangle');
      triangles.forEach(triangle => triangle.remove());
    }
  }
  
  // 重置卡片状态
  resetCardState() {
    // 清空数据缓存中的当前用户数据
    const cacheKey = this.getCurrentCacheKey();
    if (this._dataCache.has(cacheKey)) {
      this._dataCache.delete(cacheKey);
    }
    
    // 重置标准数据
    this.standardData = {
      dayUsage: [],
      monthUsage: [],
      yearUsage: [],
      payRecords: [],
      unit: ''
    };
    
    // 重置历史数据加载标志
    this.historicalDataLoaded = false;
  }
  
  // 关闭所有模态框
  closeAllModals() {
    // 关闭日历日期详情模态框（现在在document.body中）
    if (this.dayModalEl) {
      this.dayModalEl.style.display = 'none';
    }
    
    // 关闭缴费历史模态框（现在在document.body中）
    if (this.payHistoryModalEl) {
      this.payHistoryModalEl.style.display = 'none';
    }
  }
  
  // 销毁图表（保留ECharts库）
  destroyCharts() {
    // 销毁年视图图表
    if (this.yearChart) {
      this.yearChart.dispose();
      this.yearChart = null;
    }
    
    // 销毁月视图图表
    if (this.monthChart) {
      this.monthChart.dispose();
      this.monthChart = null;
    }
    
    // 销毁日视图图表
    if (this.dayChart) {
      this.dayChart.dispose();
      this.dayChart = null;
    }
    
    // 销毁缴费方式饼图
    if (this.paySourceChart) {
      this.paySourceChart.dispose();
      this.paySourceChart = null;
    }
    
    // 销毁热力图
    if (this.yearHeatmapChart) {
      this.yearHeatmapChart.dispose();
      this.yearHeatmapChart = null;
    }

    // 销毁动态排名柱状图
    this.stopBarRacing();
    if (this.barRacingChart) {
      this.barRacingChart.dispose();
      this.barRacingChart = null;
    }
  }

  /**
   * 计算无分时用电量（usage_ele_no）
   */
  calculateUsageEleNo(data) {
    const valley = this.safeParseFloat(data.usage_ele_valley);
    const peak = this.safeParseFloat(data.usage_ele_peak);
    const tip = this.safeParseFloat(data.usage_ele_tip);
    const norm = this.safeParseFloat(data.usage_ele_norm);
    const totalUsage = this.safeParseFloat(data.total_usage);
    
    const sumTime = valley + peak + tip + norm;
    
    // 四舍五入到2位小数，避免浮点数精度问题
    const sumTimeRounded = Math.round(sumTime * 100) / 100;
    const totalUsageRounded = Math.round(totalUsage * 100) / 100;
    
    let noValue = 0.0;
    
    if (Math.abs(totalUsageRounded - sumTimeRounded) < 0.01) {
      // 相等，无未分类电量
      noValue = 0.0;
    } else if (totalUsageRounded > sumTimeRounded) {
      // 总用量大于分时总和，差额为未分类
      noValue = parseFloat((totalUsageRounded - sumTimeRounded).toFixed(2));
    } else {
      // 数据错误：总用量小于分时总和
      this.debugWarn(`数据错误: user=${data.user}, time=${data.time}, total_usage(${totalUsageRounded}) < 分时总和(${sumTimeRounded})`);
      noValue = 0.0;
    }
    
    return noValue;
  }
  
  /**
   * 转换日用量数据为统一格式
   */
  convertDayList(daylist, user = 'ele_01') {
    if (!Array.isArray(daylist)) return [];
    
    // 获取字段映射（如果有）
    const mapping = this.fieldMapping || {};
    const dateField = mapping.date || 'day';
    const usageField = mapping.usage;
    const amountField = mapping.amount;
    
    return daylist.map(item => {
      let converted;
      
      if (this.utilityType === 'ele') {
        // 电力类型使用原有字段
        converted = {
          user: user,
          utility_type: this.utilityType,
          data_category: 'usage',
          date_granularity: 'day',
          time: item.day || '',
          data_source: 'entity',
          total_usage: this.safeParseFloat(item.dayEleNum),
          total_amount: this.safeParseFloat(item.dayEleCost),
          unit: item.unit || this.getUnitByUtilityType(this.utilityType),
          usage_ele_valley: this.safeParseFloat(item.dayVPq),
          usage_ele_peak: this.safeParseFloat(item.dayPPq),
          usage_ele_tip: this.safeParseFloat(item.dayTPq),
          usage_ele_norm: this.safeParseFloat(item.dayNPq)
        };
      } else {
        // 非电力类型使用字段映射
        const dateValue = item[dateField] || '';
        // 处理日期字符串，移除可能的双引号
        const cleanDate = typeof dateValue === 'string' ? dateValue.replace(/"/g, '') : dateValue;
        
        converted = {
          user: user,
          utility_type: this.utilityType,
          data_category: 'usage',
          date_granularity: 'day',
          time: cleanDate,
          data_source: 'entity',
          total_usage: this.safeParseFloat(usageField ? item[usageField] : item.dayEleNum),
          total_amount: this.safeParseFloat(amountField ? item[amountField] : item.dayEleCost),
          unit: item.unit || this.getUnitByUtilityType(this.utilityType),
          usage_ele_valley: 0,
          usage_ele_peak: 0,
          usage_ele_tip: 0,
          usage_ele_norm: 0
        };
      }
      
      converted.usage_ele_no = this.calculateUsageEleNo(converted);
      
      return converted;
    });
  }
  
  /**
   * 转换月用量数据为统一格式
   */
  convertMonthList(monthlist, user = 'ele_01') {
    if (!Array.isArray(monthlist)) return [];
    
    return monthlist.map(item => {
      const converted = {
        user: user,
        utility_type: this.utilityType,
        data_category: 'usage',
        date_granularity: 'month',
        time: item.month || '',
        data_source: 'entity',
        total_usage: this.safeParseFloat(item.monthEleNum),
        total_amount: this.safeParseFloat(item.monthEleCost),
        unit: item.unit || this.getUnitByUtilityType(this.utilityType),
        usage_ele_valley: this.safeParseFloat(item.monthVPq),
        usage_ele_peak: this.safeParseFloat(item.monthPPq),
        usage_ele_tip: this.safeParseFloat(item.monthTPq),
        usage_ele_norm: this.safeParseFloat(item.monthNPq)
      };
      
      converted.usage_ele_no = this.calculateUsageEleNo(converted);
      
      return converted;
    });
  }
  
  /**
   * 转换年用量数据为统一格式
   */
  convertYearList(yearlist, user = 'ele_01') {
    if (!Array.isArray(yearlist)) return [];
    
    return yearlist.map(item => {
      const converted = {
        user: user,
        utility_type: this.utilityType,
        data_category: 'usage',
        date_granularity: 'year',
        time: item.year || '',
        data_source: 'entity',
        total_usage: this.safeParseFloat(item.yearEleNum),
        total_amount: this.safeParseFloat(item.yearEleCost),
        unit: item.unit || this.getUnitByUtilityType(this.utilityType),
        usage_ele_valley: this.safeParseFloat(item.yearVPq),
        usage_ele_peak: this.safeParseFloat(item.yearPPq),
        usage_ele_tip: this.safeParseFloat(item.yearTPq),
        usage_ele_norm: this.safeParseFloat(item.yearNPq)
      };
      
      converted.usage_ele_no = this.calculateUsageEleNo(converted);
      
      return converted;
    });
  }
  
  /**
   * 从统一格式数据中提取分时数据用于图表
   */
  extractTimeDistributionFromStandard(standardData) {
    if (!standardData) return [];
    
    const distributions = [];
    const timeTypes = [
      { key: 'usage_ele_tip', name: '尖', colorClass: 'time-segment-tip' },
      { key: 'usage_ele_peak', name: '峰', colorClass: 'time-segment-peak' },
      { key: 'usage_ele_norm', name: '平', colorClass: 'time-segment-normal' },
      { key: 'usage_ele_valley', name: '谷', colorClass: 'time-segment-valley' }
    ];
    
    let hasNonZeroValue = false;
    
    for (const type of timeTypes) {
      const value = this.safeParseFloat(standardData[type.key]);
      
      if (value > 0) {
        hasNonZeroValue = true;
        distributions.push({
          name: type.name,
          colorClass: type.colorClass,
          value: value,
          percentage: 0,
          width: 0
        });
      }
    }
    
    if (!hasNonZeroValue) return [];
    
    const sum = distributions.reduce((total, dist) => total + dist.value, 0);
    
    distributions.forEach(dist => {
      dist.percentage = sum > 0 ? (dist.value / sum * 100) : 0;
      dist.width = dist.percentage;
    });
    
    return distributions;
  }
  
  // 从标准格式获取当前月份数据
  getCurrentMonthStandardData() {
    const currentMonthStr = this.getCurrentMonthStr();
    const currentMonthData = this.standardData.monthUsage.find(item => item.time === currentMonthStr);
    
    if (currentMonthData) {
      return currentMonthData;
    }
    
    // 返回默认值
    return {
      user: 'ele_01',
      utility_type: this.utilityType,
      data_category: 'usage',
      date_granularity: 'month',
      time: currentMonthStr,
      data_source: 'entity',
      total_usage: 0,
      total_amount: 0,
      unit: this.standardData.unit || '',
      usage_ele_valley: 0,
      usage_ele_peak: 0,
      usage_ele_tip: 0,
      usage_ele_norm: 0,
      usage_ele_no: 0
    };
  }

  // 从标准格式获取上月数据
  getLastMonthStandardData() {
    const now = new Date();
    const lastMonthDate = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const lastMonthStr = `${lastMonthDate.getFullYear()}-${String(lastMonthDate.getMonth() + 1).padStart(2, '0')}`;
    
    const lastMonthData = this.standardData.monthUsage.find(item => item.time === lastMonthStr);
    
    if (lastMonthData) {
      return lastMonthData;
    }
    
    // 如果找不到，返回第二个数据（如果存在）
    if (this.standardData.monthUsage.length > 1) {
      return this.standardData.monthUsage[1];
    }
    
    // 返回默认值
    return {
      user: 'ele_01',
      utility_type: this.utilityType,
      data_category: 'usage',
      date_granularity: 'month',
      time: lastMonthStr,
      data_source: 'entity',
      total_usage: 0,
      total_amount: 0,
      unit: this.standardData.unit || '',
      usage_ele_valley: 0,
      usage_ele_peak: 0,
      usage_ele_tip: 0,
      usage_ele_norm: 0,
      usage_ele_no: 0
    };
  }

  // 从标准格式获取当前年度数据
  getCurrentYearStandardData() {
    const currentYear = new Date().getFullYear().toString();
    
    const currentYearData = this.standardData.yearUsage.find(item => item.time === currentYear);
    
    if (currentYearData) {
      return currentYearData;
    }
    
    // 如果找不到，返回第一个年份数据（如果存在）
    if (this.standardData.yearUsage.length > 0) {
      return this.standardData.yearUsage[0];
    }
    
    // 返回默认值
    return {
      user: 'ele_01',
      utility_type: this.utilityType,
      data_category: 'usage',
      date_granularity: 'year',
      time: currentYear,
      data_source: 'entity',
      total_usage: 0,
      total_amount: 0,
      unit: this.standardData.unit || '',
      usage_ele_valley: 0,
      usage_ele_peak: 0,
      usage_ele_tip: 0,
      usage_ele_norm: 0,
      usage_ele_no: 0
    };
  }
  
  // 配色方案定义
  static get COLOR_SCHEMES() {
    return {
      // 亮色主题方案 - 主要使用白色系
      light: {
        '--button-color-active': 'rgba(0, 0, 0, 0.8)',
        '--button-active-text-color': 'rgb(255, 255, 255)',
        '--selec-button-bg-color': 'rgba(0, 0, 0, 0.12)',
        '--button-color': 'rgba(0, 0, 0, 0.6)',
        '--text-color': 'rgba(0, 0, 0, 0.8)',
        '--svg-icon-color': 'rgba(0, 0, 0, 0.8)',
        '--card-primary-hover': 'rgba(0, 0, 0, 0.9)',
        '--button-primary-transparent': 'rgba(0, 0, 0, 0.1)',
        '--card-on-state-hover': 'rgba(0, 0, 0, 0.2)',
        '--card-button-bg': 'rgba(0, 0, 0, 0.05)',
        '--card-name-color': 'rgba(0, 0, 0, 0.8)',
        '--card-value-color': 'rgba(0, 0, 0, 0.8)',
        '--card-slider-value-color': 'rgba(0, 0, 0, 0.8)',
        '--card-bg': 'rgb(255, 255, 255)',
        '--date-circle-bg':  'rgba(0, 0, 0, 0.12)',
        '--date-circle-color':'rgba(0, 0, 0, 0.8)',
        '--usage-color': '#F9D505',
        '--money-color': '#804AFF',
        '--calendar-line-color': 'rgba(0, 0, 0, 0.12)',
        '--tooltip-bg': 'var(--card-bg)',
        '--tooltip-text-color': 'var(--text-color)',
        '--tooltip-border-color': 'var(--button-primary-transparent)',
        '--tooltip-highlight-bg': 'var(--button-color-active)'
      },
      // 暗色主题方案 - 主要使用黑色系
      dark: {
        '--button-color-active': 'rgba(255, 255, 255, 0.4)',
        '--button-active-text-color': 'rgb(255, 255, 255)',
        '--text-color': 'rgba(255, 255, 255, 0.6)',
        '--svg-icon-color': 'rgba(255, 255, 255, 0.6)',
        '--button-color': 'rgba(255, 255, 255, 0.6)',
        '--card-primary-hover': 'rgba(255, 255, 255, 0.9)',
        '--button-primary-transparent': 'rgba(255, 255, 255, 0.1)',
        '--card-on-state-hover': 'rgba(255, 255, 255, 0.2)',
        '--card-button-bg': 'rgba(0, 0, 0, 0.12)',
        '--card-name-color': 'rgba(255, 255, 255, 0.8)',
        '--card-value-color': 'rgba(255, 255, 255, 0.8)',
        '--card-slider-value-color': 'rgba(255, 255, 255, 0.8)',
        '--card-bg': 'rgb(50, 50, 50)',
        '--date-circle-bg': 'rgba(0, 0, 0, 0.12)',
        '--date-circle-color': 'white',
        '--usage-color': '#F9D505',
        '--money-color': '#804AFF',
        '--calendar-line-color': 'rgba(0, 0, 0, 0.12)',
        '--tooltip-bg': 'var(--card-bg)',
        '--tooltip-text-color': 'var(--text-color)',
        '--tooltip-border-color': 'var(--button-primary-transparent)',
        '--tooltip-highlight-bg': 'var(--button-color-active)'
      },
      // 纯黑色主题方案 - 主要使用纯黑色
      black: {
        '--button-color-active': 'rgb(255, 255, 255)',
        '--button-active-text-color': 'rgb(0, 0, 0)',
        '--text-color': 'rgb(255, 255, 255)',
        '--svg-icon-color': 'rgba(255, 255, 255, 0.6)',
        '--button-color': 'rgb(255, 255, 255)',
        '--card-primary-hover': 'rgba(255, 255, 255, 0.9)',
        '--button-primary-transparent': 'rgba(255, 255, 255, 0.1)',
        '--card-on-state-hover': 'rgba(255, 255, 255, 0.2)',
        '--card-button-bg': 'rgba(255, 255, 255, 0.1)',
        '--card-name-color': 'rgba(255, 255, 255, 0.8)',
        '--card-value-color': 'rgba(255, 255, 255, 0.8)',
        '--card-slider-value-color': 'rgba(255, 255, 255, 0.8)',
        '--card-bg': 'rgb(0, 0, 0)',
        '--date-circle-bg': 'rgba(0, 0, 0, 0.12)',
        '--date-circle-color': 'white',
        '--usage-color': '#F9D505',
        '--money-color': '#804AFF',
        '--calendar-line-color': 'rgba(255, 255, 255, 0.1)',
        '--tooltip-bg': 'var(--card-bg)',
        '--tooltip-text-color': 'var(--text-color)',
        '--tooltip-border-color': 'var(--button-primary-transparent)',
        '--tooltip-highlight-bg': 'var(--button-color-active)'
      },    
      // 深灰主题方案 - 主要使用深灰色 (#222222)
      darkgray: {
        '--button-color-active': 'rgb(255, 255, 255)',
        '--button-active-text-color': 'rgb(34, 34, 34)',
        '--text-color': 'rgb(255, 255, 255)',
        '--svg-icon-color': 'rgba(255, 255, 255, 0.6)',
        '--button-color': 'rgb(255, 255, 255)',
        '--card-primary-hover': 'rgba(255, 255, 255, 0.9)',
        '--button-primary-transparent': 'rgba(255, 255, 255, 0.1)',
        '--card-on-state-hover': 'rgba(255, 255, 255, 0.2)',
        '--card-button-bg': 'rgba(255, 255, 255, 0.1)',
        '--card-name-color': 'rgba(255, 255, 255, 0.8)',
        '--card-value-color': 'rgba(255, 255, 255, 0.8)',
        '--card-slider-value-color': 'rgba(255, 255, 255, 0.8)',
        '--card-bg': 'rgb(34, 34, 34)',
        '--date-circle-bg': 'rgba(0, 0, 0, 0.12)',
        '--date-circle-color': 'white',
        '--usage-color': '#F9D505',
        '--money-color': '#804AFF',
        '--calendar-line-color': 'rgba(255, 255, 255, 0.1)',
        '--tooltip-bg': 'var(--card-bg)',
        '--tooltip-text-color': 'var(--text-color)',
        '--tooltip-border-color': 'var(--button-primary-transparent)',
        '--tooltip-highlight-bg': 'var(--button-color-active)'
      },      
      // 国家电网主题方案 - 主要使用国家电网的配色
      power: {
        '--button-color-active': '#2395f5',
        '--button-active-text-color': 'rgb(255, 255, 255)',
        '--button-color': '#2395f5',
        '--button-text-color': '#242424',
        '--text-color': '#242424',
        '--svg-icon-color': '#242424',
        '--card-primary-hover': '#2196f3',
        '--button-primary-transparent': 'rgba(255, 255, 255, 0.1)',
        '--card-on-state-hover': 'rgba(255, 255, 255, 0.2)',
        '--card-button-bg': 'rgba(255, 255, 255, 0.3)',
        '--card-name-color': 'rgba(0, 0, 0, 0.8)',
        '--card-value-color': '#ff5722',
        '--card-slider-value-color': 'rgba(255, 255, 255, 0.8)',
        '--card-bg': 'linear-gradient(135deg, rgba(204, 244, 243, 1) 0%, rgba(177, 233, 234, 1) 100%)',
        '--date-circle-bg': 'rgba(255, 107, 107, 1)',
        '--date-circle-color': 'white',
        '--usage-color': '#F9D505',
        '--money-color': '#804AFF',
        '--tooltip-bg': 'rgba(204, 244, 243, 1)',
        '--tooltip-text-color': 'var(--text-color)',
        '--calendar-line-color': 'rgba(0, 0, 0, 0.12)',
        '--tooltip-border-color': 'var(--button-primary-transparent)',
        '--tooltip-highlight-bg': 'var(--button-color-active)'
      },
      // 半透明主题方案 - 暗色半透明模式
      transparent: {
        '--button-color-active': 'rgba(255, 255, 255, 0.8)',
        '--button-active-text-color': 'rgb(255, 255, 255)',
        '--button-color': 'rgba(255, 255, 255, 0.6)',
        '--text-color': 'rgba(255, 255, 255, 0.6)', 
        '--svg-icon-color': 'rgba(255, 255, 255, 0.6)', 
        '--card-primary-hover': 'rgba(255, 255, 255, 0.9)',
        '--button-primary-transparent': 'rgba(255, 255, 255, 0.1)',
        '--card-on-state-hover': 'rgba(255, 255, 255, 0.2)',
        '--card-button-bg': 'rgba(255, 255, 255, 0.05)',
        '--card-name-color': 'rgba(220, 220, 220, 1)',
        '--card-value-color': 'rgba(220, 220, 220, 1)',
        '--card-slider-value-color': 'rgba(0, 0, 0, 0.8)',
        '--card-bg': 'rgba(0, 0, 0, 0.3)',
        '--date-circle-bg': 'rgba(255, 107, 107, 1)',
        '--date-circle-color': 'white',
        '--usage-color': '#F9D505',
        '--money-color': '#804AFF',
        '--calendar-line-color': 'rgba(0, 0, 0, 0.12)',
        '--tooltip-bg': 'var(--card-bg)',
        '--tooltip-text-color': 'var(--text-color)',
        '--tooltip-border-color': 'var(--button-primary-transparent)',
        '--tooltip-highlight-bg': 'var(--button-color-active)'
      },
      // 蓝色主题 - 完全使用蓝色系
      blue: {
        '--button-color-active': 'rgba(96, 165, 250, 0.9)',
        '--button-active-text-color': 'rgb(255, 255, 255)',
        '--button-color': 'rgba(96, 165, 250, 0.7)',
        '--text-color': 'rgba(96, 165, 250, 0.7)',
        '--svg-icon-color': 'rgba(96, 165, 250, 0.7)',
        '--card-primary-hover': 'rgba(59, 130, 246, 0.9)',
        '--button-primary-transparent': 'rgba(96, 165, 250, 0.1)',
        '--card-on-state-hover': 'rgba(96, 165, 250, 0.2)',
        '--card-button-bg': 'rgba(96, 165, 250, 0.1)',
        '--card-name-color': 'rgba(96, 165, 250, 0.8)',
        '--card-value-color': 'rgba(15, 123, 255, 1)',
        '--card-slider-value-color': 'rgba(96, 165, 250, 0.8)',
        '--card-bg': 'rgb(225, 245, 254)',
        '--date-circle-bg': 'rgba(96, 165, 250, 0.8)',
        '--date-circle-color': 'white',
        '--usage-color': '#F9D505',
        '--money-color': '#804AFF',
        '--calendar-line-color': 'rgba(0, 0, 0, 0.12)',
        '--tooltip-bg': 'var(--card-bg)',
        '--tooltip-text-color': 'var(--text-color)',
        '--tooltip-border-color': 'var(--button-primary-transparent)',
        '--tooltip-highlight-bg': 'var(--button-color-active)'
      },
      // 绿色主题 - 完全使用绿色系
      green: {
        '--button-color-active': 'rgba(52, 211, 153, 0.9)',
        '--button-active-text-color': 'rgb(255, 255, 255)',
        '--button-color': 'rgba(52, 211, 153, 0.7)',
        '--text-color': 'rgba(52, 211, 153, 0.7)',
        '--svg-icon-color': 'rgba(52, 211, 153, 0.7)',
        '--card-primary-hover': 'rgba(16, 185, 129, 0.9)',
        '--button-primary-transparent': 'rgba(52, 211, 153, 0.1)',
        '--card-on-state-hover': 'rgba(52, 211, 153, 0.2)',
        '--card-button-bg': 'rgba(240, 253, 244, 1)',
        '--card-name-color': 'rgba(52, 211, 153, 0.8)',
        '--card-value-color': 'rgba(52, 211, 153, 0.8)',
        '--card-slider-value-color': 'rgba(52, 211, 153, 0.8)',
        '--card-bg': 'rgb(232, 255, 234)',
        '--date-circle-bg': 'rgba(52, 211, 153, 0.8)',
        '--date-circle-color': 'white',
        '--usage-color': '#F9D505',
        '--money-color': '#804AFF',
        '--calendar-line-color': 'rgba(0, 0, 0, 0.12)',
        '--tooltip-bg': 'var(--card-bg)',
        '--tooltip-text-color': 'var(--text-color)',
        '--tooltip-border-color': 'var(--button-primary-transparent)',
        '--tooltip-highlight-bg': 'var(--button-color-active)'
      },
      // 红色主题 - 完全使用红色系
      red: {
        '--button-color-active': 'rgba(248, 113, 113, 0.9)',
        '--button-active-text-color': 'rgb(255, 255, 255)',
        '--button-color': 'rgba(248, 113, 113, 0.7)',
        '--text-color':  'rgba(248, 113, 113, 0.7)',
        '--svg-icon-color': 'rgba(248, 113, 113, 0.7)',
        '--card-primary-hover': 'rgba(239, 68, 68, 0.9)',
        '--button-primary-transparent': 'rgba(248, 113, 113, 0.1)',
        '--card-on-state-hover': 'rgba(248, 113, 113, 0.2)',
        '--card-button-bg': 'rgba(254, 242, 242, 1)',
        '--card-name-color': 'rgba(248, 113, 113, 0.8)',
        '--card-value-color': 'rgba(248, 113, 113, 0.8)',
        '--card-slider-value-color': 'rgba(248, 113, 113, 0.8)',
        '--card-bg': 'rgb(255, 235, 238)',
        '--date-circle-bg': 'rgba(248, 113, 113, 0.8)',
        '--date-circle-color': 'white',
        '--usage-color': '#F9D505',
        '--money-color': '#804AFF',
        '--calendar-line-color': 'rgba(0, 0, 0, 0.12)',
        '--tooltip-bg': 'var(--card-bg)',
        '--tooltip-text-color': 'var(--text-color)',
        '--tooltip-border-color': 'var(--button-primary-transparent)',
        '--tooltip-highlight-bg': 'var(--button-color-active)'
      },
      // 紫色主题 - 完全使用紫色系
      purple: {
        '--button-color-active': 'rgba(192, 132, 252, 0.9)',
        '--button-active-text-color': 'rgb(255, 255, 255)',
        '--button-color': 'rgba(192, 132, 252, 0.7)',
        '--text-color': 'rgba(192, 132, 252, 0.7)',
        '--svg-icon-color': 'rgba(192, 132, 252, 0.7)',
        '--card-primary-hover': 'rgba(168, 85, 247, 0.9)',
        '--button-primary-transparent': 'rgba(192, 132, 252, 0.1)',
        '--card-on-state-hover': 'rgba(192, 132, 252, 0.2)',
        '--card-button-bg': 'rgba(250, 245, 255, 1)',
        '--card-name-color': 'rgba(192, 132, 252, 0.8)',
        '--card-value-color': 'rgba(192, 132, 252, 0.8)',
        '--card-slider-value-color': 'rgba(192, 132, 252, 0.8)',
        '--card-bg': 'rgb(243, 229, 245)',
        '--date-circle-bg': 'rgba(192, 132, 252, 0.8)',
        '--date-circle-color': 'white',
        '--usage-color': '#F9D505',
        '--money-color': '#804AFF',
        '--calendar-line-color': 'rgba(0, 0, 0, 0.12)',
        '--tooltip-bg': 'var(--card-bg)',
        '--tooltip-text-color': 'var(--text-color)',
        '--tooltip-border-color': 'var(--button-primary-transparent)',
        '--tooltip-highlight-bg': 'var(--button-color-active)'
      },
      // 黄色主题 - 完全使用黄色系
      yellow: {
        '--button-color-active': 'rgba(251, 191, 36, 0.9)',
        '--button-active-text-color': 'rgb(255, 255, 255)',
        '--button-color': 'rgba(251, 191, 36, 0.7)',
        '--text-color': 'rgba(251, 191, 36, 0.7)', 
        '--svg-icon-color': 'rgba(251, 191, 36, 0.7)', 
        '--card-primary-hover': 'rgba(245, 158, 11, 0.9)',
        '--button-primary-transparent': 'rgba(251, 191, 36, 0.1)',
        '--card-on-state-hover': 'rgba(251, 191, 36, 0.2)',
        '--card-button-bg': 'rgba(255, 244, 211, 0.5)',
        '--card-name-color': 'rgba(251, 191, 36, 0.8)',
        '--card-value-color': 'rgba(251, 191, 36, 0.8)',
        '--card-slider-value-color': 'rgba(251, 191, 36, 0.8)',
        '--card-bg': 'rgb(255, 253, 231)',
        '--date-circle-bg': 'rgba(251, 191, 36, 0.8)',
        '--date-circle-color': 'white',
        '--usage-color': '#F9D505',
        '--money-color': '#804AFF',
        '--tooltip-bg': 'var(--card-bg)',
        '--calendar-line-color': 'rgba(0, 0, 0, 0.12)',
        '--tooltip-text-color': 'var(--text-color)',
        '--tooltip-border-color': 'var(--button-primary-transparent)',
        '--tooltip-highlight-bg': 'var(--button-color-active)'
      },
      // 青色主题 - 完全使用青色系
      cyan: {
        '--button-color-active': 'rgba(34, 211, 238, 0.9)',
        '--button-active-text-color': 'rgb(255, 255, 255)',
        '--button-color': 'rgba(34, 211, 238, 0.7)',
        '--text-color': 'rgba(34, 211, 238, 0.7)',
        '--svg-icon-color': 'rgba(34, 211, 238, 0.7)',
        '--card-primary-hover': 'rgba(6, 182, 212, 0.9)',
        '--button-primary-transparent': 'rgba(34, 211, 238, 0.1)',
        '--card-on-state-hover': 'rgba(34, 211, 238, 0.2)',
        '--card-button-bg': 'rgba(236, 254, 255, 0.5)',
        '--card-name-color': 'rgba(34, 211, 238, 0.8)',
        '--card-value-color': 'rgba(34, 211, 238, 0.8)',
        '--card-slider-value-color': 'rgba(34, 211, 238, 0.8)',
        '--card-bg': 'rgb(224, 247, 250)',
        '--date-circle-bg': 'rgba(34, 211, 238, 0.8)',
        '--date-circle-color': 'white',
        '--usage-color': '#F9D505',
        '--money-color': '#804AFF',
        '--calendar-line-color': 'rgba(0, 0, 0, 0.12)',
        '--tooltip-bg': 'var(--card-bg)',
        '--tooltip-text-color': 'var(--text-color)',
        '--tooltip-border-color': 'var(--button-primary-transparent)',
        '--tooltip-highlight-bg': 'var(--button-color-active)'
      },
      // 粉色主题 - 完全使用粉色系
      pink: {
        '--button-color-active': 'rgba(249, 168, 212, 0.9)',
        '--button-active-text-color': 'rgb(255, 255, 255)',
        '--button-color': 'rgba(249, 168, 212, 0.7)',
        '--text-color': 'rgba(249, 168, 212, 0.7)', 
        '--svg-icon-color': 'rgba(249, 168, 212, 0.7)', 
        '--card-primary-hover': 'rgba(244, 114, 182, 0.9)',
        '--button-primary-transparent': 'rgba(249, 168, 212, 0.1)',
        '--card-on-state-hover': 'rgba(249, 168, 212, 0.2)',
        '--card-button-bg': 'rgba(253, 242, 248, 1)',
        '--card-name-color': 'rgba(249, 168, 212, 0.8)',
        '--card-value-color': 'rgba(249, 168, 212, 0.8)',
        '--card-slider-value-color': 'rgba(249, 168, 212, 0.8)',
        '--card-bg': 'rgb(252, 228, 236)',
        '--date-circle-bg': 'rgba(249, 168, 212, 0.8)',
        '--date-circle-color': 'white',
        '--usage-color': '#F9D505',
        '--money-color': '#804AFF',
        '--calendar-line-color': 'rgba(0, 0, 0, 0.12)',
        '--tooltip-bg': 'var(--card-bg)',
        '--tooltip-text-color': 'var(--text-color)',
        '--tooltip-border-color': 'var(--button-primary-transparent)',
        '--tooltip-highlight-bg': 'var(--button-color-active)'          
      },
      // 橙色主题 - 完全使用橙色系
      orange: {
        '--button-color-active': 'rgba(251, 146, 60, 0.9)',
        '--button-active-text-color': 'rgb(255, 255, 255)',
        '--button-color': 'rgba(251, 146, 60, 0.7)',
        '--text-color': 'rgba(251, 146, 60, 0.7)',
        '--svg-icon-color': 'rgba(251, 146, 60, 0.7)', 
        '--card-primary-hover': 'rgba(249, 115, 22, 0.9)',
        '--button-primary-transparent': 'rgba(251, 146, 60, 0.1)',
        '--card-on-state-hover': 'rgba(251, 146, 60, 0.2)',
        '--card-button-bg': 'rgba(255, 247, 237, 1)',
        '--card-name-color': 'rgba(251, 146, 60, 0.8)',
        '--card-value-color': 'rgba(251, 146, 60, 0.8)',
        '--card-slider-value-color': 'rgba(251, 146, 60, 0.8)',
        '--card-bg': 'rgb(255, 243, 224)',
        '--date-circle-bg': 'rgba(251, 146, 60, 0.8)',
        '--date-circle-color': 'white',
        '--usage-color': '#F9D505',
        '--money-color': '#804AFF',
        '--calendar-line-color': 'rgba(0, 0, 0, 0.12)',
        '--tooltip-bg': 'var(--card-bg)',
        '--tooltip-text-color': 'var(--text-color)',
        '--tooltip-border-color': 'var(--button-primary-transparent)',
        '--tooltip-highlight-bg': 'var(--button-color-active)'
      }
    };
  }

  // ==================== 主题相关方法（优化版） ====================
  // 解析暗色/亮色主题配置
  parseDarkLightTheme() {
    const darkLightTheme = this._config?.dark_light_theme;
    if (darkLightTheme && typeof darkLightTheme === 'string') {
      const parts = darkLightTheme.split(',').map(p => p.trim());
      if (parts.length >= 2) {
        return [parts[0] || 'black', parts[1] || 'light'];
      }
    }
    return ['black', 'light']; // 默认值
  }

  // 根据时间判断主题（白天6-18点亮色，其他时间暗色）
  getThemeByTime() {
    const hour = new Date().getHours();
    const [darkTheme, lightTheme] = this.parseDarkLightTheme();
    return (hour >= 6 && hour < 18) ? lightTheme : darkTheme;
  }

  // 获取系统主题
  getSystemTheme() {
    const [darkTheme, lightTheme] = this.parseDarkLightTheme();
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return darkTheme;
    }
    return lightTheme; // 默认亮色
  }

  // 设置主题监听器
  setupThemeListeners() {
    // 如果已经设置了监听器，先清理
    if (this._themeObserver) {
      this._themeObserver.disconnect();
    }
    
    // 监听主题实体变化（在hass设置时触发）
  }

  // 停止主题定时器
  stopThemeTimer() {
    if (this.themeTimer) {
      clearInterval(this.themeTimer);
      this.themeTimer = null;
    }
  }
  
  // 停止手机主题监听器
  stopPhoneThemeListener() {
    this.toggleThemeListener(false);
  }
  
  // 启动或关闭主题监听器
  toggleThemeListener(enable = true) {
    // 停止主题定时器
    this.stopThemeTimer();
    
    if (this.systemThemeMediaQuery) {
      if (this.systemThemeMediaQuery.removeEventListener) {
        this.systemThemeMediaQuery.removeEventListener('change', this.systemThemeChangeHandler);
      }
      this.systemThemeMediaQuery = null;
    }

    if (enable) {
      // 设置系统主题监听
      if (window.matchMedia) {
        this.systemThemeMediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        this.systemThemeMediaQuery.addEventListener('change', (e) => {
          const themeName = e.matches ? this.parseDarkLightTheme()[0] : this.parseDarkLightTheme()[1];
          this.applyThemeInternal(themeName);
        });
      }
      
      // 启动时间主题定时器
      this.themeTimer = setInterval(() => {
        const currentTheme = this.getThemeByTime();
        if (this.lastThemeName !== currentTheme) {
          this.lastThemeName = currentTheme;
          this.lastThemeUpdate = Date.now();
          this.applyThemeInternal(currentTheme);
        }
      }, 60000);
    }
  }

  // 应用主题变量到根元素和全局作用域（供tooltip和模态框使用）
  applyThemeVariables(themeName) {
    const theme = ElectricityInfoCard.COLOR_SCHEMES[themeName] || ElectricityInfoCard.COLOR_SCHEMES.light;
    const root = this.electricityCardEl;
    
    // 应用所有CSS变量到卡片元素
    Object.keys(theme).forEach(key => {
      root.style.setProperty(key, theme[key]);
    });
    
    // 同时应用到documentElement，让全局tooltip和模态框可以访问这些变量
    if (document.documentElement) {
      Object.keys(theme).forEach(key => {
        document.documentElement.style.setProperty(key, theme[key]);
      });
    }
  }

  // 统一应用主题
  applyThemeInternal(themeName) {
    // 移除所有主题类
    const themeClasses = ['dark', 'light', 'transparent', 'blue', 'green', 'red', 
                         'purple', 'yellow', 'cyan', 'pink', 'orange', 'power', 'darkgray'];
    this.electricityCardEl.classList.remove(...themeClasses.map(t => t + '-theme'));
    
    // 应用主题变量和类
    this.applyThemeVariables(themeName);
    this.electricityCardEl.classList.add(themeName + '-theme');
  }

  // 处理特殊主题模式（复用逻辑）
  handleSpecialThemeMode(theme) {
    const [darkTheme, lightTheme] = this.parseDarkLightTheme();
    
    if (theme === 'off') return { themeName: darkTheme, needsListener: false };
    if (theme === 'on') return { themeName: lightTheme, needsListener: false };
    if (theme === 'time') return { themeName: this.getThemeByTime(), needsListener: true };
    if (theme === 'phone') return { themeName: this.getSystemTheme(), needsListener: true };
    
    return null;
  }

  // 处理实体主题配置
  handleEntityTheme(theme) {
    if (this._hass && this._hass.states[theme]) {
      return this.determineTheme(this._hass.states[theme].state);
    }
    return null;
  }

  // 根据配置确定主题（优化后的统一处理）
  determineTheme(theme) {
    // 处理特殊模式
    const specialMode = this.handleSpecialThemeMode(theme);
    if (specialMode) return specialMode.themeName;
    
    // 处理对象配置
    if (typeof theme === 'object' && theme !== null) {
      if (theme.value && ElectricityInfoCard.COLOR_SCHEMES[theme.value]) {
        return theme.value;
      }
      if (theme.entity && this._hass) {
        const entityTheme = this.handleEntityTheme(theme.entity);
        if (entityTheme) return entityTheme;
      }
    }
    
    // 处理字符串（实体或主题名）
    if (typeof theme === 'string') {
      // 检查是否是实体
      const entityTheme = this.handleEntityTheme(theme);
      if (entityTheme) return entityTheme;
      
      // 检查是否是预定义主题
      if (ElectricityInfoCard.COLOR_SCHEMES[theme]) {
        return theme;
      }
    }
    
    return this.parseDarkLightTheme()[1]; // 默认返回亮色主题
  }

  // 根据实体状态确定主题名称（复用determineTheme逻辑）
  determineThemeFromEntityState(entityState, isSelectEntity) {
    // 下拉选择实体：检查是否是预定义的主题名称
    if (isSelectEntity && ElectricityInfoCard.COLOR_SCHEMES[entityState]) {
      return entityState;
    }
    
    // 复用determineTheme逻辑处理特殊值
    return this.determineTheme(entityState);
  }

  // 更新主题配置（优化后的主入口）
  updateTheme(config) {
    const theme = config.theme;
    
    // 没有配置且已有主题时保持当前主题（避免闪烁）
    if (theme === undefined && this.lastThemeName) return;
    
    // 停止所有监听器
    this.toggleThemeListener(false);
    
    let themeName = 'power'; // 默认主题
    let needsListener = false;
    
    if (theme !== undefined) {
      // 处理特殊模式
      const specialMode = this.handleSpecialThemeMode(theme);
      if (specialMode) {
        themeName = specialMode.themeName;
        needsListener = specialMode.needsListener;
      } else {
        themeName = this.determineTheme(theme);
      }
      
      this.lastThemeName = themeName;
    }
    
    // 启用监听器（如果需要）
    if (needsListener) {
      this.toggleThemeListener(true);
    }
    
    // 应用主题
    this.applyThemeInternal(themeName);
  }
  // ==================== 主题相关方法结束 ====================

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.shadowRoot.appendChild(template.content.cloneNode(true));
    
    // 初始化统一数据格式存储
    this.standardData = {
      dayUsage: [],
      monthUsage: [],
      yearUsage: [],
      payRecords: [],
      unit: '' // 单位将根据 utility_type 自动设置
    };
    
    // 默认 utility_type
    this.utilityType = 'ele'; // 默认为电力
    
    // 多用户相关初始化
    this.multiClassConfig = {}; // 多用户配置
    this.currentUserIndex = 0; // 当前用户索引
    this.userCount = 0; // 用户数量
    this.showMultiUserBar = false; // 是否显示多用户切换条
    this.currentUserKey = ''; // 当前用户键
    this.currentConfig = {}; // 当前用户配置
    this.entityId = ''; // 当前实体ID
    this.fieldMapping = {}; // 字段映射
    this.jiaofeiEntityId = null; // 缴费实体ID
    this.jiaofeiFieldMapping = {}; // 缴费实体字段映射
    
    // 数据缓存相关（5分钟缓存）
    this._dataCache = new Map(); // 数据缓存，键：{info}_{utility_type}
    this._cacheExpiry = new Map(); // 缓存过期时间
    this._isCardVisible = false; // 卡片可见性
    this._cacheDuration = 5 * 60 * 1000; // 缓存时长：5分钟
    
    // 余额刷新定时器（10秒）
    this._balanceUpdateInterval = null;
    
    // 调试信息开关（默认不显示调试信息）
    this.showDebug = false;
    
    // 只显示一次的调试信息（版本信息，不受showDebug控制）
    if (!window._electricityInfoCardDebugShown) {
      window._electricityInfoCardDebugShown = true;

      // 使用新的ECharts加载函数
      loadECharts().then(() => {
        // ECharts加载成功后检测来源
        const scripts = document.querySelectorAll('script[src]');
        let echartsSource = '未知';
        
        for (const script of scripts) {
          if (script.src.includes('echarts')) {
            if (script.src.includes('/local/')) {
              echartsSource = '本地';
            } else if (script.src.includes('cdn')) {
              echartsSource = 'CDN';
            }
            break;
          }
        }

        // 显示卡片信息（字体已调小）
        console.log(
          '%c⚡electricity-info-card\n%cVersion 3.3.2 ｜  ECharts: ' + echartsSource,
          `background: #ff5722; color: white; padding: 3px 8px; margin: 0; display: inline-block; text-align: center; font-weight: bold; font-size: 12px; font-family: monospace; line-height: 1.3; border-radius: 3px 3px 0 0;`,
          `background: white; color: #ff5722; padding: 3px 8px; margin: 0; display: inline-block; text-align: center; font-weight: bold; font-size: 11px; font-family: monospace; line-height: 1.3; border-radius: 0 0 3px 3px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);`
        );
      }).catch(err => {
        // 如果ECharts加载失败，仍然显示调试信息
        console.log(
          '%c⚡electricity-info-card\n%cVersion 3.3.2 ｜  ECharts: 加载失败',
          `background: #ff5722; color: white; padding: 3px 8px; margin: 0; display: inline-block; text-align: center; font-weight: bold; font-size: 12px; font-family: monospace; line-height: 1.3; border-radius: 3px 3px 0 0;`,
          `background: white; color: #ff5722; padding: 3px 8px; margin: 0; display: inline-block; text-align: center; font-weight: bold; font-size: 11px; font-family: monospace; line-height: 1.3; border-radius: 0 0 3px 3px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);`
        );
        console.error('ECharts加载失败:', err);
      });
    }
    
    // 存储元素引用
    this.userInfoEl = this.shadowRoot.getElementById('user-info');
    this.multiUserInfoEl = this.shadowRoot.getElementById('multi-user-info');
    this.sliderIndicatorEl = this.shadowRoot.getElementById('slider-indicator');
    this.userBlocks = this.shadowRoot.querySelectorAll('.user-block');
    this.balanceEl = this.shadowRoot.getElementById('balance');
    this.balanceLabelEl = this.shadowRoot.getElementById('balance-label');
    this.payCountBadgeEl = this.shadowRoot.getElementById('pay-count-badge');
    this.dateEl = this.shadowRoot.getElementById('date');
    this.dataDateEl = this.shadowRoot.getElementById('data-date');
    this.relativeDateEl = this.shadowRoot.getElementById('relative-date');
    this.electricityCardEl = this.shadowRoot.querySelector('.electricity-card');
    this.dataContainerEl = this.shadowRoot.getElementById('data-container');
    
    // 本月用电元素
    this.currentMonthElectricityEl = this.shadowRoot.getElementById('current-month-electricity');
    this.currentMonthCostEl = this.shadowRoot.getElementById('current-month-cost');
    this.currentMonthEleUnitEl = this.shadowRoot.getElementById('current-month-ele-unit');
    this.currentMonthCostUnitEl = this.shadowRoot.getElementById('current-month-cost-unit');
    this.currentMonthDistributionEl = this.shadowRoot.getElementById('current-month-distribution');
    this.currentMonthLabelsEl = this.shadowRoot.getElementById('current-month-labels');
    
    // 上月用电元素
    this.lastMonthElectricityEl = this.shadowRoot.getElementById('last-month-electricity');
    this.lastMonthCostEl = this.shadowRoot.getElementById('last-month-cost');
    this.lastMonthEleUnitEl = this.shadowRoot.getElementById('last-month-ele-unit');
    this.lastMonthCostUnitEl = this.shadowRoot.getElementById('last-month-cost-unit');
    this.lastMonthDistributionEl = this.shadowRoot.getElementById('last-month-distribution');
    this.lastMonthLabelsEl = this.shadowRoot.getElementById('last-month-labels');
    
    // 年度用电元素
    this.currentYearEl = this.shadowRoot.getElementById('current-year');
    this.yearElectricityEl = this.shadowRoot.getElementById('year-electricity');
    this.yearCostEl = this.shadowRoot.getElementById('year-cost');
    this.yearEleUnitEl = this.shadowRoot.getElementById('year-ele-unit');
    this.yearCostUnitEl = this.shadowRoot.getElementById('year-cost-unit');
    this.yearDistributionEl = this.shadowRoot.getElementById('year-distribution');
    
    // 趋势箭头元素
    this.monthTrendArrowEl = this.shadowRoot.getElementById('month-trend-arrow');
    this.lastMonthTrendArrowEl = this.shadowRoot.getElementById('last-month-trend-arrow');
    this.yearTrendArrowEl = this.shadowRoot.getElementById('year-trend-arrow');
    this.yearLabelsEl = this.shadowRoot.getElementById('year-labels');
    
    this.electricityPriceEl = this.shadowRoot.getElementById('electricity-price');
    this.priceUnitEl = this.shadowRoot.querySelector('.price-unit');
    this.priceLabelEl = this.shadowRoot.querySelector('.price-label');
    // 新增剩余天数元素引用
    this.remainingDaysEl = this.shadowRoot.getElementById('remaining-days');
    this.remainingDaysDateEl = this.shadowRoot.getElementById('remaining-days-date');
    
    // 阶梯电价相关元素
    this.tierPeriodEl = this.shadowRoot.getElementById('tier-period');
    this.tier1El = this.shadowRoot.getElementById('tier-1');
    this.tier2El = this.shadowRoot.getElementById('tier-2');
    this.tier3El = this.shadowRoot.getElementById('tier-3');
    this.currentIndicatorEl = this.shadowRoot.getElementById('current-indicator');
    this.indicatorArrowEl = this.shadowRoot.getElementById('indicator-arrow');
    this.currentTierEl = this.shadowRoot.getElementById('current-tier');
    this.currentUsageEl = this.shadowRoot.getElementById('current-usage');
    this.tiersContainerEl = this.shadowRoot.querySelector('.tiers-container');
    
    // 阶梯块中的文字元素
    this.tier1BlockEl = this.shadowRoot.getElementById('tier-1-block');
    this.tier2BlockEl = this.shadowRoot.getElementById('tier-2-block');
    this.tier3BlockEl = this.shadowRoot.getElementById('tier-3-block');
    
    // 阶梯范围DOM元素
    this.tier1RangeEl = this.shadowRoot.getElementById('tier-1-range');
    this.tier2RangeEl = this.shadowRoot.getElementById('tier-2-range');
    this.tier3RangeEl = this.shadowRoot.getElementById('tier-3-range');
    this.tier1PriceEl = this.shadowRoot.getElementById('tier-1-price');
    this.tier2PriceEl = this.shadowRoot.getElementById('tier-2-price');
    this.tier3PriceEl = this.shadowRoot.getElementById('tier-3-price');
    
    // 所有tier-content元素
    this.tierContentElements = this.shadowRoot.querySelectorAll('.tier-content');
    
    // 动态文本元素
    this.tierLabelLeftEl = this.shadowRoot.querySelector('.tier-label-left');
    this.monthLabels = this.shadowRoot.querySelectorAll('.month-label');
    this.yearLabels = this.shadowRoot.querySelectorAll('.year-label');
    
    // 日历视图相关元素
    this.dataContainerEl = this.shadowRoot.getElementById('data-container');
    this.calendarViewEl = this.shadowRoot.getElementById('calendar-view');
    this.calendarHeaderEl = this.shadowRoot.querySelector('.calendar-header');
    this.calendarTabsEl = this.shadowRoot.querySelector('.calendar-tabs');
    this.calendarControlsEl = this.shadowRoot.querySelector('.calendar-controls');
    this.calendarGridEl = this.shadowRoot.getElementById('calendar-grid');
    this.calYearSelectEl = this.shadowRoot.getElementById('cal-year-select');
    this.calMonthSelectEl = this.shadowRoot.getElementById('cal-month-select');
    this.currentMonthBtnEl = this.shadowRoot.getElementById('current-month-btn');
    this.backToMainBtnEl = this.shadowRoot.getElementById('back-to-main');
    
    // 日历统计元素
    this.calMonthUsageEl = this.shadowRoot.getElementById('cal-month-usage');
    this.calMonthCostEl = this.shadowRoot.getElementById('cal-month-cost');
    this.calYearUsageEl = this.shadowRoot.getElementById('cal-year-usage');
    this.calYearCostEl = this.shadowRoot.getElementById('cal-year-cost');
    
    // 年视图元素
    this.calendarContentEl = this.shadowRoot.getElementById('calendar-content');
    this.yearContentEl = this.shadowRoot.getElementById('year-content');
    this.yearComboChartEl = this.shadowRoot.getElementById('year-combo-chart');
    this.yearHeatmapContainerEl = this.shadowRoot.getElementById('year-heatmap-container');
    this.yearHeatmapChartEl = this.shadowRoot.getElementById('year-heatmap-chart');
    this.yearFilterMainEl = this.shadowRoot.getElementById('year-filter-main');
    this.yearFilterYearsEl = this.shadowRoot.getElementById('year-filter-years');
    // 动态排名柱状图元素
    this.barRacingContainerEl = this.shadowRoot.getElementById('bar-racing-container');
    this.barRacingChartEl = this.shadowRoot.getElementById('bar-racing-chart');
    this.barRacingDateEl = this.shadowRoot.getElementById('bar-racing-date');
    this.barRacingPlayBtnEl = this.shadowRoot.getElementById('bar-racing-play-btn');
    this.barRacingSpeedBtnEl = this.shadowRoot.getElementById('bar-racing-speed-btn');
    this.barRacingModeDayBtnEl = this.shadowRoot.getElementById('bar-racing-mode-day-btn');
    this.barRacingModeMonthBtnEl = this.shadowRoot.getElementById('bar-racing-mode-month-btn');
    this.barRacingProgressEl = this.shadowRoot.getElementById('bar-racing-progress');
    this.barRacingMarkerEl = this.shadowRoot.getElementById('bar-racing-marker');
    this.barRacingChart = null;
    this.barRacingTimer = null;
    this.barRacingPaused = false;
    this.barRacingSpeed = 1; // 播放速度倍率
    this.barRacingFrameIndex = 0;
    this.barRacingFrames = [];
    this.barRacingMode = '日'; // '日' 或 '月'
    this.yearChart = null;
    this.yearHeatmapChart = null;
    // 年视图数据缓存
    this._yearChartData = null;
    this._daylistData = null;
    this.selectedYearView = '年度'; // 年视图当前选中的按钮：总计、年度、热力图、xx年

    // 月视图元素
    this.monthContentEl = this.shadowRoot.getElementById('month-content');
    this.monthComboChartEl = this.shadowRoot.getElementById('month-combo-chart');
    this.monthYearFilterEl = this.shadowRoot.getElementById('month-year-filter');
    this.monthChart = null;
    this.selectedYear = null; // 当前选中的年份
    // 月视图数据缓存
    this._monthChartData = null;

    // 日视图元素
    this.dayContentEl = this.shadowRoot.getElementById('day-content');
    this.dayComboChartEl = this.shadowRoot.getElementById('day-combo-chart');
    this.dayFilterMainEl = this.shadowRoot.getElementById('day-filter-main');
    this.dayFilterYearsEl = this.shadowRoot.getElementById('day-filter-years');
    this.futureMonthMessageEl = this.shadowRoot.getElementById('future-month-message');
    this.dayViewChart = null;
    this.selectedDayYear = null; // 日视图中当前选中的年份
    this.selectedDayMonth = null; // 日视图中当前选中的月份
    // 日视图数据缓存
    this._dayChartData = null;

    // 日历状态
    this.isCalendarView = false;
    this.currentView = 'calendar';
    this.calCurrentYear = new Date().getFullYear();
    this.calCurrentMonth = new Date().getMonth() + 1;
    this.availableYears = [];
    this.daylistData = [];
    this.yearlistData = [];
    this.monthlistData = [];
    
    // 日详情模态框元素
    this.dayModalEl = this.shadowRoot.getElementById('day-modal');
    this.dayModalTitleEl = this.shadowRoot.getElementById('day-modal-title');
    this.dayModalBodyEl = this.shadowRoot.getElementById('day-modal-body');
    this.dayModalCloseEl = this.shadowRoot.getElementById('day-modal-close');
    this.dayModalContentEl = this.shadowRoot.querySelector('.day-modal-content');

    // 缴费历史模态框元素
    this.payHistoryModalEl = this.shadowRoot.getElementById('pay-history-modal');
    this.payHistoryTitleEl = this.shadowRoot.getElementById('pay-history-title');
    this.payHistoryBodyEl = this.shadowRoot.getElementById('pay-history-body');
    this.payHistoryCloseEl = this.shadowRoot.getElementById('pay-history-close');
    this.payHistoryContentEl = this.shadowRoot.querySelector('#pay-history-modal .day-modal-content');

    // 将模态框从shadow DOM移到document.body，避免弹出卡片时窗口限制问题
    if (this.dayModalEl) {
      // 添加模态框全局样式到document.head（只添加一次）
      if (!document.getElementById('electricity-card-modal-styles')) {
        const modalStyle = document.createElement('style');
        modalStyle.id = 'electricity-card-modal-styles';
        modalStyle.textContent = `
          /* ==================== 模态框样式 ==================== */
          .day-modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            animation: fadeIn 0.2s ease;
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
          }

          .day-modal-content {
            position: relative;
            background: var(--card-bg);
            border-radius: 12px;
            padding: 5px 10px 10px 10px;
            max-width: 450px;
            width: 90%;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8);
            animation: scaleIn 0.3s ease;
            color: var(--text-color);
            transform: scale(0.9);
            opacity: 0;
            transition: transform 0.3s ease, opacity 0.3s ease;
          }
          
          .day-modal-overlay[style*="display: flex"] .day-modal-content {
            transform: scale(1);
            opacity: 1;
          }

          @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
          }

          .day-modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
            padding-bottom: 0px;
            border-bottom: 2px solid rgba(0, 0, 0, 0.1);
          }

          .day-modal-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-color);
          }

          .day-modal-close {
            background: none;
            border: none;
            font-size: 28px;
            color: var(--text-color);
            cursor: pointer;
            line-height: 1;
            padding: 0;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            transition: background 0.2s;
          }

          .day-modal-close:hover {
            background: rgba(0, 0, 0, 0.1);
          }

          /* 饼图区域样式 */
          .pie-chart-section {
            display: flex;
            flex-direction: column;
            background: var(--card-button-bg);
            border-radius: 8px;
            flex: 1;
            min-width: 0;
            height: 235px;
          }

          .pie-chart-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-color);
            margin-left: 15px;
          }

          .pie-chart-content {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            flex: 1;
            min-height: 0;
          }

          .pie-chart-container {
            width: 100%;
            height: 205px;
            position: relative;
            top: -7px;
          }

          .usage-stats {
            flex: 0 0 35%;
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-top: -20px;
          }

          .usage-stat-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 3px 3px;
            background: var(--button-primary-transparent);
            border-radius: 6px;
            border-left: 4px solid;
          }

          .usage-stat-label {
            font-weight: 600;
            font-size: 11px;
            color: var(--text-color);
          }

          .usage-stat-value {
            font-weight: bold;
            font-size: 11px;
            color: var(--text-color);
          }

          .valley-stat {
            border-left-color: #4CAF50;
          }

          .peak-stat {
            border-left-color: #FF9800;
          }

          .normal-stat {
            border-left-color: #2196F3;
          }

          .sharp-stat {
            border-left-color: #F44336;
          }

          .total-stat {
            border-left-color: #804AFF;
            background: rgba(128, 74, 255, 0.1) !important;
          }

          /* 设备轨道样式 */
          .timeline-aligner {
            display: grid;
            grid-template-columns: 67px 80px 1fr;
            align-items: center;
            margin-top: 10px;
            gap: 2px;
          }

          .timeline-aligner-spacer {
            width: 100px;
            flex-shrink: 0;
          }

          .timeline-aligner-spacer-2 {
            width: 60px;
            flex-shrink: 0;
          }

          .timeline-aligner-content {
            flex-grow: 1;
            margin-left: 0;
            width: 299px;
          }

          #timeline-container {
            margin-top: 10px;
            background: var(--card-button-bg);
            border-radius: 8px;
            padding: 10px;
          }

          .device-track {
            display: grid;
            grid-template-columns: 60px 85px 1fr;
            align-items: center;
            margin-bottom: 8px;
            height: 12px;
            width: 100%;
            gap: 2px;
            align-content: center;
          }

          .device-label {
            width: 100px;
            font-size: 12px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-right: 10px;
            padding: 0px 0px;
            border-radius: 4px;
            color: var(--button-color-active);
            flex-shrink: 0;
            text-align: left;
            box-sizing: border-box;
          }

          .power-usage-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 4px;
            font-size: 10px;
            font-weight: 600;
            white-space: nowrap;
            font-family: 'Courier New', monospace;
            transform-origin: center;
          }

          .power-usage,
          .usage-duration,
          .power-usage-estimate {
            text-align: center;
            font-size: 10px;
            min-width: 40px;
            padding: 0px 0px;
            border-radius: 3px;
            font-weight: 600;
          }

          .power-usage {
            background: var(--usage-color);
            color: #000000;
          }

          .power-usage-estimate {
            background: #38b48b;
            color: #000000;
          }

          .usage-duration {
            background: var(--money-color);
            color: white;
          }

          .total-row {
            display: grid;
            grid-template-columns: 60px 85px 1fr;
            align-items: center;
            margin-top: 10px;
            padding-top: 8px;
            border-top: 1px solid var(--button-primary-transparent);
            font-weight: 600;
            font-size: 11px;
            color: var(--text-color);
            height: 12px;
            width: 100%;
            gap: 2px;
            align-content: center;
          }

          .total-label {
            width: 100px;
            font-size: 11px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-right: 10px;
            padding: 0px 0px;
            border-radius: 4px;
            color: var(--button-color-active);
            flex-shrink: 0;
            text-align: left;
            box-sizing: border-box;
          }

          .total-value {
            text-align: center;
            font-size: 10px;
            min-width: 40px;
            padding: 2px 4px;
            border-radius: 3px;
            font-weight: 600;
            background: var(--button-primary-transparent);
            color: var(--text-color);
          }

          .timeline-aligner .time-labels {
            position: relative;
            width: 106%;
            height: 10px;
            margin-top: -5px;
            margin-left: -10px;
            font-size: 9px;
            color: var(--text-color);
            font-weight: 400;
          }

          .timeline-aligner .time-labels span {
            position: absolute;
            top: 0;
            white-space: nowrap;
            box-sizing: border-box;
            transform: translateX(-50%);
            font-weight: 400;
          }

          .timeline-aligner .time-labels span:nth-child(1) {
            left: 0%;
            transform: translateX(0%);
          }
          .timeline-aligner .time-labels span:nth-child(2) { left: 33.333%; }
          .timeline-aligner .time-labels span:nth-child(3) { left: 66.666%; }
          .timeline-aligner .time-labels span:nth-child(4) {
            left: 100%;
            transform: translateX(-100%);
          }

          .track-bar-wrapper {
            flex-grow: 1;
            position: relative;
            height: 15px;
            background: rgba(0,0,0,0.05);
            border-radius: 4px;
            cursor: pointer;
            margin-right: 0;
          }

          .track-bar {
            width: 100%;
            height: 15px;
            position: relative;
          }

          .track-fill {
            position: absolute;
            height: 15px;
            top: 0;
            opacity: 0.7;
            border-radius: 2px;
            transition: opacity 0.2s;
          }

          .track-fill.active {
            opacity: 1;
            box-shadow: 0 0 4px rgba(0,0,0,0.3);
            z-index: 2;
          }

          @keyframes stripe-move {
            from { background-position: 0 0; }
            to { background-position: 1rem 0; }
          }

          @keyframes rainbow-glow {
            0% { box-shadow: 0 0 6px 2px rgba(255, 0, 0, 0.8), 0 0 12px 4px rgba(255, 165, 0, 0.6); }
            14% { box-shadow: 0 0 6px 2px rgba(255, 165, 0, 0.8), 0 0 12px 4px rgba(255, 255, 0, 0.6); }
            28% { box-shadow: 0 0 6px 2px rgba(255, 255, 0, 0.8), 0 0 12px 4px rgba(0, 128, 0, 0.6); }
            42% { box-shadow: 0 0 6px 2px rgba(0, 128, 0, 0.8), 0 0 12px 4px rgba(0, 255, 255, 0.6); }
            57% { box-shadow: 0 0 6px 2px rgba(0, 255, 255, 0.8), 0 0 12px 4px rgba(0, 0, 255, 0.6); }
            71% { box-shadow: 0 0 6px 2px rgba(0, 0, 255, 0.8), 0 0 12px 4px rgba(128, 0, 128, 0.6); }
            85% { box-shadow: 0 0 6px 2px rgba(128, 0, 128, 0.8), 0 0 12px 4px rgba(255, 0, 0, 0.6); }
            100% { box-shadow: 0 0 6px 2px rgba(255, 0, 0, 0.8), 0 0 12px 4px rgba(255, 165, 0, 0.6); }
          }

          .track-fill.on-going {
            background-image: linear-gradient(45deg,rgba(255,255,255,.15) 25%,transparent 25%,transparent 50%,rgba(255,255,255,.15) 50%,rgba(255,255,255,.15) 75%,transparent 75%,transparent);
            background-size: 1rem 1rem;
            animation: stripe-move 1s linear infinite, rainbow-glow 8s linear infinite;
          }

          /* 正在运行事件列表项的动画样式 */
          #tooltip-events-list .on-going-event {
            position: relative;
            background-image: linear-gradient(45deg, rgba(255,255,255,0.1) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.1) 75%, transparent 75%, transparent);
            background-size: 0.8rem 0.8rem;
            animation: stripe-move 1.5s linear infinite;
            border-left: 3px solid var(--button-color-active);
            padding-left: 8px;
          }

          #tooltip-events-list .on-going-event::before {
            content: "●";
            position: absolute;
            left: -12px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--button-color-active);
            font-size: 8px;
            animation: pulse 1.5s infinite;
          }

          @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.3; }
            100% { opacity: 1; }
          }

          /* 缴费历史模态框样式 */
          .pay-history-top-section {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
            align-items: stretch;
            height: 140px;
          }

          .pay-history-summary {
            display: flex;
            justify-content: space-evenly;
            background: var(--card-button-bg);
            border-radius: 8px;
            width: 25%;
            flex-shrink: 0;
            flex-direction: column;
            height: 130px;
          }

          .pay-history-item {
            text-align: center;
          }

          .pay-history-label {
            font-size: 12px;
            color: var(--text-color);
            opacity: 0.8;
          }

          .pay-history-value {
            font-size: 18px;
            font-weight: 700;
            color: var(--card-value-color);
          }

          .pay-history-list {
            max-height: 350px;
            overflow-y: auto;
            padding-right: 5px;
          }

          .pay-history-list::-webkit-scrollbar {
            width: 6px;
          }

          .pay-history-list::-webkit-scrollbar-track {
            background: var(--button-primary-transparent);
            border-radius: 3px;
          }

          .pay-history-list::-webkit-scrollbar-thumb {
            background: var(--button-color);
            border-radius: 3px;
          }

          .pay-record {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 5px 15px;
            background: var(--card-button-bg);
            border-radius: 6px;
            margin-bottom: 8px;
            border-left: 3px solid var(--money-color);
            transition: all 0.2s ease;
          }

          .pay-record:hover {
            background: var(--button-primary-transparent);
            transform: translateX(3px);
          }

          .pay-record-left {
            flex: 1;
          }

          .pay-record-time {
            font-size: 12px;
            color: var(--text-color);
            opacity: 0.7;
            margin-bottom: 1px;
          }

          .pay-record-source {
            font-size: 11px;
            color: white;
            opacity: 1;
            padding: 2px 6px;
            border-radius: 4px;
            display: inline-block;
          }

          .pay-record-source.alipay {
            background: #1677FF;
          }

          .pay-record-source.wechat {
            background: #52C41A;
          }

          .pay-record-source.sgcc-online {
            background: #14806E;
          }

          .pay-record-source.eebao {
            background: #FAAD14;
          }

          .pay-record-source.outlet {
            background: #FA8C16;
          }

          .pay-record-source.bank {
            background: #9C27B0;
          }

          .pay-record-source.other {
            background: #8C8C8C;
          }

          .pay-record-source.default {
            background: #13C2C2;
          }

          .pay-record-cost {
            font-size: 16px;
            font-weight: 700;
            color: var(--money-color);
          }

          .pay-record-cost::before {
            content: '¥';
            font-size: 12px;
            margin-right: 2px;
          }

          .no-pay-history {
            text-align: center;
            padding: 40px 20px;
            color: var(--text-color);
            opacity: 0.7;
          }

          .no-pay-history-icon {
            font-size: 48px;
            margin-bottom: 10px;
          }

          .no-pay-history-text {
            font-size: 14px;
          }

          .no-pay-history-subtext {
            font-size: 12px;
            margin-top: 5px;
            opacity: 0.7;
          }
        `;
        document.head.appendChild(modalStyle);
      }
      
      // 将日详情模态框移到document.body
      document.body.appendChild(this.dayModalEl);
    }
    
    // 将缴费历史模态框移到document.body
    if (this.payHistoryModalEl) {
      document.body.appendChild(this.payHistoryModalEl);
    }

    // 设备事件提示框元素 - 将其移到document.body以避免shadow DOM定位问题
    this.eventTooltip = this.shadowRoot.getElementById('event-tooltip');
    this.tooltipDeviceName = this.shadowRoot.getElementById('tooltip-device-name');
    this.tooltipEventsList = this.shadowRoot.getElementById('tooltip-events-list');
    
    // 将tooltip从shadow DOM移到document.body，使其成为真正的固定定位弹出窗口
    if (this.eventTooltip) {
      // 添加主题化的tooltip样式到document.head
      const tooltipStyle = document.createElement('style');
      tooltipStyle.textContent = `
        #event-tooltip {
          position: absolute !important;
          background-color: var(--tooltip-bg, var(--card-button-bg));
          color: var(--tooltip-text-color, var(--text-color));
          border: 1px solid var(--tooltip-border-color, var(--button-primary-transparent));
          border-radius: 6px;
          padding: 10px;
          box-shadow: 0 4px 10px rgba(0,0,0,0.3);
          z-index: 99999;
          display: none;
          width: auto;
          min-width: 100px;
          max-width: 300px;
          font-size: 11px;
          line-height: 1.4;
          --arrow-y: 50%;
          max-height: 150px;
          pointer-events: auto !important;
        }
        #event-tooltip strong {
          display: block;
          margin-bottom: 5px;
          color: var(--tooltip-text-color, var(--text-color));
        }
        #event-tooltip ul {
          list-style: none;
          padding: 0;
          margin: 0;
          max-height: 120px;
          overflow-y: auto;
        }
        #event-tooltip ul li {
          margin-bottom: 3px;
          border-bottom: 1px dashed var(--tooltip-border-color, var(--button-primary-transparent));
          padding: 3px 0;
          font-size: 11px;
          transition: background-color 0.2s;
        }
        #event-tooltip ul li.highlighted-event {
          background-color: var(--tooltip-highlight-bg, var(--button-color-active));
          padding: 3px 5px;
          border-radius: 4px;
          border-bottom: none;
        }
        #event-tooltip ul li.highlighted-event span,
        #event-tooltip ul li.highlighted-event {
          color: var(--button-active-text-color);
        }
        #event-tooltip ul li span {
          color: var(--tooltip-text-color, var(--text-color));
          opacity: 0.8;
        }
        #event-tooltip[data-arrow]::after {
          content: '';
          position: absolute;
          top: var(--arrow-y);
          transform: translateY(-50%);
          width: 0;
          height: 0;
          bottom: auto;
          border-color: transparent;
        }
        #event-tooltip[data-arrow="left"]::after {
          left: -7px;
          border-top: 7px solid transparent;
          border-bottom: 7px solid transparent;
          border-right: 7px solid var(--tooltip-bg);
        }
        #event-tooltip[data-arrow="right"]::after {
          right: -7px;
          border-top: 7px solid transparent;
          border-bottom: 7px solid transparent;
          border-left: 7px solid var(--tooltip-bg);
        }
      `;
      document.head.appendChild(tooltipStyle);
      
      // 将tooltip移到document.body（固定定位，浮动在所有内容之上）
      document.body.appendChild(this.eventTooltip);
      this.eventTooltip.style.display = 'none';
    }
    
    // ECharts相关
    this.echartsLoaded = false;
    this.echartsPath = '/local/echarts.min.js';
    this.echartsFallbackPath = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js';
    this.dayChart = null;
    this.echartsScriptElement = null;
    
    // 设备事件数据
    this.deviceEvents = [];
    
    // 默认配置
    this.defaultConfig = {
      // 背景色配置（由主题系统控制）
      // background: null,
      // 主题配置:
      // - 不配置时: 使用power主题
      // - 配置为"time": 根据时间自动切换主题 (白天使用dark_light_theme配置的亮色主题(默认light)，晚上使用dark_light_theme配置的暗色主题(默认black))
      // - 配置为"phone": 跟随手机系统主题自动切换 (亮色使用dark_light_theme配置的亮色主题(默认light)，暗色使用dark_light_theme配置的暗色主题(默认black))
      // - 开关实体配置: 仅在dark_light_theme配置的亮色主题和暗色主题之间切换 (默认light和black)
      // - 下拉选择实体配置: 根据实体值切换对应主题 (light、dark、transparent、blue、green、red、purple、yellow、cyan、pink、orange)
      // - 特殊值 "time": 根据时间自动切换主题
      // - 特殊值 "phone": 跟随手机系统主题
      theme: undefined,
      // 暗色和亮色主题配置:
      // - 当theme配置为time或phone，或者使用开关实体时，使用该配置的主题进行切换
      // - 配置格式: "暗色主题,亮色主题"，使用逗号分隔，例如: "black,red"
      // - 不配置时默认使用"black,light" (暗色black，亮色light)
      // - 可选值: dark、black、transparent、blue、green、red、purple、yellow、cyan、pink、orange、light
      dark_light_theme: undefined,
      // 设备实体配置（用于显示设备使用情况）
      device_entity: null,
      // 隐藏配置：可以隐藏指定的UI组件，支持多个值，用逗号分隔
      // 可选值：
      // - price-display: 隐藏所有价格显示区域
      // - electricity-price-display: 隐藏电价显示区域
      // - remaining-days-display: 隐藏剩余天数显示区域
      // - tier-indicator: 隐藏用电阶梯指示器
      // - time-distribution-bar: 隐藏分时用电条
      // - data-container: 隐藏统计数据容器（本月/上月/年度统计）
      // - user-info: 隐藏用户信息标题
      // 可以同时填写多个，用逗号分隔，例如：'tier-indicator,time-distribution-bar'
      hide: ''
    };
    
    // 阶梯电价配置（初始化为空，将由配置文件或实体数据填充）
    this.tierConfig = {
      tiers: [
        { id: 1, max: null, price: null, color: '#55c593', title: '第一阶梯' },
        { id: 2, max: null, price: null, color: '#f8c337', title: '第二阶梯' },
        { id: 3, max: Infinity, price: null, color: '#f79335', title: '第三阶梯' }
      ],
      // 阶梯电价计算周期 (默认: 7月1日到6月30日，但仅用于非电力类型)
      periodStartMonth: null, // 开始月份
      periodStartDay: null,   // 开始日
      periodEndMonth: null,   // 结束月份
      periodEndDay: null      // 结束日
    };
    
    // 分时用电配置
    this.timeConfig = {
      // 分时用电类型配置
      types: [
        { key: 'TPq', name: '尖', colorClass: 'time-segment-tip', dotClass: 'time-dot-tip' },
        { key: 'PPq', name: '峰', colorClass: 'time-segment-peak', dotClass: 'time-dot-peak' },
        { key: 'NPq', name: '平', colorClass: 'time-segment-normal', dotClass: 'time-dot-normal' },
        { key: 'VPq', name: '谷', colorClass: 'time-segment-valley', dotClass: 'time-dot-valley' }
      ]
    };
    
    // 初始化变量
    this._hass = null;
    this._config = null;
    this.currentPeriodUsage = 0; // 当前周期用电量
    this.currentTier = 1; // 当前阶梯
    this.lastUpdateTime = 0; // 上次更新时间戳
    this.updateInterval = 10 * 60 * 1000; // 10分钟更新间隔（毫秒）
    this.deviceEntityConfig = null; // 设备实体配置
    this.themeTimer = null; // 主题定时器
    this.lastThemeUpdate = 0; // 上次主题更新时间
    this.historicalData = null; // 历史数据缓存
    this.historicalDataLoaded = false; // 历史数据是否已加载完成
    this.paySourceChart = null; // 缴费方式饼图实例
    this.dayDeviceData = null; // 日设备数据（包含设备详细数据、房间聚合数据、分时用电数据）
    this.sankeyChart = null; // 桑基图实例
    this.showSankeyChart = false; // 是否显示桑基图（false为显示设备轨道，true为显示桑基图）
  }

  setConfig(config) {
    // 必须配置multiclass
    if (!config.multiclass) {
      throw new Error('必须配置multiclass参数');
    }

    this._config = config;
    
    // 保存顶层配置
    this.topName = config.name || ''; // 顶层的名称
    this.showName = config.show_name !== false; // 是否显示名称，默认为true
    
    // 读取调试开关配置（默认为false，不显示调试信息）
    this.showDebug = config.show_debug === true;
    
    // 初始化多用户配置
    this.multiClassConfig = config.multiclass;
    this.currentUserIndex = 0; // 默认选中第一个用户
    this.userCount = Object.keys(this.multiClassConfig).length;

    // 根据用户数量设置单类样式（调整背景图标位置）
    this.updateSingleClassStyle();

    // 根据用户数量决定是否显示切换条
    this.showMultiUserBar = this.userCount >= 2;
    
    // 初始化当前用户配置
    this.initializeCurrentUserConfig();
    
    // 初始化ECharts（仅在首次加载时）
    if (!this.echartsInitialized) {
      this.initializeECharts();
      this.echartsInitialized = true;
    }
    
    // 应用隐藏配置
    this.applyHiddenConfig();
    
    // 初始化日历事件监听
    this.initCalendarEvents();
    
    // 设置主题相关的监听器
    this.setupThemeListeners();
  }
  
  // 调试日志方法（根据showDebug配置决定是否输出）
  debugLog(...args) {
    if (this.showDebug) {
      console.log(...args);
    }
  }
  
  debugWarn(...args) {
    if (this.showDebug) {
      console.warn(...args);
    }
  }
  
  debugError(...args) {
    if (this.showDebug) {
      console.error(...args);
    }
  }

  // 根据用户数量更新单类样式（调整背景图标位置）
  updateSingleClassStyle() {
    if (!this.electricityCardEl) return;

    if (this.userCount === 1) {
      this.electricityCardEl.classList.add('single-class');
    } else {
      this.electricityCardEl.classList.remove('single-class');
    }
  }

  // 初始化当前用户配置
  initializeCurrentUserConfig() {
    const userKeys = Object.keys(this.multiClassConfig);
    const currentKey = userKeys[this.currentUserIndex];
    const currentConfig = this.multiClassConfig[currentKey];
    
    if (!currentConfig) {
      throw new Error('无法获取当前用户配置');
    }
    
    // 设置当前用户信息
    this.currentUserKey = currentKey;
    this.currentConfig = currentConfig;
    
    // 更新 user-info 显示（使用顶层配置的 name）
    if (this.userInfoEl && this.topName) {
      this.userInfoEl.textContent = this.topName;
    }
    
    // 根据 show_name 控制 user-info 和 multi-user-info 的显示
    if (this.userInfoEl && this.multiUserInfoEl) {
      if (this.showName) {
        // 显示名称
        this.userInfoEl.classList.remove('hidden');
        this.multiUserInfoEl.classList.remove('hidden');
      } else {
        // 隐藏名称
        this.userInfoEl.classList.add('hidden');
        this.multiUserInfoEl.classList.add('hidden');
      }
    }
    
    // 读取 utility_type 配置（默认为 'ele'）
    this.utilityType = currentConfig.utility_type || 'ele';
    
    // 根据 utility_type 设置单位
    this.standardData.unit = this.getUnitByUtilityType(this.utilityType);
    
    // 根据 utility_type 更新动态文本
    this.updateDynamicTexts(this.utilityType);
    
    // 根据 utility_type 更新背景图标
    this.updateCardBackgroundIcon(this.utilityType);
    
    // 解析实体配置（支持字段映射）
    this.parseEntityConfig(currentConfig);
    
    // 解析缴费实体配置
    this.parseJiaofeiConfig(currentConfig);
    
    // 当 utility_type 不是 'ele' 时，才使用手动配置的阶梯电价和计费周期
    // 'ele' 类型完全从实体获取数据，不使用任何手动配置
    if (this.utilityType !== 'ele') {
      // 更新阶梯电价配置和计费周期配置（仅非电力类型使用）
      this.updateTierConfig(currentConfig);
      this.updatePeriodConfig(currentConfig);
    }
    
    // 更新背景色配置
    this.updateBackgroundConfig(currentConfig);
    
    // 更新卡片宽度配置（从顶层配置读取）
    this.updateCardWidth();
    
    // 保存设备实体配置
    this.deviceEntityConfig = currentConfig.device_entity || null;
    
    // 控制分时用电显示
    this.updateTimeDistributionVisibility(currentConfig);
    
    // 初始化多用户切换条
    this.setupMultiUserBar();
    
    // 初始化所有用户的余额显示
    this.updateAllUsersBalance();
    
    // 应用当前用户的隐藏配置
    this.applyHiddenConfig();
    
    // 确保当前用户块的 active 状态正确设置（首次进入卡片时）
    this.ensureCurrentUserActive();
    
    // 如果卡片可见，加载数据
    if (this._isCardVisible) {
      this.loadDataForCurrentUser();
    }
  }
  
  // 解析实体配置（支持字段映射语法）
  parseEntityConfig(config) {
    const entityStr = config.entity || '';
    
    // 解析实体ID和字段映射（支持逗号前后有空格）
    const entityMatch = entityStr.match(/^([^,\s[]+)(?:\s*,\s*\[(.+)\])?$/);
    if (entityMatch) {
      this.entityId = entityMatch[1].trim();
      this.fieldMapping = {};
      
      // 解析字段映射
      if (entityMatch[2]) {
        const mappingStr = entityMatch[2];
        const mappings = mappingStr.split(',');
        
        mappings.forEach(mapping => {
          const kv = mapping.trim().split(':');
          if (kv.length === 2) {
            const key = kv[0].trim();
            const value = kv[1].trim();
            this.fieldMapping[key] = value;
          }
        });
      }
    } else {
      this.entityId = entityStr.trim();
      this.fieldMapping = {};
    }
    
    // 根据 utility_type 设置默认字段映射（如果没有自定义映射）
    if (this.utilityType === 'gas' && Object.keys(this.fieldMapping).length === 0) {
      // 燃气默认映射
      this.fieldMapping = {
        node: 'daylist',
        daylist: 'daylist',
        date: 'day',
        usage: 'f_gas',
        amount: 'e_gas'
      };
    } else if (this.utilityType === 'water' && Object.keys(this.fieldMapping).length === 0) {
      // 水默认映射
      this.fieldMapping = {
        node: 'daylist',
        daylist: 'daylist',
        date: 'day',
        usage: 'usge',
        amount: 'money'
      };
    }
  }
  
  // 解析缴费实体配置
  parseJiaofeiConfig(config) {
    const jiaofeiStr = config.jiaofei_entity || '';
    this.jiaofeiEntityId = null;
    this.jiaofeiFieldMapping = {};
    
    if (jiaofeiStr) {
      // 解析缴费实体ID和字段映射（支持逗号前后有空格）
      const match = jiaofeiStr.match(/^([^,\s[]+)(?:\s*,\s*\[(.+)\])?$/);
      if (match) {
        this.jiaofeiEntityId = match[1].trim();
        
        // 解析字段映射
        if (match[2]) {
          const mappingStr = match[2];
          const mappings = mappingStr.split(',');
          
          mappings.forEach(mapping => {
            const kv = mapping.trim().split(':');
            if (kv.length === 2) {
              const key = kv[0].trim();
              const value = kv[1].trim();
              this.jiaofeiFieldMapping[key] = value;
            }
          });
        }
      } else {
        this.jiaofeiEntityId = jiaofeiStr.trim();
        this.jiaofeiFieldMapping = {};
      }
    }
  }
  
  // 加载当前用户的数据
  loadDataForCurrentUser() {
    if (!this._hass || !this.entityId) {
      return Promise.resolve();
    }
    
    const cacheKey = this.getCurrentCacheKey();
    
    // 检查缓存是否有效
    if (this.isCacheValid(cacheKey)) {
      // 使用缓存数据
      const cachedData = this._dataCache.get(cacheKey);
      this.processEntityData(cachedData);
      return Promise.resolve();
    }
    
    // 从实体获取数据
    const entity = this._hass.states[this.entityId];
    if (!entity || entity.state === 'unknown' || entity.state === 'unavailable') {
      // 实体不存在或状态为unknown/unavailable时，设置默认数据并更新卡片显示
      this.setDefaultData();
      // 更新所有用户的余额显示为"--"
      this.updateAllUsersBalance();
      return Promise.resolve();
    }
    
    // 根据字段映射获取数据
    const entityData = this.extractDataFromEntity(entity);
    
    // 加载并合并历史数据，返回 Promise
    return this.loadAndMergeData(entityData).then(() => {
      // 缓存数据
      this._dataCache.set(cacheKey, entityData);
      this._cacheExpiry.set(cacheKey, Date.now() + this._cacheDuration);
      
      // 确保切换用户后更新卡片显示（重要：解决切换用户时数据不显示的问题）
      this.updateCard();
    });
  }

  // 设置默认数据（当实体不存在时使用）
  setDefaultData() {
    // 设置默认的实体数据
    const defaultEntityData = {
      yearlist: [],
      monthlist: [],
      daylist: [],
      syn: '未知',
      latest_data: '未知'
    };
    
    // 处理默认数据
    this.processEntityData(defaultEntityData);
    
    // 更新卡片显示
    this.updateCardWithDefaultData();
  }

  // 使用默认数据更新卡片显示
  updateCardWithDefaultData() {
    // 设置余额为0
    if (this.balanceEl) {
      this.balanceEl.textContent = '0.00';
    }
    
    // 设置日期信息
    if (this.dateEl) {
      this.dateEl.textContent = '更新时间 未知';
    }
    
    if (this.dataDateEl) {
      this.dataDateEl.textContent = '数据: 未知';
    }
    
    // 设置默认的用电数据
    if (this.currentMonthEleEl) {
      this.currentMonthEleEl.textContent = '0';
    }
    
    if (this.currentMonthCostEl) {
      this.currentMonthCostEl.textContent = '0';
    }
    
    if (this.lastMonthEleEl) {
      this.lastMonthEleEl.textContent = '0';
    }
    
    if (this.lastMonthCostEl) {
      this.lastMonthCostEl.textContent = '0';
    }
    
    if (this.yearEleEl) {
      this.yearEleEl.textContent = '0';
    }
    
    if (this.yearCostEl) {
      this.yearCostEl.textContent = '0';
    }
    
    // 隐藏分时用电条（因为没有数据）
    const distributionBars = this.shadowRoot.querySelectorAll('.time-distribution-bar');
    distributionBars.forEach(bar => {
      bar.classList.add('empty');
    });
    
    const distributionLabels = this.shadowRoot.querySelectorAll('.time-distribution-labels');
    distributionLabels.forEach(label => {
      label.classList.add('empty');
    });
  }
  
  // 获取当前缓存键
  getCurrentCacheKey() {
    const info = this.currentUserKey || 'default';
    const utilityType = this.utilityType || 'ele';
    return `${info}_${utilityType}`;
  }
  
  // 检查缓存是否有效
  isCacheValid(cacheKey) {
    if (!this._dataCache.has(cacheKey)) return false;
    
    const expiryTime = this._cacheExpiry.get(cacheKey);
    if (!expiryTime) return false;
    
    return Date.now() < expiryTime;
  }
  
  // 从实体中提取数据（支持字段映射）
  extractDataFromEntity(entity) {
    const attributes = entity.attributes || {};
    const mapping = this.fieldMapping || {};

    // 【重要】优先判断是否使用data节点（电力数据可能在data节点下）
    const useDataNode = this.isUsingDataNode(entity);

    // 判断是否有node（有node表示数据在attributes的某个节点下）
    const hasNode = mapping.node;
    // 确定实际的数据源：如果使用data节点，则从attributes.data获取，否则从attributes获取
    const attributesSource = useDataNode ? (attributes.data || attributes) : attributes;
    const dataNode = hasNode ? attributesSource[mapping.node] : attributesSource;

    // 提取数据（如果无node，则直接从attributesSource取）
    const rawData = hasNode ? dataNode : attributesSource;

    // 根据字段映射转换数据
    let convertedData;

    // 如果 rawData 本身就是数组（说明我们已经定位到具体节点，如 daylist）
    if (hasNode && Array.isArray(rawData)) {
      const nodeKey = mapping.node; // 例如 'daylist'

      convertedData = {
        yearlist: [],
        monthlist: [],
        daylist: [],
        syn: this.getEntityAttribute(entity, mapping.syn),
        latest_data: this.getEntityAttribute(entity, mapping.latest_data)
      };

      // 根据 node 类型设置对应的数组
      if (nodeKey === 'daylist') {
        convertedData.daylist = rawData;
      } else if (nodeKey === 'monthlist') {
        convertedData.monthlist = rawData;
      } else if (nodeKey === 'yearlist') {
        convertedData.yearlist = rawData;
      }
    } else {
      // 正常情况：从对象中提取各个字段
      convertedData = {
        yearlist: this.extractArrayData(rawData, mapping, 'yearlist', 'yearlist'),
        monthlist: this.extractArrayData(rawData, mapping, 'monthlist', 'monthlist'),
        daylist: this.extractArrayData(rawData, mapping, 'daylist', 'daylist'),
        syn: this.getEntityAttribute(entity, mapping.syn),
        latest_data: this.getEntityAttribute(entity, mapping.latest_data)
      };
    }

    // 如果 utility_type 不是 'ele' 且没有 monthlist/yearlist，从 daylist 自动计算
    if (this.utilityType !== 'ele' && convertedData.daylist && convertedData.daylist.length > 0) {
      // 如果没有 monthlist，从 daylist 计算
      if (!convertedData.monthlist || convertedData.monthlist.length === 0) {
        convertedData.monthlist = this.calculateMonthlyData(convertedData.daylist, mapping);
      }

      // 如果没有 yearlist，从 daylist 计算
      if (!convertedData.yearlist || convertedData.yearlist.length === 0) {
        convertedData.yearlist = this.calculateYearlyData(convertedData.daylist, mapping);
      }
    }

    // 如果配置了syn字段，显示date-info
    if (mapping.syn && this.dateEl) {
      const synValue = this.getEntityAttribute(entity, mapping.syn);
      if (synValue !== undefined) {
        this.dateEl.textContent = `更新时间 ${synValue}`;
      }
    } else if (this.utilityType === 'ele' && this.dateEl) {
      // 电力类型：显示同步时间
      // 优先从 entity 的顶层节点的 date 字段获取
      let date = attributes.date;
      
      // 如果获取不到，再从 entity 的 data 节点的 date 字段获取（data.date）
      if (!date) {
        try {
          date = attributes.data?.date || '';
        } catch (e) {
          date = '';
        }
      }
      
      // 显示为"同步：yyyy-mm-dd hh:mm:ss"
      this.dateEl.textContent = `同步: ${date}`;
    } else if (this.utilityType !== 'ele' && this.dateEl) {
      // 非电力类型：显示为"同步: yyyy-mm-dd hh:mm:ss"，从entity的date字段获取
      const dateValue = this.getEntityAttribute(entity, 'date');
      if (dateValue !== undefined) {
        this.dateEl.textContent = `同步: ${dateValue}`;
      }
    }

    // 如果配置了latest_data字段，显示data-date-info
    if (mapping.latest_data && this.dataDateEl) {
      const latestDataValue = this.getEntityAttribute(entity, mapping.latest_data);
      if (latestDataValue !== undefined) {
        this.dataDateEl.textContent = `数据:${latestDataValue}`;
        // 获取最后一天数据用于显示
        const daylist = convertedData.daylist || [];
        const lastDayData = daylist.length > 0 ? this._extractLastDayRawData(daylist[0], mapping) : null;
        // 计算并显示相对日期
        this.updateRelativeDate(latestDataValue, lastDayData);
      }
    } else if (this.utilityType === 'ele' && this.dataDateEl) {
      // 电力类型沿用现有逻辑 - 直接设置数据日期
      const daylist = convertedData.daylist || [];
      const dataDate = daylist && daylist.length > 0 && daylist[0][mapping.date || 'day'] ? daylist[0][mapping.date || 'day'] : '--';
      this.dataDateEl.textContent = `数据: ${dataDate}`;
      // 获取最后一天数据用于显示
      const lastDayData = daylist.length > 0 ? this._extractLastDayRawData(daylist[0], mapping) : null;
      // 计算并显示相对日期
      this.updateRelativeDate(dataDate, lastDayData);
    } else if (this.utilityType !== 'ele' && this.dataDateEl) {
      // 非电力类型：显示为"数据: yyyy-mm-dd"，从entity的daylist字段中的最新day处获取
      const daylist = convertedData.daylist || [];
      if (daylist && daylist.length > 0) {
        // 获取最新的day数据（第一条是最新的）
        const latestDayData = daylist[0];
        const dateField = mapping.date || 'day';
        const dataDate = latestDayData[dateField] || '--';
        this.dataDateEl.textContent = `数据: ${dataDate}`;
        // 计算并显示相对日期
        const lastDayData = this._extractLastDayRawData(latestDayData, mapping);
        this.updateRelativeDate(dataDate, lastDayData);
      } else {
        this.dataDateEl.textContent = '数据: --';
        // 清空相对日期
        if (this.relativeDateEl) {
          this.relativeDateEl.textContent = '';
          this.relativeDateEl.className = 'relative-date-info';
        }
      }
    }

    return convertedData;
  }
  
  // 提取数组数据
  extractArrayData(rawData, mapping, defaultKey, targetKey) {
    // 如果 rawData 本身就是数组，直接返回（例如燃气数据：daylist 节点直接是数组）
    if (Array.isArray(rawData)) {
      return rawData;
    }
    
    const value = rawData[mapping[targetKey] || defaultKey];
    if (Array.isArray(value)) {
      return value;
    }
    
    // 如果是字符串，尝试解析为JSON
    if (typeof value === 'string') {
      try {
        return JSON.parse(value);
      } catch (e) {
        return [];
      }
    }
    
    return [];
  }
  
  // 从日数据计算月合计数据
  calculateMonthlyData(daylist, mapping) {
    if (!daylist || !Array.isArray(daylist) || daylist.length === 0) {
      return [];
    }
    
    const monthlyMap = new Map();
    const dateField = mapping.date || 'day';
    const usageField = mapping.usage || 'f_gas';
    const amountField = mapping.amount || 'e_gas';
    
    daylist.forEach(item => {
      const dateStr = item[dateField];
      if (!dateStr) return;
      
      // 处理日期字符串，移除可能的双引号
      const cleanDateStr = dateStr.replace(/"/g, '');
      const date = new Date(cleanDateStr);
      if (isNaN(date.getTime())) return;
      
      const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      
      const usage = this.safeParseFloat(item[usageField]);
      const amount = this.safeParseFloat(item[amountField]);
      
      if (!monthlyMap.has(monthKey)) {
        monthlyMap.set(monthKey, {
          month: monthKey,
          monthEleNum: 0,
          monthEleCost: 0,
          unit: this.getUnitByUtilityType(this.utilityType)
        });
      }
      
      const monthData = monthlyMap.get(monthKey);
      monthData.monthEleNum += usage;
      monthData.monthEleCost += amount;
    });
    
    // 转换为数组并保留两位小数
    const result = Array.from(monthlyMap.values()).map(item => ({
      ...item,
      monthEleNum: parseFloat(item.monthEleNum.toFixed(2)),
      monthEleCost: parseFloat(item.monthEleCost.toFixed(2))
    }));
    
    // 按月份排序（降序）
    return result.sort((a, b) => b.month.localeCompare(a.month));
  }
  
  // 从日数据计算年合计数据
  calculateYearlyData(daylist, mapping) {
    if (!daylist || !Array.isArray(daylist) || daylist.length === 0) {
      return [];
    }
    
    const yearlyMap = new Map();
    const dateField = mapping.date || 'day';
    const usageField = mapping.usage || 'f_gas';
    const amountField = mapping.amount || 'e_gas';
    
    daylist.forEach(item => {
      const dateStr = item[dateField];
      if (!dateStr) return;
      
      // 处理日期字符串，移除可能的双引号
      const cleanDateStr = dateStr.replace(/"/g, '');
      const date = new Date(cleanDateStr);
      if (isNaN(date.getTime())) return;
      
      const yearKey = date.getFullYear().toString();
      
      const usage = this.safeParseFloat(item[usageField]);
      const amount = this.safeParseFloat(item[amountField]);
      
      if (!yearlyMap.has(yearKey)) {
        yearlyMap.set(yearKey, {
          year: yearKey,
          yearEleNum: 0,
          yearEleCost: 0,
          unit: this.getUnitByUtilityType(this.utilityType)
        });
      }
      
      const yearData = yearlyMap.get(yearKey);
      yearData.yearEleNum += usage;
      yearData.yearEleCost += amount;
    });
    
    // 转换为数组并保留两位小数
    const result = Array.from(yearlyMap.values()).map(item => ({
      ...item,
      yearEleNum: parseFloat(item.yearEleNum.toFixed(2)),
      yearEleCost: parseFloat(item.yearEleCost.toFixed(2))
    }));
    
    // 按年份排序（降序）
    return result.sort((a, b) => b.year.localeCompare(a.year));
  }
  
  // 加载并合并数据（包括JSON文件）
  async loadAndMergeData(entityData) {
    // 转换实体数据为标准格式
    const user = this.getCurrentCacheKey();
    this.standardData = {
      dayUsage: this.convertDayList(entityData.daylist || [], user),
      monthUsage: this.convertMonthList(entityData.monthlist || [], user),
      yearUsage: this.convertYearList(entityData.yearlist || [], user),
      payRecords: [],
      unit: this.getUnitByUtilityType(this.utilityType)
    };
    
    // 保存数据到实例变量
    this.daylistData = entityData.daylist || [];
    this.monthlistData = entityData.monthlist || [];
    this.yearlistData = entityData.yearlist || [];
    
    // 标记历史数据已加载
    this.historicalDataLoaded = true;
    
    // 更新卡片显示
    this.updateCard();
  }
  
  // 处理实体数据（从缓存）
  processEntityData(entityData) {
    // 转换数据（与loadAndMergeData类似，但不加载历史数据）
    const user = this.getCurrentCacheKey();
    this.standardData = {
      dayUsage: this.convertDayList(entityData.daylist || [], user),
      monthUsage: this.convertMonthList(entityData.monthlist || [], user),
      yearUsage: this.convertYearList(entityData.yearlist || [], user),
      payRecords: [],
      unit: this.getUnitByUtilityType(this.utilityType)
    };
    
    // 保存数据到实例变量
    this.daylistData = entityData.daylist || [];
    this.monthlistData = entityData.monthlist || [];
    this.yearlistData = entityData.yearlist || [];
    
    // 标记数据已加载（重要：确保updateCard可以正常显示数据）
    this.historicalDataLoaded = true;
    
    // 更新卡片显示
    this.updateCard();
  }

  // 控制分时用电显示
  updateTimeDistributionVisibility(config) {
    // 默认显示分时用电
    const showTimeDistribution = config.show_time_distribution !== undefined ? config.show_time_distribution : true;
    
    // 获取所有分时用电相关元素
    const timeDistributionBars = [
      this.currentMonthDistributionEl,
      this.lastMonthDistributionEl,
      this.yearDistributionEl
    ];
    
    const timeLabels = [
      this.currentMonthLabelsEl,
      this.lastMonthLabelsEl,
      this.yearLabelsEl
    ];
    
    if (showTimeDistribution) {
      // 显示分时用电条和标签
      timeDistributionBars.forEach(el => el.classList.remove('hidden'));
      timeLabels.forEach(el => el.classList.remove('hidden'));
    } else {
      // 隐藏分时用电条和标签
      timeDistributionBars.forEach(el => el.classList.add('hidden'));
      timeLabels.forEach(el => el.classList.add('hidden'));
    }
  }

  // 元素连接到DOM时的回调
  connectedCallback() {
    this._isCardVisible = true;
    
    // 设置IntersectionObserver来检测卡片可见性
    this._setupVisibilityObserver();
    
    // 如果配置已设置，初始化余额显示
    if (this._config) {
      this.updateAllUsersBalance();
    }
    
    // 如果配置已设置且数据未加载，加载数据
    if (this._config && this.currentConfig && !this.historicalDataLoaded) {
      this.loadDataForCurrentUser();
    }
    
    // 启动余额刷新定时器（10秒）
    this.startBalanceUpdateTimer();

    // 分时电价会在时段边界切换，不依赖下一次电费数据同步。
    this._priceUpdateTimer = setInterval(() => {
      if (this._isCardVisible && this.standardData) {
        this.updateTierIndicator(this.currentPeriodUsage || 0);
      }
    }, 60000);

  }
  
  // 设置可见性观察器
  _setupVisibilityObserver() {
    if (!window.IntersectionObserver) return;
    
    if (this._visibilityObserver) {
      this._visibilityObserver.disconnect();
    }
    
    this._visibilityObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        this._isCardVisible = entry.isIntersecting;
        
        // 如果卡片变为可见且需要加载数据，则加载
        if (this._isCardVisible && this._config && this.currentConfig && !this.historicalDataLoaded) {
          this.loadDataForCurrentUser();
        }
      });
    });
    
    this._visibilityObserver.observe(this);
  }

  // 元素从DOM中移除时的回调
  disconnectedCallback() {
    this._isCardVisible = false;
    
    // 清理所有定时器和监听器
    this.stopThemeTimer();
    this.stopPhoneThemeListener();
    
    // 停止余额刷新定时器
    this.stopBalanceUpdateTimer();
    if (this._priceUpdateTimer) {
      clearInterval(this._priceUpdateTimer);
      this._priceUpdateTimer = null;
    }
    
    // 销毁缴费方式饼图实例
    if (this.paySourceChart) {
      this.paySourceChart.dispose();
      this.paySourceChart = null;
    }
    
    // 断开可见性观察器
    if (this._visibilityObserver) {
      this._visibilityObserver.disconnect();
      this._visibilityObserver = null;
    }
    
    // 清理移到document.body的模态框（将它们移回shadow DOM以便正确清理）
    if (this.dayModalEl && this.dayModalEl.parentElement === document.body) {
      this.dayModalEl.style.display = 'none';
      // 移回shadow DOM以便组件销毁时自动清理
      if (this.shadowRoot) {
        this.shadowRoot.appendChild(this.dayModalEl);
      }
    }
    
    if (this.payHistoryModalEl && this.payHistoryModalEl.parentElement === document.body) {
      this.payHistoryModalEl.style.display = 'none';
      // 移回shadow DOM以便组件销毁时自动清理
      if (this.shadowRoot) {
        this.shadowRoot.appendChild(this.payHistoryModalEl);
      }
    }
    
    // 清理移到document.body的tooltip
    if (this.eventTooltip && this.eventTooltip.parentElement === document.body) {
      this.eventTooltip.style.display = 'none';
      if (this.shadowRoot) {
        this.shadowRoot.appendChild(this.eventTooltip);
      }
    }
  }
  
  // 启动余额刷新定时器（10秒）
  startBalanceUpdateTimer() {
    if (this._balanceUpdateInterval) return;
    
    this._balanceUpdateInterval = setInterval(() => {
      if (this._isCardVisible && this._hass && this.entityId) {
        this.updateBalanceDisplay();
      }
    }, 10000); // 10秒
  }
  
  // 停止余额刷新定时器
  stopBalanceUpdateTimer() {
    if (this._balanceUpdateInterval) {
      clearInterval(this._balanceUpdateInterval);
      this._balanceUpdateInterval = null;
    }
  }
  
  // 更新余额显示（当前用户）
  updateBalanceDisplay() {
    if (!this._hass || !this.entityId || !this.balanceEl) return;

    const entity = this._hass.states[this.entityId];
    if (entity) {
      // 优先从entity.state获取余额，如果state不是数值，则尝试从data节点获取
      let balance = parseFloat(entity.state);
      if (isNaN(balance)) {
        // 如果state不是数值，尝试从data.balance获取
        balance = parseFloat(this.getEntityAttribute(entity, 'balance')) || 0;
      }
      this.balanceEl.textContent = balance.toFixed(2);
    } else {
      // 实体不存在，设置默认余额
      this.balanceEl.textContent = '0.00';
    }

    // 同时更新所有用户的余额（包括当前用户）
    this.updateAllUsersBalance();
  }
  
  // 更新所有用户的余额显示
  updateAllUsersBalance() {
    if (!this._hass || !this.showMultiUserBar || !this.userBlocks) return;
    
    const userKeys = Object.keys(this.multiClassConfig);
    
    userKeys.forEach((key, index) => {
      const config = this.multiClassConfig[key];
      const entityId = config.entity ? config.entity.split(',')[0].trim() : '';
      
      if (!entityId) return;
      
      const entity = this._hass.states[entityId];
      const userBlock = this.userBlocks[index];
      
      if (userBlock) {
        const balanceDiv = userBlock.querySelector('.user-block-balance');
        if (balanceDiv) {
          if (entity && entity.state !== 'unknown' && entity.state !== 'unavailable') {
            // 实体存在且状态正常，显示实际余额
            const balance = parseFloat(entity.state) || 0;
            balanceDiv.textContent = `¥${balance.toFixed(2)}`;
          } else {
            // 实体不存在或状态为unknown/unavailable，显示"--"
            balanceDiv.textContent = '--';
          }
        }
      }
    });
  }



  // 更新卡片宽度配置
  updateCardWidth() {
    // 从顶层配置获取卡片宽度，如果未配置则自适应宽度
    const cardWidth = this._config.card_width;

    if (cardWidth) {
      // 如果配置了具体的宽度，则使用该宽度
      this.electricityCardEl.style.maxWidth = cardWidth;
      this.electricityCardEl.style.width = cardWidth;
      // 模态框内容宽度为卡片宽度的95%
      this.dayModalContentEl.style.width = `calc(${cardWidth} * 0.95)`;
    } else {
      // 如果未配置宽度，则恢复自适应行为（移除最大宽度限制）
      this.electricityCardEl.style.maxWidth = 'none';
      this.electricityCardEl.style.width = 'auto';
      // 模态框内容恢复默认的90%
      this.dayModalContentEl.style.width = '90%';
    }
  }

  // 重置所有隐藏元素的显示状态（切换用户时调用）
  resetHiddenElements() {
    // 重置 price-display
    const priceDisplays = this.shadowRoot.querySelectorAll('.price-display');
    priceDisplays.forEach(el => el.style.display = '');
    
    // 重置 electricity-price-display
    const electricityPriceDisplay = this.shadowRoot.querySelector('.electricity-price-display');
    if (electricityPriceDisplay) electricityPriceDisplay.style.display = '';
    
    // 重置 remaining-days-display
    const remainingDaysDisplay = this.shadowRoot.querySelector('.remaining-days-display');
    if (remainingDaysDisplay) remainingDaysDisplay.style.display = '';
    
    // 重置 tier-indicator
    const tierIndicator = this.shadowRoot.querySelector('.tier-indicator');
    const tierIndicatorContainer = this.shadowRoot.querySelector('.tier-indicator-container');
    if (tierIndicator) tierIndicator.style.display = '';
    if (tierIndicatorContainer) tierIndicatorContainer.style.display = '';
    
    // 重置 time-distribution-bar
    const timeDistributionBars = this.shadowRoot.querySelectorAll('.time-distribution-bar');
    timeDistributionBars.forEach(el => el.style.display = '');
    // 重置对应的标签（移除hidden类）
    const timeDistributionLabels = this.shadowRoot.querySelectorAll('.time-distribution-labels');
    timeDistributionLabels.forEach(el => el.classList.remove('hidden'));
    
    // 重置 data-container
    const dataContainer = this.shadowRoot.querySelector('.data-container');
    if (dataContainer) dataContainer.style.display = '';
    
    // 重置 pie-chart-section
    const pieChartSections = this.shadowRoot.querySelectorAll('.pie-chart-section');
    pieChartSections.forEach(el => el.style.display = '');
    
    // 重置 timeline-container
    const timelineContainers = this.shadowRoot.querySelectorAll('#timeline-container');
    timelineContainers.forEach(el => el.style.display = '');
    
    // 重置 calendar-stats
    const calendarStatsList = [
      this.shadowRoot.getElementById('cal-month-usage'),
      this.shadowRoot.getElementById('cal-month-cost'),
      this.shadowRoot.getElementById('cal-year-usage'),
      this.shadowRoot.getElementById('cal-year-cost')
    ];
    calendarStatsList.forEach(el => {
      if (el && el.parentElement) el.parentElement.style.display = '';
    });
    
    // 重置统计信息的标签
    const calendarStatsSection = this.shadowRoot.querySelector('.calendar-stats');
    if (calendarStatsSection) {
      calendarStatsSection.style.display = '';
    }
  }

  // 应用隐藏配置
  applyHiddenConfig() {
    // 优先使用当前用户的hide配置，如果没有则使用顶层配置
    const hideConfig = this.currentConfig && this.currentConfig.hide ? this.currentConfig.hide : 
                       (this._config && this._config.hide ? this._config.hide : '');
    
    if (!hideConfig) return;

    // 先重置所有隐藏元素的显示状态（重要：切换用户时需要重置）
    this.resetHiddenElements();

    // 解析隐藏配置（支持多个值，用逗号分隔）
    const hiddenItems = hideConfig.split(',').map(item => item.trim()).filter(item => item);
    
    // 隐藏price-display（所有价格显示区域）
    if (hiddenItems.includes('price-display')) {
      const priceDisplays = this.shadowRoot.querySelectorAll('.price-display');
      priceDisplays.forEach(el => el.style.display = 'none');
    }
    
    // 隐藏electricity-price-display（电价显示区域）
    if (hiddenItems.includes('electricity-price-display')) {
      const electricityPriceDisplay = this.shadowRoot.querySelector('.electricity-price-display');
      if (electricityPriceDisplay) electricityPriceDisplay.style.display = 'none';
    }
    
    // 隐藏remaining-days-display（剩余天数显示区域）
    if (hiddenItems.includes('remaining-days-display')) {
      const remainingDaysDisplay = this.shadowRoot.querySelector('.remaining-days-display');
      if (remainingDaysDisplay) remainingDaysDisplay.style.display = 'none';
    }
    
    // 隐藏tier-indicator（用电阶梯指示器）
    if (hiddenItems.includes('tier-indicator')) {
      const tierIndicator = this.shadowRoot.querySelector('.tier-indicator');
      const tierIndicatorContainer = this.shadowRoot.querySelector('.tier-indicator-container');
      if (tierIndicator) tierIndicator.style.display = 'none';
      if (tierIndicatorContainer) tierIndicatorContainer.style.display = 'none';
    }
    
    // 隐藏time-distribution-bar（分时用电条）
    if (hiddenItems.includes('time-distribution-bar')) {
      const timeDistributionBars = this.shadowRoot.querySelectorAll('.time-distribution-bar');
      timeDistributionBars.forEach(el => el.style.display = 'none');
      // 同时隐藏对应的标签（添加hidden类）
      const timeDistributionLabels = this.shadowRoot.querySelectorAll('.time-distribution-labels');
      timeDistributionLabels.forEach(el => el.classList.add('hidden'));
    }
    
    // 隐藏data-container（统计数据容器）
    if (hiddenItems.includes('data-container')) {
      const dataContainer = this.shadowRoot.querySelector('.data-container');
      if (dataContainer) dataContainer.style.display = 'none';
    }
    
    // 注意：user-info 和 multi-user-info 的显示现在由顶层的 show_name 控制，不再通过 hide 配置
    
    // 隐藏pie-chart-section（饼图区域）
    if (hiddenItems.includes('pie-chart-section')) {
      const pieChartSections = this.shadowRoot.querySelectorAll('.pie-chart-section');
      pieChartSections.forEach(el => el.style.display = 'none');
    }
    
    // 隐藏timeline-container（设备时间线容器）
    if (hiddenItems.includes('timeline-container')) {
      const timelineContainers = this.shadowRoot.querySelectorAll('#timeline-container');
      timelineContainers.forEach(el => el.style.display = 'none');
    }
    
    // 隐藏calendar-stats（日历统计信息）
    if (hiddenItems.includes('calendar-stats')) {
      const calendarStatsList = [
        this.shadowRoot.getElementById('cal-month-usage'),
        this.shadowRoot.getElementById('cal-month-cost'),
        this.shadowRoot.getElementById('cal-year-usage'),
        this.shadowRoot.getElementById('cal-year-cost')
      ];
      calendarStatsList.forEach(el => {
        if (el) el.parentElement.style.display = 'none';
      });
      
      // 也隐藏统计信息的标签
      const calendarStatsSection = this.shadowRoot.querySelector('.calendar-stats');
      if (calendarStatsSection) {
        calendarStatsSection.style.display = 'none';
      }
    }
  }

  // 根据主题实体实时更新主题
  updateThemeFromEntity() {
    if (!this._config || !this._hass) return;

    const theme = this._config.theme;
    let entityState, isSelectEntity;

    // 新的配置格式：实体模式
    if (typeof theme === 'object' && theme !== null && theme.entity && this._hass.states[theme.entity]) {
      const themeEntity = this._hass.states[theme.entity];
      entityState = themeEntity.state;
      isSelectEntity = theme.entity.toLowerCase().includes('select');
    }
    // 旧的实体ID格式（向后兼容）
    else if (typeof theme === 'string' && this._hass.states[theme]) {
      const themeEntity = this._hass.states[theme];
      entityState = themeEntity.state;
      isSelectEntity = theme.toLowerCase().includes('select');
    } else {
      return;
    }

    // 确定主题名称
    const themeName = this.determineThemeFromEntityState(entityState, isSelectEntity);

    // 保存主题名称
    this.lastThemeName = themeName;

    // 应用主题
    this.applyThemeInternal(themeName);
  }

  // ==================== 日历视图相关方法 ====================
  
  // 初始化日历事件监听
  initCalendarEvents() {
    // 为data-container中的统计卡片添加点击事件
    const statCards = this.shadowRoot.querySelectorAll('[data-type]');
    statCards.forEach(card => {
      card.addEventListener('click', (e) => {
        // 阻止移动端双击缩放
        e.preventDefault();
        this.showCalendarView(card.dataset.type);
      });
      card.style.cursor = 'pointer';
      
      // 添加touch事件处理，防止移动端双击缩放
      let lastTouchEnd = 0;
      card.addEventListener('touchend', (e) => {
        const now = Date.now();
        if (now - lastTouchEnd <= 300) {
          e.preventDefault();
        }
        lastTouchEnd = now;
      }, false);
    });
    
    // 日详情模态框关闭按钮
    this.dayModalCloseEl.addEventListener('click', () => this.hideDayModal());
    this.dayModalEl.addEventListener('click', (e) => {
      if (e.target === this.dayModalEl) {
        this.hideDayModal();
      }
    });

    // 缴费历史模态框关闭按钮
    this.payHistoryCloseEl.addEventListener('click', () => this.hidePayHistoryModal());
    this.payHistoryModalEl.addEventListener('click', (e) => {
      if (e.target === this.payHistoryModalEl) {
        this.hidePayHistoryModal();
      }
    });

    // 点击余额金额显示缴费历史
    this.shadowRoot.querySelector('.balance-amount').addEventListener('click', () => this.showPayHistoryModal());
    this.shadowRoot.querySelector('.balance-amount').style.cursor = 'pointer';

    // 点击tooltip外部时隐藏tooltip
    document.addEventListener('click', (e) => {
      if (!this.eventTooltip) return;
      const isClickInsideTooltip = e.composedPath().some(el => el === this.eventTooltip);
      if (!isClickInsideTooltip) {
        this.hideTooltip();
      }
    });
    
    // 返回按钮
    this.backToMainBtnEl.addEventListener('click', () => this.hideCalendarView());
    
    // 本月按钮
    this.currentMonthBtnEl.addEventListener('click', () => {
      const now = new Date();
      this.calCurrentYear = now.getFullYear();
      this.calCurrentMonth = now.getMonth() + 1;
      this.calYearSelectEl.value = this.calCurrentYear;
      this.calMonthSelectEl.value = this.calCurrentMonth;
      this.updateCalendarView();
    });
    
    // 年份和月份选择
    this.calYearSelectEl.addEventListener('change', () => {
      this.calCurrentYear = parseInt(this.calYearSelectEl.value);
      this.updateCalendarView();
    });
    
    this.calMonthSelectEl.addEventListener('change', () => {
      this.calCurrentMonth = parseInt(this.calMonthSelectEl.value);
      this.updateCalendarView();
    });
    
    // 选项卡切换
    const tabBtns = this.shadowRoot.querySelectorAll('.cal-tab-btn');
    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentView = btn.dataset.view;
        this.updateViewByType(btn.dataset.view);
      });
    });
    
    // 初始化年份选择器
    this.initYearSelector();
    
    // 设置初始年月
    const now = new Date();
    this.calCurrentYear = now.getFullYear();
    this.calCurrentMonth = now.getMonth() + 1;
    this.calYearSelectEl.value = this.calCurrentYear;
    this.calMonthSelectEl.value = this.calCurrentMonth;
  }
  
  // 初始化年份选择器
  initYearSelector() {
    if (!this.daylistData || this.daylistData.length === 0) {
      const now = new Date();
      this.availableYears = [now.getFullYear()];
    } else {
      // 从daylist中提取所有年份
      const years = new Set();
      this.daylistData.forEach(dayData => {
        if (dayData.day) {
          const year = parseInt(dayData.day.split('-')[0]);
          years.add(year);
        }
      });
      this.availableYears = Array.from(years).sort((a, b) => b - a);
      
      // 确保当前年份也在列表中
      const currentYear = new Date().getFullYear();
      if (!this.availableYears.includes(currentYear)) {
        this.availableYears.push(currentYear);
        this.availableYears.sort((a, b) => b - a);
      }
    }
    
    // 填充年份选择器
    this.calYearSelectEl.innerHTML = '';
    this.availableYears.forEach(year => {
      const option = document.createElement('option');
      option.value = year;
      option.textContent = year;
      this.calYearSelectEl.appendChild(option);
    });
  }
  
  // 显示日历视图
  showCalendarView(type) {
    this.isCalendarView = true;
    this.dataContainerEl.style.display = 'none';
    this.calendarViewEl.style.display = 'block';
    
    // 根据点击的类型设置年月
    const now = new Date();
    if (type === 'current-month') {
      this.calCurrentYear = now.getFullYear();
      this.calCurrentMonth = now.getMonth() + 1;
    } else if (type === 'last-month') {
      const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1);
      this.calCurrentYear = lastMonth.getFullYear();
      this.calCurrentMonth = lastMonth.getMonth() + 1;
    } else if (type === 'year') {
      this.calCurrentYear = now.getFullYear();
      this.calCurrentMonth = 1;
    }
    
    // 更新年份选择器（以防数据有更新）
    this.initYearSelector();
    
    // 在initYearSelector之后设置选中的年份和月份，避免被覆盖
    this.calYearSelectEl.value = this.calCurrentYear;
    this.calMonthSelectEl.value = this.calCurrentMonth;
    
    // 使用 requestAnimationFrame 确保 calendarViewEl 完全显示后再切换视图
    requestAnimationFrame(() => {
      // 根据类型显示不同的视图
      if (type === 'year') {
        // 点击年度统计时，显示年度图表
        this.currentView = 'year';
        // 更新选项卡的 active 状态
        const tabBtns = this.shadowRoot.querySelectorAll('.cal-tab-btn');
        tabBtns.forEach(btn => {
          btn.classList.remove('active');
          if (btn.dataset.view === 'year') {
            btn.classList.add('active');
          }
        });
        this.updateViewByType('year');
        
        // 直接点击"年"按钮，避免有时不渲染的问题
        setTimeout(() => {
          const yearTab = this.shadowRoot.querySelector('.cal-tab-btn[data-view="year"]');
          if (yearTab) {
            yearTab.click();
            // 再点击年视图中的"年度"按钮
            setTimeout(() => {
              // 查找所有包含"年度"文本的按钮
              const yearButtons = this.shadowRoot.querySelectorAll('.year-tag');
              const yearViewAllBtn = Array.from(yearButtons).find(btn => btn.textContent === '年度');
              if (yearViewAllBtn) {
                yearViewAllBtn.click();
              }
            }, 100);
          }
        }, 500);
      } else {
        // 其他情况显示日历视图（本月用电和上月用电）
        this.currentView = 'calendar';
        // 更新选项卡的 active 状态
        const tabBtns = this.shadowRoot.querySelectorAll('.cal-tab-btn');
        tabBtns.forEach(btn => {
          btn.classList.remove('active');
          if (btn.dataset.view === 'calendar') {
            btn.classList.add('active');
          }
        });
        this.updateCalendarView();
        
        // 直接点击"日历"按钮，避免有时不渲染的问题
        setTimeout(() => {
          const calendarTab = this.shadowRoot.querySelector('.cal-tab-btn[data-view="calendar"]');
          if (calendarTab) {
            calendarTab.click();
          }
        }, 500);
      }
    });
  }
  
  // 隐藏日历视图
  hideCalendarView() {
    this.isCalendarView = false;
    this.dataContainerEl.style.display = 'flex';
    this.calendarViewEl.style.display = 'none';
    // 销毁所有图表
    this.destroyYearCharts();
    this.destroyMonthCharts();
    this.destroyDayCharts();
  }
  
  // 根据视图类型更新显示
  updateViewByType(viewType) {
    // 隐藏所有视图内容
    this.calendarContentEl.style.display = 'none';
    this.yearContentEl.style.display = 'none';
    this.monthContentEl.style.display = 'none';
    this.dayContentEl.style.display = 'none';
    this.calendarControlsEl.style.display = 'none';

    if (viewType === 'year') {
      // 显示年视图
      this.yearContentEl.style.display = 'block';
      // 检查历史数据是否已加载
      if (!this.historicalDataLoaded && (!this.yearlistData || this.yearlistData.length === 0)) {
        // 在图表容器中显示加载提示
        if (this.yearComboChartEl) {
          this.yearComboChartEl.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-color);">加载历史数据中...</div>';
        }
        // 等待数据加载完成后重新渲染
        const checkData = setInterval(() => {
          if (this.historicalDataLoaded && this.yearlistData && this.yearlistData.length > 0) {
            clearInterval(checkData);
            // 恢复图表容器
            if (this.yearComboChartEl) {
              this.yearComboChartEl.innerHTML = '';
            }
            requestAnimationFrame(() => {
              this.renderYearView();
              setTimeout(() => {
                if (this.yearChart) {
                  this.yearChart.resize();
                }
              }, 10);
            });
          }
        }, 100);
        // 10秒后停止检查，避免无限等待
        setTimeout(() => clearInterval(checkData), 10000);
      } else {
        // 使用 requestAnimationFrame 确保在下一帧渲染，等待容器布局完成
        requestAnimationFrame(() => {
          this.renderYearView();
          // 延迟调用resize以确保容器已完成布局
          setTimeout(() => {
            if (this.yearChart) {
              this.yearChart.resize();
            }
          }, 10);
        });
      }
    } else if (viewType === 'month') {
      // 显示月视图
      this.monthContentEl.style.display = 'block';
      // 检查历史数据是否已加载
      if (!this.historicalDataLoaded && (!this.monthlistData || this.monthlistData.length === 0)) {
        // 在图表容器中显示加载提示
        if (this.monthComboChartEl) {
          this.monthComboChartEl.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-color);">加载历史数据中...</div>';
        }
        // 等待数据加载完成后重新渲染
        const checkData = setInterval(() => {
          if (this.historicalDataLoaded && this.monthlistData && this.monthlistData.length > 0) {
            clearInterval(checkData);
            // 恢复图表容器
            if (this.monthComboChartEl) {
              this.monthComboChartEl.innerHTML = '';
            }
            requestAnimationFrame(() => {
              this.renderMonthView();
              setTimeout(() => {
                if (this.monthChart) {
                  this.monthChart.resize();
                }
              }, 10);
            });
          }
        }, 100);
        // 10秒后停止检查，避免无限等待
        setTimeout(() => clearInterval(checkData), 10000);
      } else {
        // 使用 requestAnimationFrame 确保在下一帧渲染，等待容器布局完成
        requestAnimationFrame(() => {
          this.renderMonthView();
          // 延迟调用resize以确保容器已完成布局
          setTimeout(() => {
            if (this.monthChart) {
              this.monthChart.resize();
            }
          }, 10);
        });
      }
    } else if (viewType === 'day') {
      // 显示日视图
      this.dayContentEl.style.display = 'block';
      // 使用 requestAnimationFrame 确保在下一帧渲染，等待容器布局完成
      requestAnimationFrame(() => {
        this.renderDayView();
        // 延迟调用resize以确保容器已完成布局
        setTimeout(() => {
          if (this.dayViewChart) {
            this.dayViewChart.resize();
          }
        }, 10);
      });
    } else {
      // 显示日历视图
      this.calendarContentEl.style.display = 'block';
      this.calendarControlsEl.style.display = 'flex';
      this.updateCalendarView();
    }
  }
  
  // 渲染年视图
  async renderYearView() {
    // 从统一数据接口获取数据
    if (!this.standardData || !this.standardData.yearUsage || this.standardData.yearUsage.length === 0) {
      return;
    }

    // 销毁现有图表
    this.destroyYearCharts();

    // 从统一格式准备数据
    const yearData = this.standardData.yearUsage;
    const years = yearData.map(item => item.time);
    const costs = yearData.map(item => item.total_amount);
    const peakData = yearData.map(item => item.usage_ele_peak || 0);
    const valleyData = yearData.map(item => item.usage_ele_valley || 0);
    const normalData = yearData.map(item => item.usage_ele_norm || 0);
    const sharpData = yearData.map(item => item.usage_ele_tip || 0);
    const noTimeData = yearData.map(item => item.usage_ele_no || 0);

    // 获取单位符号（从统一数据格式中获取，不设置默认值）
    const usageUnit = yearData.length > 0 ? yearData[0].unit : '';

    // 保存数据到缓存，用于重试
    this._yearChartData = { years, costs, peakData, valleyData, normalData, sharpData, noTimeData, usageUnit };

    // 生成年份选择器按钮
    this.generateYearFilterButtons(years);

    // 根据当前选中的视图类型渲染图表
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (this.selectedYearView === '总计') {
          this.renderYearTotalChart(usageUnit);
        } else if (this.selectedYearView === '年度') {
          this.renderYearComboChart(years, costs, peakData, valleyData, normalData, sharpData, noTimeData, usageUnit);
        } else if (this.selectedYearView === '热力图') {
          this.renderYearHeatmapChart();
        } else if (this.selectedYearView === '动态排名') {
          this.renderBarRacingChart();
        } else {
          // 单个年份，渲染饼图
          this.renderYearSingleChart(this.selectedYearView, usageUnit);
        }
      });
    });
  }

  // 生成年份选择器按钮
  generateYearFilterButtons(years) {
    // 获取两个容器
    const mainFilterEl = this.yearFilterMainEl;
    const yearsFilterEl = this.yearFilterYearsEl;

    if (!mainFilterEl || !yearsFilterEl) {
      return;
    }

    // 清空两个容器
    mainFilterEl.innerHTML = '';
    yearsFilterEl.innerHTML = '';

    // 添加"总计"按钮到主容器
    const totalBtn = document.createElement('button');
    totalBtn.className = 'year-tag';
    totalBtn.textContent = '总计';
    if (this.selectedYearView === '总计') {
      totalBtn.classList.add('active');
    }
    totalBtn.onclick = () => {
      this.selectedYearView = '总计';
      this.updateYearFilterButtons();
      this.renderYearTotalChart();
    };
    mainFilterEl.appendChild(totalBtn);

    // 添加"年度"按钮到主容器
    const allBtn = document.createElement('button');
    allBtn.className = 'year-tag';
    allBtn.textContent = '年度';
    if (this.selectedYearView === '年度') {
      allBtn.classList.add('active');
    }
    allBtn.onclick = () => {
      this.selectedYearView = '年度';
      this.updateYearFilterButtons();
      const { years, costs, peakData, valleyData, normalData, sharpData, noTimeData } = this._yearChartData;
      this.renderYearComboChart(years, costs, peakData, valleyData, normalData, sharpData, noTimeData);
    };
    mainFilterEl.appendChild(allBtn);

    // 添加"热力图"按钮到主容器
    const allDaysBtn = document.createElement('button');
    allDaysBtn.className = 'year-tag';
    allDaysBtn.textContent = '热力图';
    if (this.selectedYearView === '热力图') {
      allDaysBtn.classList.add('active');
    }
    allDaysBtn.onclick = () => {
      this.selectedYearView = '热力图';
      this.updateYearFilterButtons();
      this.renderYearHeatmapChart();
    };
    mainFilterEl.appendChild(allDaysBtn);

    // 添加"动态排名"按钮到主容器
    const barRacingBtn = document.createElement('button');
    barRacingBtn.className = 'year-tag';
    barRacingBtn.textContent = '动态排名';
    if (this.selectedYearView === '动态排名') {
      barRacingBtn.classList.add('active');
    }
    barRacingBtn.onclick = () => {
      this.selectedYearView = '动态排名';
      this.updateYearFilterButtons();
      this.renderBarRacingChart();
    };
    mainFilterEl.appendChild(barRacingBtn);

    // 添加各年份按钮到年份容器（倒序排列）
    [...years].reverse().forEach(year => {
      const btn = document.createElement('button');
      btn.className = 'year-tag';
      btn.textContent = year;
      if (this.selectedYearView === year) {
        btn.classList.add('active');
      }
      btn.onclick = () => {
        this.selectedYearView = year;
        this.updateYearFilterButtons();
        this.renderYearSingleChart(year);
      };
      yearsFilterEl.appendChild(btn);
    });
  }

  // 更新年份选择器按钮的激活状态
  updateYearFilterButtons() {
    // 从两个容器中查找所有按钮
    const mainButtons = this.yearFilterMainEl.querySelectorAll('.year-tag');
    const yearButtons = this.yearFilterYearsEl.querySelectorAll('.year-tag');
    
    // 合并所有按钮
    const allButtons = [...mainButtons, ...yearButtons];
    
    allButtons.forEach(btn => {
      if (btn.textContent === this.selectedYearView) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }

  // 渲染总计饼图
  renderYearTotalChart() {
    if (!this.echartsLoaded || typeof echarts === 'undefined' || !this.yearComboChartEl) {
      return;
    }

    // 显示组合图容器，隐藏其他容器
    this.yearComboChartEl.parentElement.style.display = 'block';
    this.yearHeatmapContainerEl.style.display = 'none';
    this.barRacingContainerEl.style.display = 'none';
    this.stopBarRacing();

    // 销毁现有图表实例
    if (this.yearChart) {
      this.yearChart.dispose();
      this.yearChart = null;
    }

    this.yearChart = echarts.init(this.yearComboChartEl);

    const { peakData, valleyData, normalData, sharpData, noTimeData, costs, usageUnit } = this._yearChartData;

    // 根据 utility_type 设置颜色
    const isElectricity = this.utilityType === 'ele';
    const pieColor = this.utilityType === 'gas' ? '#FF9800' : // 燃气黄色
                     this.utilityType === 'water' ? '#2196F3' : // 水蓝色
                     '#9E9E9E'; // 默认灰色

    // 计算总和
    const totalValley = valleyData.reduce((a, b) => a + b, 0);
    const totalPeak = peakData.reduce((a, b) => a + b, 0);
    const totalNormal = normalData.reduce((a, b) => a + b, 0);
    const totalSharp = sharpData.reduce((a, b) => a + b, 0);
    const totalNo = noTimeData.reduce((a, b) => a + b, 0);
    const totalCost = costs.reduce((a, b) => a + b, 0);

    // 准备饼图数据
    const pieData = [];
    
    if (isElectricity) {
      // 电力类型显示分时数据
      if (totalValley > 0) pieData.push({ name: '谷', value: totalValley, itemStyle: { color: '#4CAF50' } });
      if (totalPeak > 0) pieData.push({ name: '峰', value: totalPeak, itemStyle: { color: '#FF9800' } });
      if (totalNormal > 0) pieData.push({ name: '平', value: totalNormal, itemStyle: { color: '#2196F3' } });
      if (totalSharp > 0) pieData.push({ name: '尖', value: totalSharp, itemStyle: { color: '#F44336' } });
      if (totalNo > 0) pieData.push({ name: '无分时', value: totalNo, itemStyle: { color: '#9E9E9E' } });
    } else {
      // 非电力类型只显示用量（使用noTimeData的总和）
      const totalUsage = totalNo;
      if (totalUsage > 0) {
        pieData.push({ name: '用量', value: totalUsage, itemStyle: { color: pieColor } });
      }
    }

    const totalElectricity = pieData.reduce((sum, item) => sum + item.value, 0);

    const option = {
      tooltip: {
        trigger: 'item',
        textStyle: {
          fontSize: 12
        },
        formatter: (function(totalElectricity, usageUnit) {
          return function(params) {
            const percentage = ((params.value / totalElectricity) * 100).toFixed(1);
            return `${params.name}: ${params.value.toFixed(2)} ${usageUnit}<br/>占比: ${percentage}%`;
          };
        })(totalElectricity, usageUnit)
      },
      legend: {
        orient: 'horizontal',
        bottom: 0,
        left: 'center',
        itemWidth: 10,
        itemHeight: 14,
        itemGap: 8,
        data: pieData.map(item => ({
          name: item.name,
          icon: 'none',
          textStyle: {
            rich: {
              title: {
                color: '#fff',
                backgroundColor: item.itemStyle.color,
                padding: [2, 5],
                borderRadius: 2,
                fontSize: 11,
                fontWeight: 'bold'
              }
            }
          }
        })),
        textStyle: {
          fontSize: 11,
          fontWeight: 'bold'
        },
        formatter: function(name) {
          return '{title|' + name + '}';
        }
      },
      series: [
        {
          name: '用电量',
          type: 'pie',
          radius: ['40%', '65%'],
          center: ['48%', '48%'],
          avoidLabelOverlap: false,
          label: {
            show: true,
            position: 'outside',
            formatter: function(params) {
              const percentage = ((params.value / totalElectricity) * 100).toFixed(1);
              return `${params.name}\n${percentage}%`;
            },
            fontSize: 11
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 13,
              fontWeight: 'bold'
            }
          },
          labelLine: {
            show: true
          },
          data: pieData
        }
      ],
      graphic: [
        {
          type: 'text',
          left: '40%',
          top: '43%',
          style: {
            text: '总计\n' + totalElectricity.toFixed(0) + ' ' + usageUnit,
            textAlign: 'left',
            fill: '#666',
            fontSize: 13,
            fontWeight: 'bold'
          },
          z: 10
        },
        {
          type: 'text',
          left: '40%',
          top: '53%',
          style: {
            text: '¥' + totalCost.toFixed(2),
            textAlign: 'center',
            fill: '#804AFF',
            fontSize: 13,
            fontWeight: 'bold'
          },
          z: 10
        }
      ]
    };

    this.yearChart.setOption(option);
  }

  // 渲染单个年份饼图
  renderYearSingleChart(year) {
    if (!this.echartsLoaded || typeof echarts === 'undefined' || !this.yearComboChartEl) {
      return;
    }

    // 显示组合图容器，隐藏其他容器
    this.yearComboChartEl.parentElement.style.display = 'block';
    this.yearHeatmapContainerEl.style.display = 'none';
    this.barRacingContainerEl.style.display = 'none';
    this.stopBarRacing();

    const { years, peakData, valleyData, normalData, sharpData, noTimeData, costs, usageUnit } = this._yearChartData;
    const yearIndex = years.indexOf(year);

    if (yearIndex === -1) {
      console.error('未找到年份:', year);
      return;
    }

    // 销毁现有图表实例
    if (this.yearChart) {
      this.yearChart.dispose();
      this.yearChart = null;
    }

    this.yearChart = echarts.init(this.yearComboChartEl);

    // 获取该年份的数据
    const yearData = {
      peak: peakData[yearIndex],
      valley: valleyData[yearIndex],
      normal: normalData[yearIndex],
      sharp: sharpData[yearIndex],
      no: noTimeData[yearIndex],
      cost: costs[yearIndex]
    };

    // 根据 utility_type 设置颜色
    const isElectricity = this.utilityType === 'ele';
    const pieColor = this.utilityType === 'gas' ? '#FF9800' : // 燃气黄色
                     this.utilityType === 'water' ? '#2196F3' : // 水蓝色
                     '#9E9E9E'; // 默认灰色

    // 准备饼图数据
    const pieData = [];
    
    if (isElectricity) {
      // 电力类型显示分时数据
      if (yearData.valley > 0) pieData.push({ name: '谷', value: yearData.valley, itemStyle: { color: '#4CAF50' } });
      if (yearData.peak > 0) pieData.push({ name: '峰', value: yearData.peak, itemStyle: { color: '#FF9800' } });
      if (yearData.normal > 0) pieData.push({ name: '平', value: yearData.normal, itemStyle: { color: '#2196F3' } });
      if (yearData.sharp > 0) pieData.push({ name: '尖', value: yearData.sharp, itemStyle: { color: '#F44336' } });
      if (yearData.no > 0) pieData.push({ name: '无分时', value: yearData.no, itemStyle: { color: '#9E9E9E' } });
    } else {
      // 非电力类型只显示用量
      if (yearData.no > 0) {
        pieData.push({ name: '用量', value: yearData.no, itemStyle: { color: pieColor } });
      }
    }

    const totalElectricity = pieData.reduce((sum, item) => sum + item.value, 0);

    const option = {
      tooltip: {
        trigger: 'item',
        textStyle: {
          fontSize: 12
        },
        formatter: (function(totalElectricity, usageUnit) {
          return function(params) {
            const percentage = ((params.value / totalElectricity) * 100).toFixed(1);
            return `${params.name}: ${params.value.toFixed(2)} ${usageUnit}<br/>占比: ${percentage}%`;
          };
        })(totalElectricity, usageUnit)
      },
      legend: {
        orient: 'horizontal',
        bottom: 0,
        left: 'center',
        itemWidth: 10,
        itemHeight: 14,
        itemGap: 8,
        data: pieData.map(item => ({
          name: item.name,
          icon: 'none',
          textStyle: {
            rich: {
              title: {
                color: '#fff',
                backgroundColor: item.itemStyle.color,
                padding: [2, 5],
                borderRadius: 2,
                fontSize: 11,
                fontWeight: 'bold'
              }
            }
          }
        })),
        textStyle: {
          fontSize: 11,
          fontWeight: 'bold'
        },
        formatter: function(name) {
          return '{title|' + name + '}';
        }
      },
      series: [
        {
          name: '用电量',
          type: 'pie',
          radius: ['40%', '65%'],
          center: ['48%', '48%'],
          avoidLabelOverlap: false,
          label: {
            show: true,
            position: 'outside',
            formatter: function(params) {
              const percentage = ((params.value / totalElectricity) * 100).toFixed(1);
              return `${params.name}\n${percentage}%`;
            },
            fontSize: 11
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 13,
              fontWeight: 'bold'
            }
          },
          labelLine: {
            show: true
          },
          data: pieData
        }
      ],
      graphic: [
        {
          type: 'text',
          left: '40%',
          top: '40%',
          style: {
            text: year + '年\n' + totalElectricity.toFixed(0) + ' ' + usageUnit,
            textAlign: 'left',
            fill: '#666',
            fontSize: 13,
            fontWeight: 'bold'
          },
          z: 10
        },
        {
          type: 'text',
          left: '40%',
          top: '53%',
          style: {
            text: '¥' + yearData.cost.toFixed(0),
            textAlign: 'left',
            fill: '#804AFF',
            fontSize: 13,
            fontWeight: 'bold'
          },
          z: 10
        }
      ]
    };

    this.yearChart.setOption(option);
  }

  // 停止动态排名播放
  stopBarRacing() {
    if (this.barRacingTimer) {
      cancelAnimationFrame(this.barRacingTimer);
      this.barRacingTimer = null;
    }
    this.barRacingPaused = false;
    this.barRacingFrameIndex = 0;
    this.barRacingFrames = [];
  }

  // 渲染动态排名柱状图（入口方法，根据模式分发）
  renderBarRacingChart() {
    if (!this.echartsLoaded || typeof echarts === 'undefined') {
      console.log('[renderBarRacingChart] ECharts未加载');
      return;
    }

    if (!this.barRacingChartEl) {
      console.log('[renderBarRacingChart] 容器不存在');
      return;
    }

    // 停止之前的播放
    this.stopBarRacing();

    // 先隐藏其他容器，显示动态排名容器
    this.yearComboChartEl.parentElement.style.display = 'none';
    this.yearHeatmapContainerEl.style.display = 'none';
    this.barRacingContainerEl.style.display = 'block';

    // 设置容器高度（初始值，initBarRacingChart 会根据年份数自适应）
    this.barRacingChartEl.style.height = '200px';

    // 重置进度条（去掉 transition 避免动画）
    if (this.barRacingProgressEl) {
      this.barRacingProgressEl.style.transition = 'none';
      this.barRacingProgressEl.style.width = '0%';
    }
    if (this.barRacingMarkerEl) {
      this.barRacingMarkerEl.style.transition = 'none';
      this.barRacingMarkerEl.style.left = '0%';
    }
    requestAnimationFrame(() => {
      if (this.barRacingProgressEl) this.barRacingProgressEl.style.transition = '';
      if (this.barRacingMarkerEl) this.barRacingMarkerEl.style.transition = '';
    });

    // 更新模式按钮状态
    if (this.barRacingModeDayBtnEl) {
      this.barRacingModeDayBtnEl.classList.toggle('active', this.barRacingMode === '日');
    }
    if (this.barRacingModeMonthBtnEl) {
      this.barRacingModeMonthBtnEl.classList.toggle('active', this.barRacingMode === '月');
    }

    // 绑定模式切换按钮
    if (this.barRacingModeDayBtnEl) {
      this.barRacingModeDayBtnEl.onclick = () => {
        if (this.barRacingMode !== '日') {
          this.barRacingMode = '日';
          this.renderBarRacingChart();
        }
      };
    }
    if (this.barRacingModeMonthBtnEl) {
      this.barRacingModeMonthBtnEl.onclick = () => {
        if (this.barRacingMode !== '月') {
          this.barRacingMode = '月';
          this.renderBarRacingChart();
        }
      };
    }

    // 更新播放/暂停按钮状态
    this.barRacingPaused = false;
    this.barRacingSpeed = 1;
    if (this.barRacingPlayBtnEl) {
      this.barRacingPlayBtnEl.textContent = '播放';
      this.barRacingPlayBtnEl.classList.add('active');
    }
    if (this.barRacingSpeedBtnEl) {
      this.barRacingSpeedBtnEl.textContent = '速度 x1';
      this.barRacingSpeedBtnEl.classList.remove('active');
    }

    // 绑定播放/暂停按钮
    if (this.barRacingPlayBtnEl) {
      this.barRacingPlayBtnEl.onclick = () => {
        if (this.barRacingPaused) {
          // 如果在末尾暂停，从头开始
          if (this.barRacingFrameIndex >= this.barRacingFrames.length - 1) {
            this.barRacingFrameIndex = 0;
            this.renderBarRacingFrame();
          }
          this.barRacingPaused = false;
          this.barRacingPlayBtnEl.textContent = '暂停';
        } else {
          this.barRacingPaused = true;
          this.barRacingPlayBtnEl.textContent = '播放';
        }
      };
    }

    // 绑定速度按钮
    if (this.barRacingSpeedBtnEl) {
      this.barRacingSpeedBtnEl.onclick = () => {
        const speeds = [0.5, 1, 2, 4];
        const currentIdx = speeds.indexOf(this.barRacingSpeed);
        const nextIdx = (currentIdx + 1) % speeds.length;
        this.barRacingSpeed = speeds[nextIdx];
        this.barRacingSpeedBtnEl.textContent = '速度 x' + speeds[nextIdx];
        // 同步更新 ECharts 动画时长，避免速度切换后动画不同步
        if (this.barRacingChart) {
          this.barRacingChart.setOption({
            animationDurationUpdate: Math.max(80, Math.round(500 / this.barRacingSpeed))
          });
        }
      };
    }

    // 根据模式分发
    if (this.barRacingMode === '月') {
      this.renderBarRacingMonthChart();
    } else {
      this.renderBarRacingDayChart();
    }
  }

  // 渲染动态排名柱状图（日模式）
  renderBarRacingDayChart() {
    // 检查数据
    if (!this.standardData || !this.standardData.dayUsage || this.standardData.dayUsage.length === 0) {
      this.barRacingChartEl.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 250px; color: #999;">暂无数据</div>';
      return;
    }

    // 1. 按年聚合日数据
    const yearDailyData = {};
    const yearsSet = new Set();

    this.standardData.dayUsage.forEach(item => {
      if (item.time && item.total_usage && item.total_usage > 0) {
        const parts = item.time.split('-');
        if (parts.length >= 3) {
          const year = parts[0];
          const monthDay = parseInt(parts[1]) + '.' + parseInt(parts[2]);
          const dayOfYear = this.getDayOfYear(parts[0], parseInt(parts[1]), parseInt(parts[2]));
          yearsSet.add(year);
          if (!yearDailyData[year]) yearDailyData[year] = {};
          if (!yearDailyData[year][dayOfYear]) {
            yearDailyData[year][dayOfYear] = { usage: 0, monthDay: monthDay };
          }
          yearDailyData[year][dayOfYear].usage += item.total_usage;
        }
      }
    });

    if (yearsSet.size === 0) {
      this.barRacingChartEl.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 250px; color: #999;">暂无有效数据</div>';
      return;
    }

    const years = Array.from(yearsSet).sort();

    // 2. 计算每年每天截至该天的累计值，生成帧数据
    const maxDayOfYear = 366;
    const frames = [];

    const yearCumulative = {};
    years.forEach(year => {
      yearCumulative[year] = new Array(maxDayOfYear + 1).fill(0);
      for (let d = 1; d <= maxDayOfYear; d++) {
        const prev = yearCumulative[year][d - 1];
        const today = (yearDailyData[year] && yearDailyData[year][d]) ? yearDailyData[year][d].usage : 0;
        yearCumulative[year][d] = prev + today;
      }
    });

    for (let d = 1; d <= maxDayOfYear; d++) {
      let hasAnyData = false;
      years.forEach(year => {
        if (yearDailyData[year] && yearDailyData[year][d]) hasAnyData = true;
      });
      if (!hasAnyData) continue;

      const yearValues = years.map(year => ({
        name: year + '年',
        value: yearCumulative[year][d]
      }));

      let displayDate = '';
      for (const year of years) {
        if (yearDailyData[year] && yearDailyData[year][d]) {
          displayDate = yearDailyData[year][d].monthDay;
          break;
        }
      }

      frames.push({ day: d, date: displayDate, data: yearValues });
    }

    if (frames.length === 0) {
      this.barRacingChartEl.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 250px; color: #999;">暂无有效数据</div>';
      return;
    }

    this.barRacingFrames = frames;
    this.barRacingFrameIndex = 0;

    // 初始化ECharts并开始动画
    this.initBarRacingChart(years);
  }

  // 渲染动态排名柱状图（月模式）
  renderBarRacingMonthChart() {
    const monthData = this.standardData.monthUsage;
    if (!monthData || monthData.length === 0) {
      this.barRacingChartEl.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 250px; color: #999;">暂无月度数据</div>';
      return;
    }

    // 1. 按年聚合月数据，提取所有年份和月份
    const yearMonthData = {}; // { "2024": { "01": 100, "02": 200, ... }, ... }
    const yearsSet = new Set();
    const allMonths = new Set();

    monthData.forEach(item => {
      if (item.time && item.total_usage && item.total_usage > 0) {
        const parts = item.time.split('-');
        if (parts.length >= 2) {
          const year = parts[0];
          const month = parts[1];
          yearsSet.add(year);
          allMonths.add(month);
          if (!yearMonthData[year]) yearMonthData[year] = {};
          if (!yearMonthData[year][month]) yearMonthData[year][month] = 0;
          yearMonthData[year][month] += item.total_usage;
        }
      }
    });

    if (yearsSet.size === 0) {
      this.barRacingChartEl.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 250px; color: #999;">暂无有效月度数据</div>';
      return;
    }

    const years = Array.from(yearsSet).sort();
    const months = Array.from(allMonths).sort();

    // 2. 计算每年截至该月的累计值，生成帧数据
    const frames = [];

    // 预计算每年截至每月的累计值
    const yearMonthCumulative = {};
    years.forEach(year => {
      yearMonthCumulative[year] = {};
      let cumulative = 0;
      for (const month of months) {
        const usage = (yearMonthData[year] && yearMonthData[year][month]) ? yearMonthData[year][month] : 0;
        cumulative += usage;
        yearMonthCumulative[year][month] = cumulative;
      }
    });

    for (const month of months) {
      let hasAnyData = false;
      years.forEach(year => {
        if (yearMonthData[year] && yearMonthData[year][month]) hasAnyData = true;
      });
      if (!hasAnyData) continue;

      const yearValues = years.map(year => ({
        name: year + '年',
        value: yearMonthCumulative[year][month]
      }));

      frames.push({ month: month, date: String(parseInt(month)), data: yearValues });
    }

    if (frames.length === 0) {
      this.barRacingChartEl.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 250px; color: #999;">暂无有效月度数据</div>';
      return;
    }

    this.barRacingFrames = frames;
    this.barRacingFrameIndex = 0;

    // 初始化ECharts并开始动画
    this.initBarRacingChart(years);
  }

  // 初始化ECharts图表并开始动画（日/月模式共用）
  initBarRacingChart(years) {
    requestAnimationFrame(() => {
      if (this.barRacingChartEl.offsetWidth === 0 || this.barRacingChartEl.offsetHeight === 0) {
        setTimeout(() => this.renderBarRacingChart(), 100);
        return;
      }

      // 根据年份数量自适应容器高度和柱宽
      const yearCount = years.length;
      // 获取图表区域之前已占用的高度，计算剩余可用空间
      const usedHeight = this.barRacingChartEl.offsetTop || 0;
      const maxHeight = Math.max(150, 350 - usedHeight);
      const barHeight = Math.min(50, Math.max(24, Math.floor(maxHeight / yearCount)));
      const containerHeight = barHeight * yearCount + 40;
      this.barRacingChartEl.style.height = Math.min(maxHeight, Math.max(150, containerHeight)) + 'px';
      const barWidth = Math.min(50, Math.max(30, Math.round(barHeight * 0.85))) + '%';

      if (this.barRacingChart) {
        this.barRacingChart.dispose();
        this.barRacingChart = null;
      }

      this.barRacingChart = echarts.init(this.barRacingChartEl);

      // 使用与卡片一致的 Material Design 风格颜色（阶梯色 + 分时色）
      const barColors = [
        { c: ['#55C593', '#6FD9A8'], border: '#3DA87A' },   // 阶梯绿
        { c: ['#F8C337', '#FAD06B'], border: '#D9A81E' },   // 阶梯黄
        { c: ['#F79335', '#FAAB64'], border: '#D47A1C' },   // 阶梯橙
        { c: ['#2196F3', '#64B5F6'], border: '#1976D2' },   // 平段蓝
        { c: ['#FF9800', '#FFB74D'], border: '#F57C00' },   // 峰段橙
        { c: ['#4CAF50', '#81C784'], border: '#388E3C' }    // 谷段绿
      ];
      this.barRacingColors = barColors.map(b => b.c[0]);
      this.barRacingColorStyles = barColors;
      this.barRacingYears = years;
      const unit = this.standardData.unit || 'kWh';

      this.barRacingChart.setOption({
        grid: {
          left: '13%',
          right: '12%',
          top: '5%',
          bottom: '8%'
        },
        xAxis: {
          max: 'dataMax',
          position: 'bottom',
          axisLabel: {
            formatter: (val) => val >= 1000 ? (val / 1000).toFixed(1) + 'k' : Math.round(val),
            color: 'var(--text-color, #666)',
            fontSize: 10
          },
          splitLine: {
            lineStyle: { color: 'rgba(200,200,200,0.15)', type: 'dashed' }
          },
          axisLine: {
            lineStyle: { color: 'rgba(200,200,200,0.3)' }
          },
          axisTick: {
            lineStyle: { color: 'rgba(200,200,200,0.3)' }
          }
        },
        yAxis: {
          type: 'category',
          data: years.map(y => y + '年'),
          inverse: false,
          animationDuration: 300,
          animationDurationUpdate: 300,
          axisLabel: {
            fontSize: Math.min(12, Math.max(9, Math.floor(14 - yearCount * 0.4))),
            color: 'var(--text-color, #666)',
            fontWeight: 500
          },
          axisLine: {
            lineStyle: { color: 'rgba(200,200,200,0.2)' }
          },
          axisTick: {
            show: false
          }
        },
        series: [{
          realtimeSort: true,
          type: 'bar',
          data: years.map((y, i) => ({
            value: 0,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: barColors[i % barColors.length].c[0] },
                { offset: 1, color: barColors[i % barColors.length].c[1] }
              ]),
              borderRadius: [0, 3, 3, 0]
            }
          })),
          barWidth: barWidth,
          barGap: yearCount > 6 ? '10%' : '30%',
          barCategoryGap: yearCount > 6 ? '15%' : '20%',
          label: {
            show: true,
            position: 'right',
            valueAnimation: true,
            formatter: (params) => Math.round(params.value) + ' ' + unit,
            fontSize: 11,
            fontWeight: 600,
            color: 'var(--text-color, #333)'
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 8,
              shadowColor: 'rgba(0,0,0,0.15)'
            }
          }
        }],
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          backgroundColor: 'var(--card-bg, #fff)',
          borderColor: 'var(--button-primary-transparent, rgba(0,0,0,0.1))',
          textStyle: { color: 'var(--text-color, #333)', fontSize: 12 },
          formatter: (params) => {
            if (!params || params.length === 0) return '';
            const p = params[0];
            return `<span style="font-weight:700;">${p.name}</span><br/>累计用电：<span style="font-weight:600;">${Math.round(p.value)} ${unit}</span>`;
          }
        },
        animationDuration: 0,
        animationDurationUpdate: Math.max(80, Math.round(500 / this.barRacingSpeed)),
        animationEasing: 'linear',
        animationEasingUpdate: 'linear'
      }, true);

      // 渲染第一帧
      this.renderBarRacingFrame();

      // 开始动画
      this.startBarRacingAnimation();
    });
  }

  // 获取某天在一年中的第几天
  getDayOfYear(year, month, day) {
    const date = new Date(parseInt(year), month - 1, day);
    const start = new Date(parseInt(year), 0, 0);
    const diff = date - start;
    return Math.floor(diff / (1000 * 60 * 60 * 24));
  }

  // 启动动态排名动画（使用 requestAnimationFrame 实现流畅动画）
  startBarRacingAnimation() {
    if (this.barRacingTimer) {
      cancelAnimationFrame(this.barRacingTimer);
    }
    let lastTime = 0;

    const tick = (timestamp) => {
      // 动态计算帧间隔，支持运行时变速
      const frameInterval = Math.max(80, Math.round(500 / this.barRacingSpeed));
      if (this.barRacingPaused) {
        lastTime = 0;
        this.barRacingTimer = requestAnimationFrame(tick);
        return;
      }
      if (!lastTime) lastTime = timestamp;
      if (timestamp - lastTime >= frameInterval) {
        lastTime = timestamp;
        this.barRacingFrameIndex++;
        if (this.barRacingFrameIndex >= this.barRacingFrames.length) {
          this.barRacingFrameIndex = this.barRacingFrames.length - 1;
          this.barRacingPaused = true;
          if (this.barRacingPlayBtnEl) {
            this.barRacingPlayBtnEl.textContent = '播放';
          }
          return;
        }
        this.renderBarRacingFrame();
      }
      this.barRacingTimer = requestAnimationFrame(tick);
    };

    this.barRacingTimer = requestAnimationFrame(tick);
  }

  // 渲染单帧动态排名（只更新 series data，让 realtimeSort 自动排序）
  renderBarRacingFrame() {
    if (!this.barRacingChart || this.barRacingFrames.length === 0) return;

    const frame = this.barRacingFrames[this.barRacingFrameIndex];

    // 更新气泡中的日期文本
    if (this.barRacingDateEl) {
      this.barRacingDateEl.textContent = frame.date;
    }

    // 更新独立时间轴进度条
    // transition 时长与帧切换间隔一致，确保平滑移动且不滞后
    const progress = this.calcBarRacingProgress(frame);
    const pct = (progress * 100).toFixed(1) + '%';
    const dur = Math.max(80, Math.round(500 / this.barRacingSpeed));
    if (this.barRacingProgressEl) {
      this.barRacingProgressEl.style.transition = `width ${dur}ms linear`;
      this.barRacingProgressEl.style.width = pct;
    }
    if (this.barRacingMarkerEl) {
      this.barRacingMarkerEl.style.transition = `left ${dur}ms linear`;
      this.barRacingMarkerEl.style.left = pct;
    }

    // 更新柱状图数据（保持渐变样式，通过年份名映射颜色索引）
    const colorStyles = this.barRacingColorStyles;
    const years = this.barRacingYears;
    this.barRacingChart.setOption({
      series: [{ data: frame.data.map(item => {
        const yearIdx = years.indexOf(item.name.replace('年', ''));
        const i = yearIdx >= 0 ? yearIdx : 0;
        const cs = colorStyles[i % colorStyles.length];
        return {
          value: item.value,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: cs.c[0] },
              { offset: 1, color: cs.c[1] }
            ]),
            borderRadius: [0, 3, 3, 0]
          }
        };
      })}]
    });
  }

  // 计算当前帧的时间进度 (0~1)
  calcBarRacingProgress(frame) {
    let monthNum = 1;
    let dayOfMonth = 1;
    let daysInMonth = 30;

    if (this.barRacingMode === '月') {
      monthNum = parseInt(frame.date) || 1;
    } else {
      const parts = frame.date.split('.');
      monthNum = parseInt(parts[0]) || 1;
      dayOfMonth = parseInt(parts[1]) || 1;
      daysInMonth = new Date(2024, monthNum, 0).getDate();
    }

    let progress;
    if (this.barRacingMode === '月') {
      progress = (monthNum - 1) / 11;
    } else {
      progress = ((monthNum - 1) + (dayOfMonth - 1) / daysInMonth) / 11;
    }
    return Math.min(progress, 1);
  }

  // 渲染日用电热力图
  renderYearHeatmapChart() {
    
    if (!this.echartsLoaded || typeof echarts === 'undefined') {
      console.log('[renderYearHeatmapChart] ECharts未加载');
      return;
    }
    
    if (!this.yearHeatmapChartEl) {
      console.log('[renderYearHeatmapChart] 热力图容器不存在');
      return;
    }

    // 先显示热力图容器，隐藏其他容器
    this.yearComboChartEl.parentElement.style.display = 'none';
    this.yearHeatmapContainerEl.style.display = 'block';
    this.barRacingContainerEl.style.display = 'none';
    this.stopBarRacing();

    // 设置热力图容器高度
    this.yearHeatmapChartEl.style.height = '320px';

    // 强制触发浏览器重排，确保容器有正确的尺寸
    const forceReflow = this.yearHeatmapChartEl.offsetWidth;

    // 使用 requestAnimationFrame 等待浏览器完成布局
    requestAnimationFrame(() => {
      // 检查容器尺寸
      if (this.yearHeatmapChartEl.offsetWidth === 0 || this.yearHeatmapChartEl.offsetHeight === 0) {
        setTimeout(() => {
          this.renderYearHeatmapChart();
        }, 100);
        return;
      }

      // 销毁现有图表实例
      if (this.yearHeatmapChart) {
        this.yearHeatmapChart.dispose();
        this.yearHeatmapChart = null;
      }

      // 将daylistData按年份分组
      const yearDataMap = new Map();
      if (this.standardData && this.standardData.dayUsage && this.standardData.dayUsage.length > 0) {
        this.standardData.dayUsage.forEach(item => {
          if (item.time && item.total_usage && item.total_usage > 0) {
            const year = item.time.split('-')[0];
            if (!yearDataMap.has(year)) {
              yearDataMap.set(year, []);
            }
            // 只保留日期和用电量数据，去掉电费
            yearDataMap.get(year).push([item.time, item.total_usage]);
          }
        });
      } else {
        console.log('[renderYearHeatmapChart] dayUsage为空或未定义');
      }

      // 如果没有数据，显示提示信息
      if (yearDataMap.size === 0) {
        console.log('[renderYearHeatmapChart] 没有有效数据');
        this.yearHeatmapChartEl.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 250px; color: #999;">暂无数据</div>';
        return;
      }

      this.yearHeatmapChart = echarts.init(this.yearHeatmapChartEl);

      // 获取所有年份数据并排序
      const years = Array.from(yearDataMap.keys()).sort();

      // 计算所有数据的范围
      const allValues = [];
      yearDataMap.forEach(dataArray => {
        dataArray.forEach(item => allValues.push(item[1]));
      });
      const maxUsage = Math.max(...allValues);
      const minUsage = Math.min(...allValues);

      // 构建calendar和series配置
      const calendarList = [];
      const seriesList = [];

      // 获取今天的日期
      const today = new Date();
      const todayStr = today.getFullYear() + '-' + 
                      String(today.getMonth() + 1).padStart(2, '0') + '-' + 
                      String(today.getDate()).padStart(2, '0');

      // 获取主题颜色
      const rootStyle = getComputedStyle(document.documentElement);
      const cardValueColor = rootStyle.getPropertyValue('--card-value-color') || '#2b2b2b';

      years.forEach((year, index) => {
        const yearData = yearDataMap.get(year);
        
        // 在第一个年份（最小年份）的图表上方显示月份标签
        const showMonthLabel = (year === years[0]);
        
        calendarList.push({
          top: (index * 85 / years.length) + '%',
          height: (85 / years.length) + '%',
          left: '18px',
          right: '15px',
          range: String(year),
          cellSize: ['auto', 20],
          itemStyle: {
            borderWidth: 0.5,
            borderColor: 'rgba(208, 208, 208, 0.3)',
            // 设置空白单元格颜色为透明
            color: 'transparent'
          },
          splitLine: {
            show: true,
            lineStyle: {
              color: cardValueColor.trim(),
              width: 0.8
            }
          },
          yearLabel: { 
            show: true,
            position: 'left',
            margin: 5,
            color: '#666',
            fontSize: 13,
            fontWeight: 'bold'
          },
          monthLabel: {
            show: false
          },
          dayLabel: {
            firstDay: 1,
            fontSize: 10,
            color: '#999',
            show: true,
            position: 'right',
            margin: 5,
            nameMap: 'cn'
          }
        });

        // 主数据系列
        seriesList.push({
          type: 'heatmap',
          coordinateSystem: 'calendar',
          calendarIndex: index,
          name: `${year}年`,
          data: yearData,
          // 明确指定使用第二个数值（用电量）进行颜色映射
          valueIndex: 1,
          emphasis: {
            itemStyle: {
              borderColor: '#333',
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.5)',
              borderWidth: 1              
            }
          },
          progressive: 1000,
          animation: true
        });

        // 检查今天是否在当前年份
        if (todayStr.startsWith(year)) {
          // 创建一个专门用于高亮今天的系列
          // 如果今天有数据，则使用数据值，否则使用占位符值
          const todayDataItem = yearData.find(item => item[0] === todayStr);
          const todayValue = todayDataItem ? todayDataItem[1] : 0;
          
          seriesList.push({
            type: 'heatmap',
            coordinateSystem: 'calendar',
            calendarIndex: index,
            name: `${year}年-今日高亮`,
            data: [[todayStr, todayValue]],
            valueIndex: 1,
            itemStyle: {
              borderColor: '#ff0000',
              borderWidth: 3,
              borderType: 'solid',
              color: 'transparent' // 确保不显示填充颜色
            },
            emphasis: {
              itemStyle: {
                borderColor: '#ff0000',
                borderWidth: 4,
                shadowBlur: 15,
                shadowColor: 'rgba(255, 0, 0, 0.5)'
              }
            },
            // 确保这个系列不会干扰visualMap的颜色映射
            visualMap: false,
            z: 100 // 设置较高的z值确保边框在最上层
          });
        }
      });

      const option = {
        title: {
          text: ' ',
          top: 0,
          left: 'center',
          textStyle: {
            fontSize: 12,
            color: '#666'
          }
        },
        tooltip: {
          position: 'top',
          formatter: (function(usageUnit) {
            return function(params) {
              const dateStr = params.value[0];
              const usage = params.value[1];
              // 如果 usage 为 0，显示"无数据"
              if (usage === 0) {
                return `${dateStr}<br/>无数据`;
              }
              return `${dateStr}<br/>用量: ${usage} ${usageUnit}`;
            };
          })(this.standardData.unit || '')
        },
        grid: {
          top: 10,
          bottom: 50, // 为visualMap预留底部空间
          left: '10%',
          right: '10%'
        },
        visualMap: {
          min: minUsage,
          max: maxUsage,
          text: ['多', '少'],
          show: true,
          type: 'continuous',
          orient: 'horizontal',
          left: 'center',
          bottom: 0, 
          textStyle: {
            fontSize: 10,
            color: '#666'
          },
          formatter: function(value) {
            return Math.round(value);
          },
          calculable: true,
          realtime: true,
          itemHeight: 180,
          itemWidth: 18,
          inRange: {
            color: ["#313695", "#4575b4", "#74add1", "#abd9e9", "#e0f3f8", "#ffffbf", "#fee090", "#fdae61", "#f46d43", "#d73027", "#a50026"]
          },
          // 设置空白单元格（没有数据的和未来的）颜色为透明
          outOfRange: {
            color: 'transparent'
          },
          // 明确指定关联的series索引（只关联主数据系列，不关联今日高亮系列）
          seriesIndex: Array.from({length: years.length}, (_, i) => i)
        },
        calendar: calendarList,
        series: seriesList,
        dataZoom: [
          {
            type: 'slider',
            show: true,
            start: 0,
            end: 100,
            height: 20,
            bottom: 5,
            right: 20,
            left: 'auto',
            width: 150,
            handleSize: '100%',
            handleStyle: {
              color: '#fff',
              shadowBlur: 3,
              shadowColor: 'rgba(0, 0, 0, 0.6)',
              shadowOffsetX: 2,
              shadowOffsetY: 2
            },
            textStyle: {
              fontSize: 10
            },
            borderColor: '#ccc',
            fillerColor: 'rgba(64, 158, 255, 0.2)',
            handleColor: '#409eff'
          }
        ]
      };

      this.yearHeatmapChart.setOption(option);
    });
  }

  // 渲染年度电费与用电量组合图
  async renderYearComboChart(years, costs, peakData, valleyData, normalData, sharpData, noTimeData, usageUnit = '') {
    if (!this.echartsLoaded || typeof echarts === 'undefined') {
      return;
    }

    // 检查容器是否存在
    if (!this.yearComboChartEl) {
      return;
    }

    // 显示组合图容器，隐藏其他容器
    this.yearComboChartEl.parentElement.style.display = 'block';
    this.yearHeatmapContainerEl.style.display = 'none';
    this.barRacingContainerEl.style.display = 'none';
    this.stopBarRacing();

    // 强制触发浏览器重排，确保容器有正确的尺寸
    const forceReflow = this.yearComboChartEl.offsetWidth;

    // 检查容器尺寸是否有效
    if (this.yearComboChartEl.offsetWidth === 0 || this.yearComboChartEl.offsetHeight === 0) {
      setTimeout(() => {
        // 使用缓存数据重试
        if (this._yearChartData) {
          const { years, costs, peakData, valleyData, normalData, sharpData, noTimeData, usageUnit } = this._yearChartData;
          this.renderYearComboChart(years, costs, peakData, valleyData, normalData, sharpData, noTimeData, usageUnit);
        } else {
          // 如果没有缓存数据，调用 renderYearView 重新获取数据
          this.renderYearView();
        }
      }, 100);
      return;
    }

    // 销毁现有图表实例
    if (this.yearChart) {
      this.yearChart.dispose();
      this.yearChart = null;
    }

    this.yearChart = echarts.init(this.yearComboChartEl);

    // 获取缴费数据并按年聚合
    let paymentData = {};
    if (this.jiaofeiEntityId) {
      try {
        const payHistory = await this.fetchPayHistory();
        if (payHistory && payHistory.length > 0) {
          // 按年聚合缴费数据
          payHistory.forEach(item => {
            if (item.time && item.cost) {
              const year = new Date(item.time).getFullYear().toString();
              if (!paymentData[year]) {
                paymentData[year] = 0;
              }
              paymentData[year] += item.cost;
            }
          });
        }
      } catch (error) {
        console.log('获取缴费数据失败:', error);
      }
    }

    // 根据缴费数据确定完整的年份范围
    let allYears = [...years];
    if (Object.keys(paymentData).length > 0) {
      const paymentYears = Object.keys(paymentData).sort();
      // 合并年份范围
      allYears = [...new Set([...years, ...paymentYears])].sort();
    }

    // 重新调整数据以匹配完整的年份范围
    const adjustedYears = allYears;
    const adjustedCosts = adjustedYears.map(year => {
      const index = years.indexOf(year);
      return index !== -1 ? costs[index] : 0;
    });
    const adjustedPeakData = adjustedYears.map(year => {
      const index = years.indexOf(year);
      return index !== -1 ? peakData[index] : 0;
    });
    const adjustedValleyData = adjustedYears.map(year => {
      const index = years.indexOf(year);
      return index !== -1 ? valleyData[index] : 0;
    });
    const adjustedNormalData = adjustedYears.map(year => {
      const index = years.indexOf(year);
      return index !== -1 ? normalData[index] : 0;
    });
    const adjustedSharpData = adjustedYears.map(year => {
      const index = years.indexOf(year);
      return index !== -1 ? sharpData[index] : 0;
    });
    const adjustedNoTimeData = adjustedYears.map(year => {
      const index = years.indexOf(year);
      return index !== -1 ? noTimeData[index] : 0;
    });
    const adjustedPaymentData = adjustedYears.map(year => paymentData[year] || 0);

    // 根据 utility_type 设置系列和图例
    const isElectricity = this.utilityType === 'ele';
    const barColor = this.utilityType === 'gas' ? '#FF9800' : // 燃气黄色
                     this.utilityType === 'water' ? '#2196F3' : // 水蓝色
                     '#9E9E9E'; // 默认灰色

    const series = [];
    const legendData = [];

    if (isElectricity) {
      // 电力类型显示分时系列
      series.push(
        {
          name: '峰',
          type: 'bar',
          stack: 'usage',
          data: adjustedPeakData,
          yAxisIndex: 0,
          itemStyle: { color: '#FF9800' }
        },
        {
          name: '谷',
          type: 'bar',
          stack: 'usage',
          data: adjustedValleyData,
          yAxisIndex: 0,
          itemStyle: { color: '#4CAF50' }
        },
        {
          name: '平',
          type: 'bar',
          stack: 'usage',
          data: adjustedNormalData,
          yAxisIndex: 0,
          itemStyle: { color: '#2196F3' }
        },
        {
          name: '尖',
          type: 'bar',
          stack: 'usage',
          data: adjustedSharpData,
          yAxisIndex: 0,
          itemStyle: { color: '#F44336' }
        },
        {
          name: '无分时',
          type: 'bar',
          stack: 'usage',
          data: adjustedNoTimeData,
          yAxisIndex: 0,
          itemStyle: { color: '#9E9E9E' }
        }
      );

      legendData.push(
        { name: '峰', icon: 'none' },
        { name: '谷', icon: 'none' },
        { name: '平', icon: 'none' },
        { name: '尖', icon: 'none' },
        { name: '无分时', icon: 'none' }
      );
    } else {
      // 非电力类型只显示用量系列
      series.push({
        name: '用量',
        type: 'bar',
        stack: 'usage',
        data: adjustedNoTimeData,
        yAxisIndex: 0,
        itemStyle: { color: barColor }
      });

      legendData.push({ name: '用量', icon: 'none' });
    }

    // 所有类型都显示费用系列
    series.push({
      name: '消费',
      type: 'line',
      data: adjustedCosts,
      yAxisIndex: 1,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      showSymbol: true,
      lineStyle: {
        width: 3,
        color: '#804AFF'
      },
      itemStyle: {
        color: '#804AFF',
        borderColor: '#fff',
        borderWidth: 1.5,
        shadowBlur: 10,
        shadowColor: 'rgba(128, 74, 255, 0.5)'
      },
      label: {
        show: true,
        position: 'top',
        fontSize: 10,
        color: '#804AFF',
        fontWeight: 600,
        formatter: function(params) {
          if (params.value === 0) {
            return '';
          }
          return params.value.toFixed(0);
        },
        offset: [0, -8]
      },
      emphasis: {
        focus: 'series',
        scale: true,
        scaleSize: 1.3,
        itemStyle: {
          borderColor: '#804AFF',
          borderWidth: 2
        }
      }
    });

    legendData.push({ name: '消费', icon: 'none' });

    // 如果有缴费数据，添加阶梯面积图系列（放在柱状图下层）
    if (Object.keys(paymentData).length > 0) {
      // 将缴费系列插入到series数组的开头，这样它会先渲染（在底层）
      series.unshift({
        name: '缴费',
        type: 'line',
        step: 'start',
        data: adjustedPaymentData,
        yAxisIndex: 1,
        z: 0, // 设置zIndex确保在柱状图下层
        symbol: 'none',
        showSymbol: false,
        lineStyle: {
          width: 0,
          opacity: 0
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(0, 200, 83, 0.3)' },
              { offset: 1, color: 'rgba(0, 200, 83, 0.05)' }
            ]
          }
        },
        label: {
          show: false
        },
        emphasis: {
          disabled: true
        }
      });
      // 同样将缴费图例插入到开头
      legendData.unshift({ name: '缴费', icon: 'none', itemStyle: { color: '#00C853' } });
    }

    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          label: {
            backgroundColor: '#6a7985'
          }
        },
        textStyle: {
          fontSize: 12
        },
        formatter: function(params) {
          let result = `${params[0].axisValue}年<br/><br/>`;

          // 先显示费用信息
          const costParam = params.find(param => param.seriesName === '消费');
          if (costParam) {
            result += `<span style="color:#804AFF">●</span> 消费: <strong>¥${costParam.value.toFixed(2)}</strong><br/>`;
            result += '<hr style="margin:3px 0;border:none;border-top:1px solid #ddd;">';
          }

          // 显示缴费信息
          const paymentParam = params.find(param => param.seriesName === '缴费');
          if (paymentParam && paymentParam.value > 0) {
            result += `<span style="color:#00C853">●</span> 缴费: <strong>¥${paymentParam.value.toFixed(2)}</strong><br/>`;
            result += '<hr style="margin:3px 0;border:none;border-top:1px solid #ddd;">';
          }

          // 显示用量信息
          let hasUsage = false;
          let totalUsage = 0;
          params.forEach(param => {
            if (param.seriesName === '用量' && param.value > 0) {
              hasUsage = true;
              result += `<span style="display:inline-block;width:10px;height:10px;background:${param.color};margin-right:5px;"></span><strong>${param.seriesName}: ${param.value.toFixed(2)} ${usageUnit}</strong><br/>`;
              totalUsage += param.value;
            } else if (param.seriesName !== '消费' && param.seriesName !== '用量' && param.seriesName !== '缴费' && param.value > 0) {
              hasUsage = true;
              result += `<span style="display:inline-block;width:10px;height:10px;background:${param.color};margin-right:5px;"></span>${param.seriesName}: ${param.value.toFixed(2)} ${usageUnit}<br/>`;
              totalUsage += param.value;
            }
          });

          if (hasUsage) {
            result += `<hr style="margin:3px 0;border:none;border-top:1px solid #ddd;">`;
            result += `<strong>总用量: ${totalUsage.toFixed(2)} ${usageUnit}</strong>`;
          }

          return result;
        }
      },
      legend: {
        data: legendData,
        bottom: 0,
        itemWidth: 10,
        itemHeight: 20,
        itemGap: 2,
        textStyle: {
          fontSize: 10,
          fontWeight: 'bold'
        },
        formatter: function(name) {
          return '{title|' + name + '}';
        },
        textStyle: {
          rich: {
            title: {
              color: '#fff',
              fontSize: 11,
              fontWeight: 'bold',
              padding: [3, 3],
              borderRadius: 2,
              backgroundColor: function(params) {
                if (params.name === '用量') {
                  return barColor;
                } else if (params.name === '消费') {
                  return '#804AFF';
                } else if (params.name === '缴费') {
                  return '#00C853';
                }
                return '#9E9E9E';
              }
            }
          }
        }
      },
      grid: {
        left: '0%',
        right: '0%',
        bottom: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: adjustedYears,
        axisLine: {
          lineStyle: { color: '#666' }
        },
        axisLabel: {
          color: '#666',
          interval: 0,
          rotate: 45,
          fontSize: 10
        }
      },
      yAxis: [
        {
          type: 'value',
          name: usageUnit,
          nameLocation: 'end',
          position: 'left',
          axisLine: {
            lineStyle: { color: '#666' }
          },
          axisLabel: {
            color: '#666',
            formatter: function(value) {
              if (value > 100) {
                return (value / 1000).toFixed(1) + 'k';
              }
              return value;
            }
          },
          splitLine: {
            lineStyle: { color: 'rgba(0,0,0,0.1)' }
          }
        },
        {
          type: 'value',
          name: '元',
          position: 'right',
          axisLine: {
            lineStyle: { color: '#804AFF' }
          },
          axisLabel: {
            color: '#804AFF',
            formatter: function(value) {
              if (value > 100) {
                return (value / 1000).toFixed(1) + 'k';
              }
              return value;
            }
          },
          splitLine: {
            show: false
          }
        }
      ],
      series: series
    };

    this.yearChart.setOption(option);
  }

  // 渲染月视图
  renderMonthView() {
    // 从统一数据接口获取数据
    if (!this.standardData || !this.standardData.monthUsage || this.standardData.monthUsage.length === 0) {
      return;
    }

    // 销毁现有图表
    this.destroyMonthCharts();

    // 从统一格式提取所有可用的年份
    const availableYears = [...new Set(
      this.standardData.monthUsage.map(item => parseInt(item.time.split('-')[0]))
    )].sort((a, b) => b - a); // 降序排列

    // 如果没有选中的年份，默认选择第一个（最新的年份）
    if (!this.selectedYear || !availableYears.includes(this.selectedYear)) {
      this.selectedYear = availableYears[0];
    }

    // 渲染年份筛选标签
    this.renderYearFilter(availableYears, this.selectedYear);

    // 从统一格式过滤出当前选中年份的数据
    const yearData = this.standardData.monthUsage.filter(item => {
      const itemYear = parseInt(item.time.split('-')[0]);
      return itemYear === this.selectedYear;
    });

    // 如果没有数据，直接返回
    if (yearData.length === 0) {
      return;
    }

    // 从统一格式准备图表数据
    const months = yearData.map(item => {
      const date = new Date(item.time + '-01');
      return `${(date.getMonth() + 1).toString().padStart(2, '0')}月`;
    });
    const costs = yearData.map(item => item.total_amount);
    const peakData = yearData.map(item => item.usage_ele_peak || 0);
    const valleyData = yearData.map(item => item.usage_ele_valley || 0);
    const normalData = yearData.map(item => item.usage_ele_norm || 0);
    const sharpData = yearData.map(item => item.usage_ele_tip || 0);
    const noTimeData = yearData.map(item => item.usage_ele_no || 0);
    
    // 获取单位符号（从统一数据格式中获取，不设置默认值）
    const usageUnit = yearData.length > 0 ? yearData[0].unit : '';

    // 保存数据到缓存，用于重试
    this._monthChartData = { months, costs, peakData, valleyData, normalData, sharpData, noTimeData, usageUnit };

    // 渲染组合图表 - 使用双重 requestAnimationFrame 确保容器布局完成
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        this.renderMonthComboChart(months, costs, peakData, valleyData, normalData, sharpData, noTimeData, usageUnit);
      });
    });
  }

  // 渲染年份筛选标签
  renderYearFilter(years, selectedYear) {
    this.monthYearFilterEl.innerHTML = '';
    
    years.forEach(year => {
      const yearTag = document.createElement('div');
      yearTag.className = 'year-tag';
      yearTag.textContent = `${year}`;
      
      if (year === selectedYear) {
        yearTag.classList.add('active');
      }
      
      yearTag.addEventListener('click', () => {
        this.selectedYear = year;
        this.renderMonthView();
      });
      
      this.monthYearFilterEl.appendChild(yearTag);
    });
  }

  // 渲染月度电费与用电量组合图
  renderMonthComboChart(months, costs, peakData, valleyData, normalData, sharpData, noTimeData, usageUnit = '') {
    if (!this.echartsLoaded || typeof echarts === 'undefined') {
      return;
    }

    // 检查容器是否存在
    if (!this.monthComboChartEl) {
      return;
    }

    // 强制触发浏览器重排，确保容器有正确的尺寸
    const forceReflow = this.monthComboChartEl.offsetWidth;

    // 检查容器尺寸是否有效
    if (this.monthComboChartEl.offsetWidth === 0 || this.monthComboChartEl.offsetHeight === 0) {
      setTimeout(() => {
        // 使用缓存数据重试
        if (this._monthChartData) {
          const { months, costs, peakData, valleyData, normalData, sharpData, noTimeData, usageUnit } = this._monthChartData;
          this.renderMonthComboChart(months, costs, peakData, valleyData, normalData, sharpData, noTimeData, usageUnit);
        } else {
          // 如果没有缓存数据，调用 renderMonthView 重新获取数据
          this.renderMonthView();
        }
      }, 100);
      return;
    }

    // 销毁现有图表实例
    if (this.monthChart) {
      this.monthChart.dispose();
      this.monthChart = null;
    }

    this.monthChart = echarts.init(this.monthComboChartEl);

    // 根据 utility_type 设置系列和图例
    const isElectricity = this.utilityType === 'ele';
    const barColor = this.utilityType === 'gas' ? '#FF9800' : // 燃气黄色
                     this.utilityType === 'water' ? '#2196F3' : // 水蓝色
                     '#9E9E9E'; // 默认灰色
    
    const series = [];
    const legendData = [];
    
    if (isElectricity) {
      // 电力类型显示分时系列
      series.push(
        {
          name: '峰',
          type: 'bar',
          stack: 'usage',
          data: peakData,
          yAxisIndex: 0,
          itemStyle: { color: '#FF9800' }
        },
        {
          name: '谷',
          type: 'bar',
          stack: 'usage',
          data: valleyData,
          yAxisIndex: 0,
          itemStyle: { color: '#4CAF50' }
        },
        {
          name: '平',
          type: 'bar',
          stack: 'usage',
          data: normalData,
          yAxisIndex: 0,
          itemStyle: { color: '#2196F3' }
        },
        {
          name: '尖',
          type: 'bar',
          stack: 'usage',
          data: sharpData,
          yAxisIndex: 0,
          itemStyle: { color: '#F44336' }
        },
        {
          name: '无分时',
          type: 'bar',
          stack: 'usage',
          data: noTimeData,
          yAxisIndex: 0,
          itemStyle: { color: '#9E9E9E' }
        }
      );
      
      legendData.push(
        { name: '峰', icon: 'none' },
        { name: '谷', icon: 'none' },
        { name: '平', icon: 'none' },
        { name: '尖', icon: 'none' },
        { name: '无分时', icon: 'none' }
      );
    } else {
      // 非电力类型只显示用量系列
      series.push({
        name: '用量',
        type: 'bar',
        stack: 'usage',
        data: noTimeData,
        yAxisIndex: 0,
        itemStyle: { color: barColor }
      });
      
      legendData.push({ name: '用量', icon: 'none' });
    }
    
    // 所有类型都显示费用系列
    series.push({
      name: '消费',
      type: 'line',
      data: costs,
      yAxisIndex: 1,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      showSymbol: true,
      lineStyle: {
        width: 3,
        color: '#804AFF'
      },
      itemStyle: {
        color: '#804AFF',
        borderColor: '#fff',
        borderWidth: 1.5,
        shadowBlur: 10,
        shadowColor: 'rgba(128, 74, 255, 0.5)'
      },
      label: {
        show: true,
        position: 'top',
        fontSize: 10,
        color: '#804AFF',
        fontWeight: 600,
        formatter: function(params) {
          if (params.value === 0) {
            return '';
          }
          return params.value.toFixed(0);
        },
        offset: [0, -8]
      },
      emphasis: {
        focus: 'series',
        scale: true,
        scaleSize: 1.3,
        itemStyle: {
          borderColor: '#804AFF',
          borderWidth: 2
        }
      }
    });
    
    legendData.push({ name: '消费', icon: 'none' });

    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          label: {
            backgroundColor: '#6a7985'
          }
        },
        textStyle: {
          fontSize: 12
        },
        formatter: (function(selectedYear, usageUnit, isElectricity) {
          return function(params) {
            // 月视图tooltip - 显示年-月格式
            const monthLabel = params[0].axisValue;
            const month = monthLabel.replace('月', '');
            const fullDate = `${selectedYear}-${month}`;
            let result = `${fullDate}<br/><br/>`;

            // 先显示费用信息
            const costParam = params.find(param => param.seriesName === '消费');
            if (costParam) {
              result += `<span style="color:#804AFF">●</span> 消费: <strong>¥${costParam.value.toFixed(2)}</strong><br/>`;
              result += '<hr style="margin:3px 0;border:none;border-top:1px solid #ddd;">';
            }

            // 显示用量信息
            let hasUsage = false;
            let totalUsage = 0;
            params.forEach(param => {
              if (param.seriesName === '用量' && param.value > 0) {
                hasUsage = true;
                result += `<span style="display:inline-block;width:10px;height:10px;background:${param.color};margin-right:5px;"></span><strong>${param.seriesName}: ${param.value.toFixed(2)} ${usageUnit}</strong><br/>`;
                totalUsage += param.value;
              } else if (param.seriesName !== '消费' && param.seriesName !== '用量' && param.value > 0) {
                hasUsage = true;
                result += `<span style="display:inline-block;width:10px;height:10px;background:${param.color};margin-right:5px;"></span>${param.seriesName}: ${param.value.toFixed(2)} ${usageUnit}<br/>`;
                totalUsage += param.value;
              }
            });

            if (hasUsage) {
              result += `<hr style="margin:3px 0;border:none;border-top:1px solid #ddd;">`;
              result += `<strong>总用量: ${totalUsage.toFixed(2)} ${usageUnit}</strong>`;
            }

            return result;
          };
        })(this.selectedYear, usageUnit, isElectricity)
      },
      legend: {
        data: legendData,
        bottom: 0,
        itemWidth: 10,
        itemHeight: 20,
        itemGap: 10,
        textStyle: {
          fontSize: 10,
          fontWeight: 'bold'
        },
        formatter: function(name) {
          var colorMap = {
            '峰': '#FF9800',
            '谷': '#4CAF50',
            '平': '#2196F3',
            '尖': '#F44336',
            '无分时': '#9E9E9E',
            '电费': '#804AFF'
          };
          return '{title|' + name + '}';
        },
        textStyle: {
          rich: {
            title: {
              color: '#fff',
              fontSize: 11,
              fontWeight: 'bold',
              padding: [3, 3],
              borderRadius: 2,
              backgroundColor: function(params) {
                var colorMap = {
                  '峰': '#FF9800',
                  '谷': '#4CAF50',
                  '平': '#2196F3',
                  '尖': '#F44336',
                  '无分时': '#9E9E9E'
                };
                return colorMap[params.name] || '#9E9E9E';
              }
            }
          }
        }
      },
      grid: {
        left: '0%',
        right: '0%',
        bottom: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: months,
        axisLine: {
          lineStyle: { color: '#666' }
        },
        axisLabel: {
          color: '#666',
          interval: 0,
          rotate: 45,
          fontSize: 10 
        }
      },
      yAxis: [
        {
          type: 'value',
          name: usageUnit,
          nameLocation: 'end',
          position: 'left',
          axisLine: {
            lineStyle: { color: '#666' }
          },
          axisLabel: {
            color: '#666',
            formatter: function(value) {
              if (value > 100) {
                return (value / 1000).toFixed(1) + 'k';
              }
              return value;
            }
          },
          splitLine: {
            lineStyle: { color: 'rgba(0,0,0,0.1)' }
          }
        },
        {
          type: 'value',
          name: '元',
          position: 'right',
          axisLine: {
            lineStyle: { color: '#804AFF' }
          },
          axisLabel: {
            color: '#804AFF',
            formatter: function(value) {
              if (value > 100) {
                return (value / 1000).toFixed(1) + 'k';
              }
              return value;
            }
          },
          splitLine: {
            show: false
          }
        }
      ],
      series: series
    };

    this.monthChart.setOption(option);
  }

  // 渲染日视图
  renderDayView() {
    // 从统一数据接口获取数据
    if (!this.standardData || !this.standardData.dayUsage || this.standardData.dayUsage.length === 0) {
      return;
    }

    // 销毁现有图表
    if (this.dayViewChart) {
      this.dayViewChart.dispose();
      this.dayViewChart = null;
    }

    // 从统一格式提取所有可用的年份和月份
    const dates = this.standardData.dayUsage
      .filter(item => item.time)
      .map(item => {
        const [year, month] = item.time.split('-');
        return { year: parseInt(year), month: parseInt(month) };
      });
    
    // 提取所有可用的年份
    const availableYears = [...new Set(dates.map(d => d.year))].sort((a, b) => b - a);
    
    // 获取当前年月
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;
    
    // 根据选中的年份过滤月份，只显示该年有数据的月份
    const selectedYear = this.selectedDayYear || availableYears[0];
    let availableMonths = [...new Set(
      dates.filter(d => d.year === selectedYear).map(d => d.month)
    )].sort((a, b) => a - b);
    
    // 如果选中年份是当前年份，只显示到当前月（不包含未来月份）
    if (selectedYear === currentYear) {
      availableMonths = availableMonths.filter(month => month <= currentMonth);
    }
    
    // 检查是否为未来月份
    // 如果选择了未来月份，显示提示文字并隐藏图表
    if (this.selectedDayYear > currentYear || 
        (this.selectedDayYear === currentYear && this.selectedDayMonth > currentMonth)) {
      // 隐藏图表，显示提示文字
      this.dayComboChartEl.style.display = 'none';
      this.futureMonthMessageEl.style.display = 'block';
      return;
    } else {
      // 显示图表，隐藏提示文字
      this.dayComboChartEl.style.display = 'block';
      this.futureMonthMessageEl.style.display = 'none';
    }

    // 如果没有选中的年份或不在可用列表中，选择当前年份（如果可用）或第一个可用年份
    if (!this.selectedDayYear || !availableYears.includes(this.selectedDayYear)) {
      // 如果当前年份在可用列表中，优先使用当前年份
      if (availableYears.includes(currentYear)) {
        this.selectedDayYear = currentYear;
      } else {
        this.selectedDayYear = availableYears[0];
      }
    }
    
    // 对于月份，必须在确定了年份后，从该年份的可用月份中选择
    // 重新获取该年份的可用月份（因为年份可能刚改变）
    availableMonths = [...new Set(
      dates.filter(d => d.year === this.selectedDayYear).map(d => d.month)
    )].sort((a, b) => a - b);
    
    // 如果选中年份是当前年份，只显示到当前月
    if (this.selectedDayYear === currentYear) {
      availableMonths = availableMonths.filter(month => month <= currentMonth);
    }
    
    // ===== 修复年份切换时月份不同步的bug =====
    // 检查当前选中的月份是否在新年份的可用月份中
    const isSelectedMonthAvailable = availableMonths.includes(this.selectedDayMonth);
    
    // 如果当前选中的月份不在新年份的可用月份中，或者没有选中月份，则重新选择月份
    if (!this.selectedDayMonth || !isSelectedMonthAvailable) {
      if (this.selectedDayYear === currentYear && availableMonths.includes(currentMonth)) {
        // 如果选中的是当前年份且当前月有数据，优先选择当前月
        this.selectedDayMonth = currentMonth;
      } else {
        // 否则选择最近的可用月份（最大的月份，因为是降序排列）
        this.selectedDayMonth = availableMonths[availableMonths.length - 1];
      }
    }
    // ===== 修复结束 =====

    // 渲染年月筛选标签
    this.renderDayFilter(availableYears, availableMonths, this.selectedDayYear, this.selectedDayMonth);

    // 从统一格式过滤出当前选中年月的数据
    const monthDays = this.standardData.dayUsage.filter(item => {
      if (!item.time) return false;
      const [year, month] = item.time.split('-').map(Number);
      return year === this.selectedDayYear && month === this.selectedDayMonth;
    }).sort((a, b) => a.time.localeCompare(b.time));

    // 如果没有数据，直接返回
    if (monthDays.length === 0) {
      return;
    }

    // 从统一格式准备图表数据
    const days = monthDays.map(item => {
      const day = parseInt(item.time.split('-')[2]);
      return `${day}`;
    });
    const costs = monthDays.map(item => item.total_amount || 0);
    const peakData = monthDays.map(item => item.usage_ele_peak || 0);
    const valleyData = monthDays.map(item => item.usage_ele_valley || 0);
    const normalData = monthDays.map(item => item.usage_ele_norm || 0);
    const sharpData = monthDays.map(item => item.usage_ele_tip || 0);
    const noTimeData = monthDays.map(item => item.usage_ele_no || 0);
    
    // 获取单位符号（从统一数据格式中获取，不设置默认值）
    const usageUnit = monthDays.length > 0 ? monthDays[0].unit : '';

    // 保存数据到缓存，用于重试
    this._dayChartData = { days, costs, peakData, valleyData, normalData, sharpData, noTimeData, usageUnit };

    // 渲染组合图表 - 使用双重 requestAnimationFrame 确保容器布局完成
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        this.renderDayComboChart(days, costs, peakData, valleyData, normalData, sharpData, noTimeData, usageUnit);
      });
    });
  }

  // 渲染年月筛选标签
  renderDayFilter(years, months, selectedYear, selectedMonth) {
    // 清空两个容器
    this.dayFilterMainEl.innerHTML = '';
    this.dayFilterYearsEl.innerHTML = '';
    
    // 创建年份筛选（放在第一行，居中）
    years.forEach(year => {
      const yearTag = document.createElement('div');
      yearTag.className = 'year-tag';
      yearTag.textContent = `${year}`;
      
      if (year === selectedYear) {
        yearTag.classList.add('active');
      }
      
      yearTag.addEventListener('click', () => {
        this.selectedDayYear = year;
        
        // 当切换年份时，检查当前选中的月份是否在新年份中可用
        // 从数据中提取该年份的所有可用月份
        const dates = this.standardData.dayUsage
          .filter(item => item.time)
          .map(item => {
            const [year, month] = item.time.split('-');
            return { year: parseInt(year), month: parseInt(month) };
          });
        
        const now = new Date();
        const currentYear = now.getFullYear();
        const currentMonth = now.getMonth() + 1;
        
        // 获取新年份的可用月份
        let newYearMonths = [...new Set(
          dates.filter(d => d.year === year).map(d => d.month)
        )].sort((a, b) => a - b);
        
        // 如果新年份是当前年份，只显示到当前月
        if (year === currentYear) {
          newYearMonths = newYearMonths.filter(month => month <= currentMonth);
        }
        
        // 检查当前选中的月份是否在新年份中可用
        const isCurrentMonthAvailable = newYearMonths.includes(this.selectedDayMonth);
        
        // 如果当前月份不可用或者是未来月份，自动选择一个合适的月份
        if (!isCurrentMonthAvailable || 
            (year === currentYear && this.selectedDayMonth > currentMonth)) {
          if (year === currentYear && newYearMonths.includes(currentMonth)) {
            // 如果是当前年份且当前月有数据，优先选择当前月
            this.selectedDayMonth = currentMonth;
          } else if (newYearMonths.length > 0) {
            // 否则选择最新的可用月份（最大的月份）
            this.selectedDayMonth = newYearMonths[newYearMonths.length - 1];
          }
        }
        
        this.renderDayView();
      });
      
      this.dayFilterMainEl.appendChild(yearTag);
    });
    
    // 创建月份筛选（放在第二行，左对齐）
    months.forEach(month => {
      const monthTag = document.createElement('div');
      monthTag.className = 'month-tag';
      monthTag.textContent = `${month}`;
      
      if (month === selectedMonth) {
        monthTag.classList.add('active');
      }
      
      monthTag.addEventListener('click', () => {
        this.selectedDayMonth = month;
        this.renderDayView();
      });
      
      this.dayFilterYearsEl.appendChild(monthTag);
    });
  }

  // 渲染日用电详情组合图
  renderDayComboChart(days, costs, peakData, valleyData, normalData, sharpData, noTimeData, usageUnit) {
    if (!this.echartsLoaded || typeof echarts === 'undefined') {
      return;
    }

    // 检查容器是否存在
    if (!this.dayComboChartEl) {
      return;
    }

    // 强制触发浏览器重排，确保容器有正确的尺寸
    const forceReflow = this.dayComboChartEl.offsetWidth;

    // 检查容器尺寸是否有效
    if (this.dayComboChartEl.offsetWidth === 0 || this.dayComboChartEl.offsetHeight === 0) {
      setTimeout(() => {
        // 使用缓存数据重试
        if (this._dayChartData) {
          const { days, costs, peakData, valleyData, normalData, sharpData, noTimeData, usageUnit } = this._dayChartData;
          this.renderDayComboChart(days, costs, peakData, valleyData, normalData, sharpData, noTimeData, usageUnit);
        } else {
          // 如果没有缓存数据，调用 renderDayView 重新获取数据
          this.renderDayView();
        }
      }, 100);
      return;
    }

    // 销毁现有图表实例
    if (this.dayViewChart) {
      this.dayViewChart.dispose();
      this.dayViewChart = null;
    }

    this.dayViewChart = echarts.init(this.dayComboChartEl);

    // 根据 utility_type 设置系列和图例
    const isElectricity = this.utilityType === 'ele';
    const barColor = this.utilityType === 'gas' ? '#FF9800' : // 燃气黄色
                     this.utilityType === 'water' ? '#2196F3' : // 水蓝色
                     '#9E9E9E'; // 默认灰色
    
    const series = [];
    const legendData = [];
    
    if (isElectricity) {
      // 电力类型显示分时系列
      series.push(
        {
          name: '峰',
          type: 'bar',
          stack: 'usage',
          data: peakData,
          yAxisIndex: 0,
          itemStyle: { color: '#FF9800' }
        },
        {
          name: '谷',
          type: 'bar',
          stack: 'usage',
          data: valleyData,
          yAxisIndex: 0,
          itemStyle: { color: '#4CAF50' }
        },
        {
          name: '平',
          type: 'bar',
          stack: 'usage',
          data: normalData,
          yAxisIndex: 0,
          itemStyle: { color: '#2196F3' }
        },
        {
          name: '尖',
          type: 'bar',
          stack: 'usage',
          data: sharpData,
          yAxisIndex: 0,
          itemStyle: { color: '#F44336' }
        },
        {
          name: '无分时',
          type: 'bar',
          stack: 'usage',
          data: noTimeData,
          yAxisIndex: 0,
          itemStyle: { color: '#9E9E9E' }
        }
      );
      
      legendData.push(
        { name: '峰', icon: 'none' },
        { name: '谷', icon: 'none' },
        { name: '平', icon: 'none' },
        { name: '尖', icon: 'none' },
        { name: '无分时', icon: 'none' }
      );
    } else {
      // 非电力类型只显示用量系列
      series.push({
        name: '用量',
        type: 'bar',
        stack: 'usage',
        data: noTimeData,
        yAxisIndex: 0,
        itemStyle: { color: barColor }
      });
      
      legendData.push({ name: '用量', icon: 'none' });
    }
    
    // 所有类型都显示费用系列
    series.push({
      name: '消费',
      type: 'line',
      data: costs,
      yAxisIndex: 1,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      showSymbol: true,
      lineStyle: {
        width: 3,
        color: '#804AFF'
      },
      itemStyle: {
        color: '#804AFF',
        borderColor: '#fff',
        borderWidth: 1.5,
        shadowBlur: 10,
        shadowColor: 'rgba(128, 74, 255, 0.5)'
      },
      label: {
        show: true,
        position: 'top',
        fontSize: 9,
        color: '#804AFF',
        fontWeight: 600,
        formatter: function(params) {
          if (params.value === 0) {
            return '';
          }
          return params.value.toFixed(0);
        },
        offset: [0, -8]
      },
      emphasis: {
        focus: 'series',
        scale: true,
        scaleSize: 1.3,
        itemStyle: {
          borderColor: '#804AFF',
          borderWidth: 2
        }
      }
    });
    
    legendData.push({ name: '消费', icon: 'none' });

    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          label: {
            backgroundColor: '#6a7985'
          }
        },
        textStyle: {
          fontSize: 12
        },
        formatter: (function(selectedDayYear, selectedDayMonth, usageUnit, isElectricity) {
          return function(params) {
            // 日视图tooltip - 显示年-月-日格式
            const day = params[0].axisValue;
            const fullDate = `${selectedDayYear}-${String(selectedDayMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            let result = `${fullDate}<br/><br/>`;

            // 先显示费用信息
            const costParam = params.find(param => param.seriesName === '消费');
            if (costParam) {
              result += `<span style="color:#804AFF">●</span> 消费: <strong>¥${costParam.value.toFixed(2)}</strong><br/>`;
              result += '<hr style="margin:3px 0;border:none;border-top:1px solid #ddd;">';
            }

            // 显示用量信息
            let hasUsage = false;
            let totalUsage = 0;
            params.forEach(param => {
              if (param.seriesName === '用量' && param.value > 0) {
                hasUsage = true;
                result += `<span style="display:inline-block;width:10px;height:10px;background:${param.color};margin-right:5px;"></span><strong>${param.seriesName}: ${param.value.toFixed(2)} ${usageUnit}</strong><br/>`;
                totalUsage += param.value;
              } else if (param.seriesName !== '消费' && param.seriesName !== '用量' && param.value > 0) {
                hasUsage = true;
                result += `<span style="display:inline-block;width:10px;height:10px;background:${param.color};margin-right:5px;"></span>${param.seriesName}: ${param.value.toFixed(2)} ${usageUnit}<br/>`;
                totalUsage += param.value;
              }
            });

            if (hasUsage) {
              result += `<hr style="margin:3px 0;border:none;border-top:1px solid #ddd;">`;
              result += `<strong>总用量: ${totalUsage.toFixed(2)} ${usageUnit}</strong>`;
            }

            return result;
          };
        })(this.selectedDayYear, this.selectedDayMonth, usageUnit, isElectricity)
      },
      legend: {
        data: legendData,
        bottom: 0,
        itemWidth: 10,
        itemHeight: 20,
        itemGap: 10,
        textStyle: {
          fontSize: 10,
          fontWeight: 'bold'
        },
        formatter: function(name) {
          return '{title|' + name + '}';
        },
        textStyle: {
          rich: {
            title: {
              color: '#fff',
              fontSize: 11,
              fontWeight: 'bold',
              padding: [3, 3],
              borderRadius: 2,
              backgroundColor: function(params) {
                if (params.name === '用量') {
                  return barColor;
                } else if (params.name === '消费') {
                  return '#804AFF';
                } else if (params.name === '缴费') {
                  return '#00C853';
                }
                return '#9E9E9E';
              }
            }
          }
        }
      },
      grid: {
        left: '0%',
        right: '0%',
        bottom: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: days,
        axisLine: {
          lineStyle: { color: '#666' }
        },
        axisLabel: {
          color: '#666',
          interval: 0,
          rotate: 45,
          fontSize: 9
        }
      },
      yAxis: [
        {
          type: 'value',
          name: usageUnit,
          nameLocation: 'end',
          position: 'left',
          axisLine: {
            lineStyle: { color: '#666' }
          },
          axisLabel: {
            color: '#666',
            formatter: function(value) {
              if (value > 100) {
                return (value / 1000).toFixed(1) + 'k';
              }
              return value;
            }
          },
          splitLine: {
            lineStyle: { color: 'rgba(0,0,0,0.1)' }
          }
        },
        {
          type: 'value',
          name: '元',
          position: 'right',
          axisLine: {
            lineStyle: { color: '#804AFF' }
          },
          axisLabel: {
            color: '#804AFF',
            formatter: function(value) {
              if (value > 100) {
                return (value / 1000).toFixed(1) + 'k';
              }
              return value;
            }
          },
          splitLine: {
            show: false
          }
        }
      ],
      series: series
    };

    this.dayViewChart.setOption(option);
  }

  // 销毁年度图表
  destroyYearCharts() {
    if (this.yearChart) {
      this.yearChart.dispose();
      this.yearChart = null;
    }
  }

  // 销毁月度图表
  destroyMonthCharts() {
    if (this.monthChart) {
      this.monthChart.dispose();
      this.monthChart = null;
    }
  }

  // 销毁日视图图表
  destroyDayCharts() {
    if (this.dayViewChart) {
      this.dayViewChart.dispose();
      this.dayViewChart = null;
    }
  }

  // 更新日历视图
  async updateCalendarView() {
    // 如果当前是月视图，重新渲染月视图图表
    if (this.currentView === 'month') {
      this.renderMonthView();
      return;
    }
    
    // 从统一数据接口获取数据
    if (!this.standardData || !this.standardData.dayUsage || this.standardData.dayUsage.length === 0) {
      this.renderCalendar([], 0, 0);
      return;
    }
    
    // 从统一格式筛选当前年月的日数据
    const currentMonthStr = `${this.calCurrentYear}-${String(this.calCurrentMonth).padStart(2, '0')}`;
    const monthDays = this.standardData.dayUsage.filter(dayData => 
      dayData.time && dayData.time.startsWith(currentMonthStr)
    );
    
    // 如果配置了device_entity，检查每个日期是否有设备历史数据
    if (this.deviceEntityConfig && this.deviceEntityConfig.length > 0) {
      // 创建当前月份的所有日期数组，但只包含今日以前（含今日）的日期
      const allDaysInMonth = [];
      const lastDay = new Date(this.calCurrentYear, this.calCurrentMonth, 0).getDate();
      
      // 获取当前日期，用于过滤未来日期
      const now = new Date();
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      
      for (let day = 1; day <= lastDay; day++) {
        const dayStr = `${this.calCurrentYear}-${String(this.calCurrentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        
        // 检查是否为未来日期（不包括今天）
        const dayDate = new Date(dayStr);
        const dayStart = new Date(dayDate.getFullYear(), dayDate.getMonth(), dayDate.getDate());
        if (dayStart > today) {
          // 跳过未来日期，不添加到检查列表
          continue;
        }
        
        // 查找是否已有对应的数据
        const existingDayData = monthDays.find(d => d.time === dayStr);
        
        if (existingDayData) {
          // 如果已有数据，直接使用
          allDaysInMonth.push({
            time: dayStr,
            day: day,
            hasDeviceHistory: existingDayData.hasDeviceHistory || false,
            existingData: true
          });
        } else {
          // 如果没有数据，创建新的对象
          allDaysInMonth.push({
            time: dayStr,
            day: day,
            hasDeviceHistory: false,
            existingData: false
          });
        }
      }
      
      // 只对今日以前（含今日）的日期进行设备历史检查
      const promises = allDaysInMonth.map(async (dayObj) => {
        const dayStr = dayObj.time;
        const dayNum = dayObj.day;
        
        if (!dayStr) {
          dayObj.hasDeviceHistory = false;
          return;
        }
        
        const dayDate = new Date(dayStr);
        if (isNaN(dayDate.getTime())) {
          dayObj.hasDeviceHistory = false;
          return;
        }
        
        const startOfDay = new Date(dayDate.getFullYear(), dayDate.getMonth(), dayDate.getDate());
        const endOfDay = new Date(dayDate.getFullYear(), dayDate.getMonth(), dayDate.getDate() + 1);
        
        let hasDeviceHistory = false;
        const devicePromises = this.deviceEntityConfig.map(async (deviceConfig) => {
          try {
            const history = await this.getHistory(deviceConfig.entity, startOfDay, endOfDay);
            if (history && history.length > 0) {
              hasDeviceHistory = true;
            }
          } catch (error) {
            // Silently fail
          }
        });
        
        await Promise.all(devicePromises);
        dayObj.hasDeviceHistory = hasDeviceHistory;
      });
      
      await Promise.all(promises);
      
      // 将设备历史信息更新到monthDays中的对应日期
      allDaysInMonth.forEach(dayObj => {
        if (dayObj.existingData) {
          // 更新已有数据
          const existingDay = monthDays.find(d => d.time === dayObj.time);
          if (existingDay) {
            existingDay.hasDeviceHistory = dayObj.hasDeviceHistory;
          }
        } else {
          // 为没有用电数据的日期创建数据对象
          if (dayObj.hasDeviceHistory) {
            monthDays.push({
              time: dayObj.time,
              day: dayObj.day,
              total_usage: 0,
              total_amount: 0,
              unit: monthDays.length > 0 ? monthDays[0].unit : '',
              hasDeviceHistory: true
            });
          }
        }
      });
    }
    
    // 计算月统计
    let monthUsage = 0;
    let monthCost = 0;
    monthDays.forEach(day => {
      monthUsage += day.total_usage || 0;
      monthCost += day.total_amount || 0;
    });
    
    // 计算年统计
    let yearUsage = 0;
    let yearCost = 0;
    const yearStr = this.calCurrentYear.toString();
    this.standardData.dayUsage.forEach(day => {
      if (day.time && day.time.startsWith(yearStr)) {
        yearUsage += day.total_usage || 0;
        yearCost += day.total_amount || 0;
      }
    });
    
    // 获取单位符号（从月份数据中获取，必须从数据中获取）
    const usageUnit = monthDays.length > 0 && monthDays[0] ? monthDays[0].unit : '';
    
    // 更新统计信息
    this.calMonthUsageEl.textContent = `${monthUsage.toFixed(2)} ${usageUnit}`;
    this.calMonthCostEl.textContent = `¥${monthCost.toFixed(2)}`;
    this.calYearUsageEl.textContent = `${yearUsage.toFixed(2)} ${usageUnit}`;
    this.calYearCostEl.textContent = `¥${yearCost.toFixed(2)}`;
    
    // 渲染日历
    this.renderCalendar(monthDays, monthUsage, monthCost);
  }
  
  // 渲染日历网格
  renderCalendar(monthDays, monthUsage, monthCost) {
    // 清空日历网格，保留星期标题
    const grid = this.calendarGridEl;
    while (grid.children.length > 7) {
      grid.removeChild(grid.lastChild);
    }
    
    const now = new Date();
    const firstDay = new Date(this.calCurrentYear, this.calCurrentMonth - 1, 1);
    const lastDay = new Date(this.calCurrentYear, this.calCurrentMonth, 0);
    
    // 获取第一天是星期几（0=周日，1=周一...）
    let startDayOfWeek = firstDay.getDay();
    // 调整为0=周一，1=周二...6=周日
    startDayOfWeek = startDayOfWeek === 0 ? 6 : startDayOfWeek - 1;
    
    // 创建日历数据
    const calendarData = [];
    
    // 添加空白单元格
    for (let i = 0; i < startDayOfWeek; i++) {
      calendarData.push(null);
    }
    
    // 添加日期
    for (let day = 1; day <= lastDay.getDate(); day++) {
      const dayStr = `${this.calCurrentYear}-${String(this.calCurrentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      const dayData = monthDays.find(d => d.time === dayStr);
      
      if (dayData && dayData.total_usage > 0) {
        calendarData.push({
          day: day,
          usage: dayData.total_usage,
          amount: dayData.total_amount,
          dayData: dayData,
          hasData: true
        });
      } else {
        // 即使没有用电数据，也要创建包含设备历史信息的日历数据对象
        calendarData.push({
          day: day,
          dayData: dayData ? {
            time: dayData.time,
            unit: dayData.unit,
            hasDeviceHistory: dayData.hasDeviceHistory || false
          } : null,
          hasData: false
        });
      }
    }
    
    // 创建日期单元格
    
    // 先计算当月用电量的最大值和最小值
    let maxUsage = 0;
    let minUsage = Infinity;
    let maxUsageDay = null;
    let minUsageDay = null;
    
    calendarData.forEach(day => {
      if (day && day.hasData && day.dayData) {
        const usage = parseFloat(day.usage) || 0;
        if (usage > maxUsage) {
          maxUsage = usage;
          maxUsageDay = day.day;
        }
        if (usage < minUsage && usage > 0) {
          minUsage = usage;
          minUsageDay = day.day;
        }
      }
    });
    
    // 如果所有值都是0，重置minUsage
    if (minUsage === Infinity) {
      minUsage = 0;
    }
    
    calendarData.forEach(day => {
      const cell = document.createElement('div');
      cell.className = 'calendar-day';
      
      if (day) {
        cell.classList.add('has-date');
        
        // 判断是否是今天
        const isToday = day.day === now.getDate() && 
            this.calCurrentYear === now.getFullYear() && 
            this.calCurrentMonth === now.getMonth() + 1;
        
        if (isToday) {
          cell.classList.add('today');
        }
        
        // 判断是否是当月用电量最大或最小的单元格
        if (day.hasData && day.dayData) {
          const usage = parseFloat(day.usage) || 0;
          if (usage === maxUsage && maxUsage > 0) {
            cell.classList.add('max-usage-day');
          } else if (usage === minUsage && minUsage > 0) {
            cell.classList.add('min-usage-day');
          }
        }
        
        // 添加预计使用天数的进度条
        // 从UI元素获取剩余天数，支持多用户/多类切换
        let remainingDays = 0;
        const remainingDaysElement = this.shadowRoot.querySelector('#remaining-days');
        if (remainingDaysElement) {
          const daysValue = remainingDaysElement.textContent;
          remainingDays = parseInt(daysValue, 10) || 0;
        }
        
        // 检查是否是预付费用户，预付费用户显示进度条
        let isPrepaid = false;
        if (this._hass && this.entityId) {
          const entity = this._hass.states[this.entityId];
          if (entity) {
            // 从实体顶层节点获取"预付费"字段
            let prepaidValue = this.getEntityAttribute(entity, '预付费');
            
            // 如果顶层节点没有，尝试从data节点的"预付费"字段获取
            if (!prepaidValue && entity.attributes && entity.attributes.data) {
              prepaidValue = entity.attributes.data['预付费'];
            }
            
            isPrepaid = (prepaidValue === '否');
          }
        }
        
        // 如果 remainingDays 存在且大于0，且不是预付费用户，添加进度条
        if (remainingDays > 0 && !isPrepaid) {
          const todayDate = new Date();
          const startDate = new Date(todayDate.getFullYear(), todayDate.getMonth(), todayDate.getDate());
          const endDate = new Date(startDate.getTime() + remainingDays * 24 * 60 * 60 * 1000);
          
          // 检查当前日期是否在进度条范围内
          const cellDate = new Date(this.calCurrentYear, this.calCurrentMonth - 1, day.day);
          
          // 只在当前月份且日期在今天到结束日期之间（含）时显示进度条
          if (cellDate >= startDate && cellDate <= endDate && 
              cellDate.getMonth() + 1 === this.calCurrentMonth && 
              cellDate.getFullYear() === this.calCurrentYear) {
            const progressBar = document.createElement('div');
            progressBar.className = 'usage-progress-bar';
            cell.appendChild(progressBar);
          }
        }
        
        // 判断是否是未来日期
        const cellDate = new Date(this.calCurrentYear, this.calCurrentMonth - 1, day.day);
        const isFutureDate = cellDate > now;
        
        // 如果是未来日期，添加禁用样式
        if (isFutureDate) {
          cell.classList.add('future-date');
          cell.style.opacity = '0.5';
          cell.style.cursor = 'not-allowed';
        } else {
          // 非未来日期都可以点击
          cell.style.cursor = 'pointer';
        }
        
        // 创建日期圆圈
        const dateCircle = document.createElement('span');
        dateCircle.className = 'date-circle';
        dateCircle.textContent = day.day;
        cell.appendChild(dateCircle);
        
        // 如果有数据，显示用量和费用
        if (day.hasData) {
          cell.classList.add('has-data');
          
          // 获取单位符号（必须从数据中获取）
          const usageUnit = day.dayData.unit;
          
          const dataValue = document.createElement('div');
          dataValue.className = 'data-value';
          dataValue.textContent = `${day.usage.toFixed(2)}${usageUnit}`;
          cell.appendChild(dataValue);
          
          const calcValue = document.createElement('div');
          calcValue.className = 'calc-value';
          calcValue.textContent = `¥${day.amount.toFixed(2)}`;
          cell.appendChild(calcValue);
        }
        
        // 如果配置了device_entity且该日期有设备历史数据，显示H标记（无论是否有用电数据）
        if (this.deviceEntityConfig && this.deviceEntityConfig.length > 0 && day.dayData && day.dayData.hasDeviceHistory) {
          const deviceMarker = document.createElement('span');
          deviceMarker.className = 'device-history-marker';
          deviceMarker.textContent = 'H';
          cell.appendChild(deviceMarker);
        }
        
        // 为所有非未来日期的单元格添加点击事件
        if (!isFutureDate) {
          // 只有当有数据或者配置了device_entity时，才允许点击
          if (day.hasData || (this.deviceEntityConfig && this.deviceEntityConfig.length > 0)) {
            cell.addEventListener('click', () => {
              const dayStr = `${this.calCurrentYear}-${String(this.calCurrentMonth).padStart(2, '0')}-${String(day.day).padStart(2, '0')}`;
              // 如果有数据，显示完整详情；如果无数据，显示空数据提示
              this.showDayModal(dayStr, day.hasData ? day.dayData : null);
            });
          } else {
            // 无数据且没有配置device_entity时，禁用点击
            cell.style.cursor = 'not-allowed';
            cell.style.opacity = '0.5';
          }
        }
      }
      
      grid.appendChild(cell);
    });
  }
  
  // 显示日详情模态框
  showDayModal(dateStr, dayData) {
    // 设置标题
    const [year, month, day] = dateStr.split('-');
    const modalTitle = this.textMap && this.textMap.dayModalTitle ? this.textMap.dayModalTitle : '用电详情';
    this.dayModalTitleEl.textContent = `${year}年${parseInt(month)}月${parseInt(day)}日 ${modalTitle}`;
    
    // 清空模态框内容
    this.dayModalBodyEl.innerHTML = '';
    
    // 检查是否有数据
    if (!dayData) {
      // 无数据时显示提示信息
      const noDataMessage = document.createElement('div');
      noDataMessage.style.textAlign = 'center';
      noDataMessage.style.padding = '40px 20px';
      noDataMessage.style.color = 'var(--text-color)';
      noDataMessage.style.opacity = '0.7';
      noDataMessage.innerHTML = `
        <div style="font-size: 16px; margin-bottom: 10px;">📊</div>
        <div style="font-size: 14px;">该日期暂无用电数据</div>
        <div style="font-size: 12px; margin-top: 5px;">可能是数据尚未更新或当日无用电记录</div>
      `;
      
      this.dayModalBodyEl.appendChild(noDataMessage);
      
      // 如果配置了设备实体，显示设备轨道（即使没有用电数据）
      if (this.deviceEntityConfig && this.deviceEntityConfig.length > 0) {
        this.renderDeviceTracks(dateStr);
      }
    } else {
      // 有数据时显示完整的详情
      // 创建柱状图区域（替代原来的饼图）
      const barChartSection = document.createElement('div');
      barChartSection.className = 'pie-chart-section';

      // 添加标题
      const barChartTitle = document.createElement('div');
      barChartTitle.className = 'pie-chart-title';
      barChartTitle.style.fontSize = '14px';
      barChartTitle.style.fontWeight = '600';
      barChartTitle.style.color = 'var(--text-color)';
      barChartTitle.style.textAlign = 'center';
      barChartTitle.style.marginBottom = '0px';
      const barTitle = this.textMap && this.textMap.dayBarChartTitle ? this.textMap.dayBarChartTitle : '历年今日用量对比';
      barChartTitle.textContent = barTitle;
      barChartSection.appendChild(barChartTitle);

      // 创建柱状图容器
      const barChartContainer = document.createElement('div');
      barChartContainer.className = 'pie-chart-container';
      barChartContainer.id = 'day-bar-chart';
      
      barChartSection.appendChild(barChartContainer);
      this.dayModalBodyEl.appendChild(barChartSection);

      // 获取所有年份的今天数据
      const todayData = this.getAllYearsTodayData(dateStr);
      
      // 渲染柱状图
      setTimeout(() => {
        this.renderDayBarChart(todayData, dateStr);
      }, 100);

      // 添加分割线
      const barDivider = document.createElement('div');
      barDivider.style.height = '1px';
      barDivider.style.backgroundColor = 'var(--secondary-text)';
      barDivider.style.opacity = '0.3';
      barDivider.style.marginBottom = '10px';
      this.dayModalBodyEl.appendChild(barDivider);

      // 如果配置了设备实体，显示设备轨道
      if (this.deviceEntityConfig && this.deviceEntityConfig.length > 0) {
        this.renderDeviceTracks(dateStr);
      }
    }

    // 显示模态框（使用平滑动画）
    this.dayModalEl.style.display = 'flex';
    
    // 强制重排以确保CSS动画生效
    this.dayModalEl.offsetHeight;
    
    // 应用隐藏配置
    requestAnimationFrame(() => {
      this.applyHiddenConfig();
    });
  }
  
  // 渲染日柱状图（替代原来的饼图）
  renderDayBarChart(valleyEle, peakEle, normalEle, sharpEle, noTimeEle, totalEle, hasTimeData, usageUnit = '', historyTodayData = null, dateStr = '') {
    const pieChartEl = this.dayModalBodyEl.querySelector('#day-pie-chart');
    if (!pieChartEl) {
      return;
    }
    
    // 销毁之前的图表实例
    if (this.dayChart) {
      this.dayChart.dispose();
      this.dayChart = null;
    }
    
    // 检查ECharts是否可用
    if (typeof echarts === 'undefined') {
      return;
    }
    
    this.dayChart = echarts.init(pieChartEl, null, { width: 210, height: 140 });
    
    // 根据 utility_type 设置颜色和数据
    const isElectricity = this.utilityType === 'ele';
    const pieColor = this.utilityType === 'gas' ? '#FF9800' : // 燃气黄色
                     this.utilityType === 'water' ? '#2196F3' : // 水蓝色
                     '#9E9E9E'; // 默认灰色
    
    // 构建数据数组
    const data = [];

    if (isElectricity) {
      // 电力类型显示分时数据
      if (sharpEle > 0) {
        data.push({ value: sharpEle, name: '尖', itemStyle: { color: '#F44336' }, label: { color: '#F44336' } });
      }
      if (peakEle > 0) {
        data.push({ value: peakEle, name: '峰', itemStyle: { color: '#FF9800' }, label: { color: '#FF9800' } });
      }
      if (normalEle > 0) {
        data.push({ value: normalEle, name: '平', itemStyle: { color: '#2196F3' }, label: { color: '#2196F3' } });
      }
      if (valleyEle > 0) {
        data.push({ value: valleyEle, name: '谷', itemStyle: { color: '#4CAF50' }, label: { color: '#4CAF50' } });
      }

      // 如果没有分时数据，显示"无分时"饼图
      if (!hasTimeData) {
        data.push({ 
          value: totalEle > 0 ? totalEle : 1, 
          name: '无分时', 
          itemStyle: { color: '#999999' }, 
          label: { color: '#999999' } 
        });
      }
    } else {
      // 非电力类型只显示用量
      data.push({ 
        value: totalEle > 0 ? totalEle : 1, 
        name: '用量', 
        itemStyle: { color: pieColor }, 
        label: { color: pieColor } 
      });
    }
    
    const option = {
      tooltip: {
        trigger: 'item',
        textStyle: {
          fontSize: 10
        },
        formatter: (function(usageUnit) {
          return function(params) {
            if (params.name === '无分时') {
              return params.name + '：<br/>' + 
                     params.value + usageUnit + '<br/>' + 
                     params.percent + '%';
            }
            return params.name + '：<br/>' + 
                   params.value + usageUnit + '<br/>' + 
                   params.percent + '%';
          };
        })(usageUnit)
      },

      series: [
        {
          type: 'pie',
          radius: ['25%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 4,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: true,
            formatter: (function(usageUnit) {
              return function(params) {
                return params.name + '\n' + params.value + usageUnit;
              };
            })(usageUnit),
            fontSize: 11,
            fontWeight: 'normal',
            color: function(params) {
              if (isElectricity) {
                // 电力类型根据系列名称返回对应的颜色
                const colorMap = {
                  '尖': '#F44336',
                  '峰': '#FF9800',
                  '平': '#2196F3',
                  '谷': '#4CAF50',
                  '无分时': '#999999'
                };
                return colorMap[params.name] || '#333';
              } else {
                // 非电力类型使用对应的颜色
                return pieColor;
              }
            }
          },
          labelLine: {
            show: true,
            length: 10,
            length2: 10
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 12,
              fontWeight: 'bold'
            },
            scale: true,
            scaleSize: 5
          },
          data: data
        }
      ]
    };
    
    try {
      this.dayChart.setOption(option);
      // Successfully rendered
      
      // 确保图表正确渲染尺寸
      setTimeout(() => {
        if (this.dayChart) {
          this.dayChart.resize();
        }
      }, 50);
    } catch (error) {
      // Render failed
    }
  }
  
  // 渲染日柱状图（显示历年今日数据对比）
  renderDayBarChart(todayData, dateStr) {
    const barChartEl = this.dayModalBodyEl.querySelector('#day-bar-chart');
    if (!barChartEl) {
      return;
    }
    
    // 销毁之前的图表实例
    if (this.dayChart) {
      this.dayChart.dispose();
      this.dayChart = null;
    }
    
    // 检查ECharts是否可用
    if (typeof echarts === 'undefined') {
      return;
    }
    
    this.dayChart = echarts.init(barChartEl);
    
    // 根据 utility_type 设置系列和颜色
    const isElectricity = this.utilityType === 'ele';
    const barColor = this.utilityType === 'gas' ? '#FF9800' : // 燃气黄色
                     this.utilityType === 'water' ? '#2196F3' : // 水蓝色
                     '#9E9E9E'; // 默认灰色
    
    // 如果数据为空
    if (!todayData || todayData.length === 0) {
      return;
    }
    
    // 从数据中提取年份、用量和金额
    const years = todayData.map(item => {
      const date = new Date(item.time);
      return date.getFullYear().toString();
    });
    
    // 提取完整日期字符串（yyyy-mm-dd）用于tooltip
    const dates = todayData.map(item => {
      const date = new Date(item.time);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    });
    
    const amounts = todayData.map(item => item.total_amount || 0);
    
    // 提取分时数据
    const peakData = todayData.map(item => item.usage_ele_peak || 0);
    const valleyData = todayData.map(item => item.usage_ele_valley || 0);
    const normalData = todayData.map(item => item.usage_ele_norm || 0);
    const sharpData = todayData.map(item => item.usage_ele_tip || 0);
    const noTimeData = todayData.map(item => item.usage_ele_no || 0);
    
    // 获取单位符号（从数据中获取，不设置默认值）
    const usageUnit = todayData.length > 0 ? (todayData[0].unit || '') : '';
    
    // 构建系列配置
    const series = [];
    const legendData = [];
    
    if (isElectricity) {
      // 电力类型显示分时系列（堆叠柱状图）
      series.push(
        {
          name: '峰',
          type: 'bar',
          stack: 'usage',
          data: peakData,
          yAxisIndex: 0,
          itemStyle: { color: '#FF9800' }
        },
        {
          name: '谷',
          type: 'bar',
          stack: 'usage',
          data: valleyData,
          yAxisIndex: 0,
          itemStyle: { color: '#4CAF50' }
        },
        {
          name: '平',
          type: 'bar',
          stack: 'usage',
          data: normalData,
          yAxisIndex: 0,
          itemStyle: { color: '#2196F3' }
        },
        {
          name: '尖',
          type: 'bar',
          stack: 'usage',
          data: sharpData,
          yAxisIndex: 0,
          itemStyle: { color: '#F44336' }
        },
        {
          name: '无分时',
          type: 'bar',
          stack: 'usage',
          data: noTimeData,
          yAxisIndex: 0,
          itemStyle: { color: '#9E9E9E' }
        }
      );
      
      legendData.push(
        { name: '峰', icon: 'none' },
        { name: '谷', icon: 'none' },
        { name: '平', icon: 'none' },
        { name: '尖', icon: 'none' },
        { name: '无分时', icon: 'none' }
      );
    } else {
      // 非电力类型只显示用量系列
      const totalUsageData = todayData.map(item => item.total_usage || 0);
      series.push({
        name: '用量',
        type: 'bar',
        stack: 'usage',
        data: totalUsageData,
        yAxisIndex: 0,
        itemStyle: { color: barColor }
      });
      
      legendData.push({ name: '用量', icon: 'none' });
    }
    
    // 所有类型都显示费用系列（折线图）
    series.push({
      name: '消费',
      type: 'line',
      data: amounts,
      yAxisIndex: 1,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      showSymbol: true,
      lineStyle: {
        width: 3,
        color: '#804AFF'
      },
      itemStyle: {
        color: '#804AFF',
        borderColor: '#fff',
        borderWidth: 1.5,
        shadowBlur: 10,
        shadowColor: 'rgba(128, 74, 255, 0.5)'
      },
      label: {
        show: true,
        position: 'top',
        fontSize: 10,
        color: '#804AFF',
        fontWeight: 600,
        formatter: function(params) {
          if (params.value === 0) {
            return '';
          }
          return params.value.toFixed(2);
        },
        offset: [0, -8]
      },
      emphasis: {
        focus: 'series',
        scale: true,
        scaleSize: 1.3,
        itemStyle: {
          borderColor: '#804AFF',
          borderWidth: 2
        }
      }
    });
    
    legendData.push({ name: '消费', icon: 'none' });
    
    // 图表配置
    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'none'
        },
        textStyle: {
          fontSize: 10
        },
        formatter: function(params) {
          // 获取当前柱子的索引
          const dataIndex = params[0].dataIndex;
          
          // 第一行：从数据中提取的正确日期格式 yyyy-mm-dd
          let result = dates[dataIndex] + '<br/>';
          
          // 第二行：消费金额
          const costParam = params.find(param => param.seriesName === '消费');
          if (costParam) {
            result += costParam.marker + '消费: ¥' + costParam.value.toFixed(2) + '<br/>';
          }
          
          // 第三行：总用量（计算所有分时数据的和）
          const usageParams = params.filter(param => param.seriesName !== '消费' && param.value > 0);
          const totalUsage = usageParams.reduce((sum, param) => sum + param.value, 0);
          if (totalUsage > 0) {
            result += '用量: ' + totalUsage.toFixed(2) + usageUnit + '<br/>';
          }
          
          // 添加分割线
          if (usageParams.length > 0) {
            result += '<hr style="margin:3px 0;border:none;border-top:1px solid #ddd;">';
            
            // 下方显示分时用电详情
            usageParams.forEach(item => {
              result += item.marker + item.seriesName + ': ' + item.value + usageUnit + '<br/>';
            });
          }
          
          return result;
        }
      },
      legend: {
        data: legendData,
        textStyle: {
          fontSize: 10,
          color: 'var(--text-color)'
        },
        top: 5,
        itemWidth: 12,
        itemHeight: 8,
        formatter: function(name) {
          const colorMap = {
            '峰': '#FF9800',
            '谷': '#4CAF50',
            '平': '#2196F3',
            '尖': '#F44336',
            '无分时': '#9E9E9E',
            '用量': barColor,
            '消费': '#804AFF'
          };
          return '{title|' + name + '}';
        },
        textStyle: {
          rich: {
            title: {
              color: '#fff',
              fontSize: 11,
              fontWeight: 'bold',
              padding: [3, 3],
              borderRadius: 2,
              backgroundColor: function(params) {
                const colorMap = {
                  '峰': '#FF9800',
                  '谷': '#4CAF50',
                  '平': '#2196F3',
                  '尖': '#F44336',
                  '无分时': '#9E9E9E',
                  '用量': barColor,
                  '消费': '#804AFF'
                };
                return colorMap[params.name] || '#9E9E9E';
              }
            }
          }
        }
      },
      grid: {
        left: '0%',
        right: '0%',
        bottom: '5%',
        top: '30%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: years,
        axisLine: {
          lineStyle: { color: 'var(--text-color)' }
        },
        axisLabel: {
          color: 'var(--text-color)',
          interval: 0,
          rotate: 45,
          fontSize: 10
        }
      },
      yAxis: [
        {
          type: 'value',
          name: usageUnit,
          nameLocation: 'end',
          position: 'left',
          axisLine: {
            lineStyle: { color: 'var(--text-color)' }
          },
          axisLabel: {
            color: 'var(--text-color)',
            formatter: function(value) {
              if (value > 100) {
                return (value / 1000).toFixed(1) + 'k';
              }
              return value;
            }
          },
          splitLine: {
            lineStyle: { color: 'rgba(0,0,0,0.1)' }
          }
        },
        {
          type: 'value',
          name: '元',
          position: 'right',
          axisLine: {
            lineStyle: { color: '#804AFF' }
          },
          axisLabel: {
            color: '#804AFF',
            formatter: function(value) {
              if (value > 100) {
                return (value / 1000).toFixed(1) + 'k';
              }
              return value;
            }
          },
          splitLine: {
            show: false
          }
        }
      ],
      series: series
    };
    
    try {
      this.dayChart.setOption(option);
      
      // 确保图表正确渲染尺寸
      setTimeout(() => {
        if (this.dayChart) {
          this.dayChart.resize();
        }
      }, 50);
    } catch (error) {
      console.error('渲染日柱状图失败:', error);
    }
  }
  
  // 获取历史今天的数据
  getHistoryTodayData(dateStr) {
    if (!this.standardData || !this.standardData.dayUsage || this.standardData.dayUsage.length === 0) {
      return null;
    }
    
    // 解析日期字符串，获取月份和日期
    const [year, month, day] = dateStr.split('-').map(Number);
    
    // 查找历史数据中相同月份和日期的数据（排除当前年）
    const historyData = this.standardData.dayUsage.find(item => {
      if (!item.time) return false;
      
      const itemDate = new Date(item.time);
      const itemYear = itemDate.getFullYear();
      const itemMonth = itemDate.getMonth() + 1;
      const itemDay = itemDate.getDate();
      
      // 匹配月份和日期，但不匹配年份（排除当前年）
      return itemYear !== year && itemMonth === month && itemDay === day;
    });
    
    return historyData || null;
  }
  
  // 获取所有年份的今天数据
  getAllYearsTodayData(dateStr) {
    if (!this.standardData || !this.standardData.dayUsage || this.standardData.dayUsage.length === 0) {
      return [];
    }
    
    // 解析日期字符串，获取月份和日期
    const [year, month, day] = dateStr.split('-').map(Number);
    
    // 查找所有年份中相同月份和日期的数据，按年份排序
    const allData = this.standardData.dayUsage.filter(item => {
      if (!item.time) return false;
      
      const itemDate = new Date(item.time);
      const itemMonth = itemDate.getMonth() + 1;
      const itemDay = itemDate.getDate();
      
      // 匹配月份和日期
      return itemMonth === month && itemDay === day;
    }).sort((a, b) => {
      // 按年份升序排序
      const yearA = new Date(a.time).getFullYear();
      const yearB = new Date(b.time).getFullYear();
      return yearA - yearB;
    });
    
    return allData;
  }
  

  // 隐藏日详情模态框
  hideDayModal() {
    this.dayModalEl.style.display = 'none';
    
    // 隐藏提示框
    this.hideTooltip();
    // 销毁饼图实例
    if (this.dayChart) {
      this.dayChart.dispose();
      this.dayChart = null;
    }
    // 销毁桑基图实例
    if (this.sankeyChart) {
      this.sankeyChart.dispose();
      this.sankeyChart = null;
    }
    // 清空模态框内容，防止下次打开时冲突
    this.dayModalBodyEl.innerHTML = '';
    
    // 清空设备数据
    this.dayDeviceData = null;
    
    // 重置显示状态
    this.showSankeyChart = false;
  }

  // ==================== 缴费历史相关方法 ====================

  // 显示缴费历史模态框
  async showPayHistoryModal() {
    // 尝试获取缴费历史数据
    try {
      const payHistory = await this.fetchPayHistory();
      if (!payHistory || payHistory.length === 0) {
        // 没有数据时不做反应
        return;
      }

      // 渲染缴费历史
      this.renderPayHistory(payHistory);

      // 显示模态框
      this.payHistoryModalEl.style.display = 'flex';
    } catch (error) {
      // 文件不存在或访问失败，不做反应
      console.log('缴费历史数据获取失败或不存在:', error);
    }
  }

  // 隐藏缴费历史模态框
  hidePayHistoryModal() {
    this.payHistoryModalEl.style.display = 'none';
    // 销毁饼图实例
    if (this.paySourceChart) {
      this.paySourceChart.dispose();
      this.paySourceChart = null;
    }
    // 清空模态框内容
    this.payHistoryBodyEl.innerHTML = '';
  }

  // 更新缴费次数角标
  async _updatePayCountBadge() {
    if (!this.payCountBadgeEl) return;
    try {
      const payHistory = await this.fetchPayHistory();
      if (payHistory && payHistory.length > 0) {
        this.payCountBadgeEl.textContent = `${payHistory.length}次`;
      } else {
        this.payCountBadgeEl.textContent = '';
      }
    } catch (e) {
      this.payCountBadgeEl.textContent = '';
    }
  }

  // 获取缴费历史数据
  async fetchPayHistory() {
    try {
      // 如果配置了缴费实体，从实体获取数据
      if (this.jiaofeiEntityId) {
        const entityState = this._hass.states[this.jiaofeiEntityId];
        if (!entityState) {
          throw new Error(`缴费实体 ${this.jiaofeiEntityId} 不存在`);
        }

        const attributes = entityState.attributes;
        
        // 必须配置 node 参数
        if (!this.jiaofeiFieldMapping || !this.jiaofeiFieldMapping.node) {
          throw new Error('缴费实体未配置 node 参数');
        }
        
        const nodeName = this.jiaofeiFieldMapping.node;
        const dataArray = attributes[nodeName];
        
        if (!dataArray || !Array.isArray(dataArray)) {
          throw new Error(`缴费实体的 ${nodeName} 节点不存在或不是数组`);
        }
        
        // 使用配置的字段映射读取数据
        const dateField = this.jiaofeiFieldMapping.date || 'time';
        const amountField = this.jiaofeiFieldMapping.pay_amount || 'cost';
        const modeField = this.jiaofeiFieldMapping.pay_mode || 'source';
        
        const payHistory = dataArray.map(item => ({
          time: item[dateField],
          cost: parseFloat(item[amountField]) || 0,
          source: item[modeField] || '其他'
        }));
        
        return payHistory;
      }
      
      // 没有配置缴费实体，返回空数组
      return [];
    } catch (error) {
      throw error;
    }
  }

  // 渲染缴费历史
  renderPayHistory(payHistory) {
    // 清空内容
    this.payHistoryBodyEl.innerHTML = '';

    // 计算缴费总额和次数
    let totalCost = 0;
    let minDate = null;
    let maxDate = null;

    payHistory.forEach(item => {
      totalCost += item.cost || 0;

      // 计算日期范围
      if (item.time) {
        const date = new Date(item.time);
        if (!minDate || date < minDate) {
          minDate = date;
        }
        if (!maxDate || date > maxDate) {
          maxDate = date;
        }
      }
    });
    const totalCount = payHistory.length;

    // 更新模态框标题，显示起止时间
    if (minDate && maxDate) {
      const formatDate = (date) => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
      };
      this.payHistoryTitleEl.textContent = `缴费历史（${formatDate(minDate)} 到 ${formatDate(maxDate)}）`;
    }

    // 创建顶部容器
    const topSection = document.createElement('div');
    topSection.className = 'pay-history-top-section';

    // 创建摘要区域
    const summaryDiv = document.createElement('div');
    summaryDiv.className = 'pay-history-summary';
    summaryDiv.innerHTML = `
      <div class="pay-history-item">
        <div class="pay-history-label">缴费总额</div>
        <div class="pay-history-value">${totalCost.toFixed(1)}</div>
      </div>
      <div class="pay-history-item">
        <div class="pay-history-label">缴费次数</div>
        <div class="pay-history-value">${totalCount}</div>
      </div>
    `;
    topSection.appendChild(summaryDiv);

    // 创建缴费类型饼图
    const paySourceData = {};
    payHistory.forEach(item => {
      const source = item.source || '未知';
      if (!paySourceData[source]) {
        paySourceData[source] = 0;
      }
      paySourceData[source] += item.cost || 0;
    });

    // 按金额排序
    const sortedSources = Object.entries(paySourceData).sort((a, b) => b[1] - a[1]);

    // 定义颜色映射：支付宝蓝色、微信绿色、其他（不用红色）
    const sourceColorMap = {
      '支付宝': '#1677FF',
      '微信': '#52C41A',
      '网上国网': '#14806E',
      '电e宝': '#e5abbe',
      '社会网点': '#FA8C16',
      '银行卡': '#9C27B0',
      '其他': '#8C8C8C',
      'default': '#13C2C2'
    };

    // 为每个缴费类型分配颜色
    const colors = sortedSources.map(item => {
      const source = item[0];
      // 检查缴费类型
      if (source.includes('支付宝') || source.includes('alipay') || source.includes('Alipay')) {
        return sourceColorMap['支付宝'];
      }
      if (source.includes('微信') || source.includes('WeChat') || source.includes('wechat')) {
        return sourceColorMap['微信'];
      }
      if (source.includes('网上国网交费') || source.includes('国网') || source.includes('sgcc')) {
        return sourceColorMap['网上国网'];
      }
      if (source.includes('电e宝') || source.includes('e宝')) {
        return sourceColorMap['电e宝'];
      }
      if (source.includes('社会网点') || source.includes('网点')) {
        return sourceColorMap['社会网点'];
      }
      if (source.includes('银行卡') || source.includes('银行')) {
        return sourceColorMap['银行卡'];
      }
      if (source.includes('其他')) {
        return sourceColorMap['其他'];
      }
      return sourceColorMap['default'];
    });

    const pieChartSection = document.createElement('div');
    pieChartSection.className = 'pay-history-pie-chart-section';

    const pieChartTitle = document.createElement('div');
    pieChartTitle.className = 'pie-chart-title';
    pieChartTitle.textContent = '缴费方式';
    pieChartSection.appendChild(pieChartTitle);

    const pieChartContent = document.createElement('div');
    pieChartContent.className = 'pie-chart-content';

    const pieChartContainer = document.createElement('div');
    pieChartContainer.className = 'pie-chart-container';
    pieChartContainer.id = 'pay-source-pie-chart';
    pieChartContent.appendChild(pieChartContainer);

    pieChartSection.appendChild(pieChartContent);
    topSection.appendChild(pieChartSection);
    this.payHistoryBodyEl.appendChild(topSection);

    // 渲染饼图
    this.renderPaySourcePieChart(pieChartContainer, sortedSources, colors);

    // 创建缴费历史列表
    const listDiv = document.createElement('div');
    listDiv.className = 'pay-history-list';

    // 按时间倒序排列（最新的在前面）
    const sortedHistory = [...payHistory].sort((a, b) => {
      return new Date(b.time) - new Date(a.time);
    });

    sortedHistory.forEach(item => {
      // 根据缴费类型确定CSS类
      const source = item.source || '';
      let sourceClass = 'default';
      if (source.includes('支付宝') || source.includes('alipay') || source.includes('Alipay')) {
        sourceClass = 'alipay';
      } else if (source.includes('微信') || source.includes('WeChat') || source.includes('wechat')) {
        sourceClass = 'wechat';
      } else if (source.includes('网上国网交费') || source.includes('国网') || source.includes('sgcc')) {
        sourceClass = 'sgcc-online';
      } else if (source.includes('电e宝') || source.includes('e宝')) {
        sourceClass = 'eebao';
      } else if (source.includes('社会网点') || source.includes('网点')) {
        sourceClass = 'outlet';
      } else if (source.includes('银行卡') || source.includes('银行')) {
        sourceClass = 'bank';
      } else if (source.includes('其他')) {
        sourceClass = 'other';
      }

      const recordDiv = document.createElement('div');
      recordDiv.className = 'pay-record';
      recordDiv.innerHTML = `
        <div class="pay-record-left">
          <div class="pay-record-time">${item.time || ''}</div>
          <div class="pay-record-source ${sourceClass}">${item.source || ''}</div>
        </div>
        <div class="pay-record-cost">${(item.cost || 0).toFixed(2)}</div>
      `;
      listDiv.appendChild(recordDiv);
    });

    this.payHistoryBodyEl.appendChild(listDiv);
  }

  // 渲染缴费方式饼图
  renderPaySourcePieChart(container, sortedSources, colors) {
    // 销毁之前的图表实例
    if (this.paySourceChart) {
      this.paySourceChart.dispose();
      this.paySourceChart = null;
    }
    
    // 检查ECharts是否可用
    if (typeof echarts === 'undefined') {
      return;
    }
    
    this.paySourceChart = echarts.init(container, null, { width: 240, height: 140 });
    
    const data = sortedSources.map((item, index) => ({
      value: item[1],
      name: item[0],
      itemStyle: { color: colors[index % colors.length] },
      label: { color: colors[index % colors.length] }
    }));

    const option = {
      tooltip: {
        trigger: 'item',
        textStyle: {
          fontSize: 10
        },
        formatter: function(params) {
          return params.name + '：<br/>' + 
                 '¥' + params.value.toFixed(2) + '<br/>' + 
                 params.percent + '%';
        }
      },

      series: [
        {
          type: 'pie',
          radius: ['25%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 4,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: true,
            formatter: function(params) {
              return params.name + '\n¥' + params.value.toFixed(2);
            },
            fontSize: 10,
            color: 'var(--text-color)'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 11,
              fontWeight: 'bold'
            },
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          },
          data: data
        }
      ]
    };

    this.paySourceChart.setOption(option);
  }

  // 渲染设备轨道
  async renderDeviceTracks(dateStr) {
    if (!this._hass || !this.deviceEntityConfig) {
      return;
    }

    // 创建标题和按钮容器（始终显示）
    const headerContainer = document.createElement('div');
    headerContainer.id = 'timeline-header-container';
    headerContainer.style.display = 'flex';
    headerContainer.style.justifyContent = 'space-between';
    headerContainer.style.alignItems = 'center';
    headerContainer.style.marginBottom = '10px';
    
    // 添加标题
    const timelineTitle = document.createElement('div');
    timelineTitle.style.textAlign = 'center';
    timelineTitle.style.fontSize = '14px';
    timelineTitle.style.fontWeight = '600';
    timelineTitle.style.color = 'var(--text-color)';
    timelineTitle.style.flex = '1';
    timelineTitle.textContent = '设备运行详情';
    headerContainer.appendChild(timelineTitle);
    
    // 添加切换按钮
    const toggleButton = document.createElement('button');
    toggleButton.id = 'sankey-toggle-btn';
    toggleButton.textContent = '桑基图';
    toggleButton.style.padding = '2px 8px';
    toggleButton.style.fontSize = '11px';
    toggleButton.style.border = '1px solid var(--button-color)';
    toggleButton.style.borderRadius = '4px';
    toggleButton.style.background = 'var(--card-button-bg)';
    toggleButton.style.color = 'var(--text-color)';
    toggleButton.style.cursor = 'pointer';
    toggleButton.style.transition = 'all 0.2s';
    toggleButton.style.marginLeft = '10px';
    toggleButton.style.whiteSpace = 'nowrap';
    
    // 添加悬停效果
    toggleButton.addEventListener('mouseenter', () => {
      toggleButton.style.background = 'var(--button-primary-transparent)';
      toggleButton.style.borderColor = 'var(--button-color-active)';
    });
    
    toggleButton.addEventListener('mouseleave', () => {
      if (!this.showSankeyChart) {
        toggleButton.style.background = 'var(--card-button-bg)';
        toggleButton.style.borderColor = 'var(--button-color)';
      }
    });
    
    // 添加点击事件
    toggleButton.addEventListener('click', () => {
      this.showSankeyChart = !this.showSankeyChart;
      this.toggleTimelineContent(this.showSankeyChart);
      
      // 更新按钮样式和文本
      if (this.showSankeyChart) {
        // 当前显示桑基图，按钮应显示"时间轴"（点击后切换到时间轴）
        toggleButton.style.background = 'var(--button-color-active)';
        toggleButton.style.color = 'var(--card-bg)';
        toggleButton.style.borderColor = 'var(--button-color-active)';
        toggleButton.textContent = '时间轴';
      } else {
        // 当前显示时间轴，按钮应显示"桑基图"（点击后切换到桑基图）
        toggleButton.style.background = 'var(--card-button-bg)';
        toggleButton.style.color = 'var(--text-color)';
        toggleButton.style.borderColor = 'var(--button-color)';
        toggleButton.textContent = '桑基图';
      }
    });
    
    headerContainer.appendChild(toggleButton);
    this.dayModalBodyEl.appendChild(headerContainer);

    // 创建时间轴容器（只包含设备轨道）
    const timelineContainer = document.createElement('div');
    timelineContainer.id = 'timeline-container';
    
    // 创建设备轨道容器
    const deviceTracksContainer = document.createElement('div');
    deviceTracksContainer.id = 'device-tracks-container';
    timelineContainer.appendChild(deviceTracksContainer);
    
    // 创建时间标签容器
    const timelineAligner = document.createElement('div');
    timelineAligner.className = 'timeline-aligner';
    timelineAligner.innerHTML = `
      <div class="timeline-aligner-spacer"></div>
      <div class="timeline-aligner-spacer-2"></div>
      <div class="time-labels timeline-aligner-content">
        <span>00:00</span>
        <span>08:00</span>
        <span>16:00</span>
        <span>24:00</span>
      </div>
    `;
    timelineContainer.appendChild(timelineAligner);
    
    // 创建合计行容器
    const totalRowContainer = document.createElement('div');
    totalRowContainer.id = 'total-row-container';
    timelineContainer.appendChild(totalRowContainer);
    
    // 添加到模态框
    this.dayModalBodyEl.appendChild(timelineContainer);
    
    // 创建桑基图容器（默认隐藏）
    const sankeyContainer = document.createElement('div');
    sankeyContainer.id = 'sankey-chart-container';
    sankeyContainer.style.display = 'none';
    sankeyContainer.style.marginTop = '10px';
    sankeyContainer.style.background = 'var(--card-button-bg)';
    sankeyContainer.style.borderRadius = '8px';
    sankeyContainer.style.padding = '10px';
    sankeyContainer.style.height = '400px';
    this.dayModalBodyEl.appendChild(sankeyContainer);

    // 获取设备数据并渲染轨道
    await this.fetchDeviceEvents(dateStr);

    // 如果没有设备运行数据，隐藏整个 timeline-container 和 header
    if (!this.deviceEvents || this.deviceEvents.length === 0) {
      timelineContainer.style.display = 'none';
      headerContainer.style.display = 'none';
    } else {
      this.initializeTracks();
    }

    // 应用隐藏配置
    this.applyHiddenConfig();
  }


  // 获取设备事件
  async fetchDeviceEvents(dateStr) {
    // 确保日期格式正确（YYYY-MM-DD）
    const dateMatch = dateStr.match(/(\d{4})-(\d{1,2})-(\d{1,2})/);
    if (!dateMatch) {
      return [];
    }
    
    const year = dateMatch[1];
    const month = String(dateMatch[2]).padStart(2, '0');
    const day = String(dateMatch[3]).padStart(2, '0');
    const formattedDateStr = `${year}-${month}-${day}`;
    
    const startOfDay = new Date(`${formattedDateStr}T00:00:00`);
    const endOfDay = new Date(`${formattedDateStr}T23:59:59`);

    
    const events = [];
    if (!this.deviceEntityConfig) return events;

    const promises = this.deviceEntityConfig.map(async (deviceConfig) => {
      const entityId = deviceConfig.entity;
      try {
        const history = await this.getHistory(entityId, startOfDay, endOfDay);
        if (history && history.length > 0) {
          const deviceEvents = this.processEntityHistory(entityId, deviceConfig, history);
          events.push(...deviceEvents);
        }
      } catch (error) {
        // Silently fail
      }
    });

    await Promise.all(promises);
    this.deviceEvents = events;
    return events;
  }

  // 获取历史数据
  async   getHistory(entityId, startTime, endTime) {
    return new Promise((resolve, reject) => {
      if (!this._hass) {
        resolve([]); 
        return;
      }

      // 检查日期对象是否有效
      if (!startTime || !endTime || isNaN(startTime.getTime()) || isNaN(endTime.getTime())) {
        resolve([]);
        return;
      }

      this._hass.connection.sendMessagePromise({
        type: 'history/history_during_period',
        start_time: startTime.toISOString(),
        end_time: endTime.toISOString(),
        entity_ids: [entityId],
        include_start_time_state: true,
        minimal_response: true,
        no_attributes: true
      }).then(response => {
        resolve(response[entityId] || []);
      }).catch(error => {
        resolve([]);
      });
    });
  }

  // 从历史状态对象中获取状态值（兼容不同版本的Home Assistant）
  getStateValue(stateObj) {
    if (!stateObj) return null;
    
    // Home Assistant不同版本返回格式不同
    // 有些版本使用'state'属性，有些使用's'属性
    const stateValue = stateObj.state !== undefined ? stateObj.state : stateObj.s;
    return stateValue;
  }

  // 处理实体历史数据
  processEntityHistory(entityId, entityConfig, history) {
    const events = [];
    let currentEvent = null;
    
    history.sort((a, b) => a.lu - b.lu);

    // 获取当前设备的实时状态
    const currentState = this.getCurrentEntityState(entityId);
    const isCurrentlyOn = this.isEntityOn(currentState, entityConfig);
    
    for (let i = 0; i < history.length; i++) {
      const stateObj = history[i];
      const stateValue = stateObj.s;
      const timestampValue = stateObj.lu;
      
      const isOn = this.isEntityOn(stateValue, entityConfig);
      const timestamp = new Date(timestampValue * 1000);
      const timeStr = this.formatTime(timestamp);

      if (isOn) {
        if (!currentEvent) {
          currentEvent = {
            device: entityConfig.name || entityId,
            start: timeStr,
            start_timestamp: timestamp,
            entity_id: entityId,
            config: entityConfig
          };
        }
      } else {
        if (currentEvent) {
          currentEvent.end = timeStr;
          currentEvent.end_timestamp = timestamp;
          events.push(currentEvent);
          currentEvent = null;
        }
      }
    }

    if (currentEvent) {
      // 只有当设备在当前日期（不是历史日期）且正在运行时才标记为进行中
      const today = new Date();
      const isToday = currentEvent.start_timestamp.getDate() === today.getDate() && 
                     currentEvent.start_timestamp.getMonth() === today.getMonth() && 
                     currentEvent.start_timestamp.getFullYear() === today.getFullYear();
      
      if (isToday && isCurrentlyOn) {
        // 检查是否跨越午夜
        const startOfDay = new Date(today);
        startOfDay.setHours(0, 0, 0, 0);
        
        if (currentEvent.start_timestamp < startOfDay) {
          // 设备在00:00:00前开启，跨越午夜后还没关闭
          // 使用00:00:00作为开启时间，当前时间作为结束时间
          currentEvent.start_timestamp = new Date(startOfDay);
          currentEvent.start = "00:00";
        }
        
        currentEvent.isOngoing = true;
        currentEvent.end = null;
        currentEvent.end_timestamp = null;
      } else {
        currentEvent.isOngoing = false;
        currentEvent.end = "23:59";
        // 使用历史数据的日期来设置结束时间，而不是今天的日期
        const endOfDayDate = new Date(currentEvent.start_timestamp);
        endOfDayDate.setHours(23, 59, 59, 999);
        currentEvent.end_timestamp = endOfDayDate;
      }
      events.push(currentEvent);
    }

    return events;
  }

  // 获取当前实体状态
  getCurrentEntityState(entityId) {
    if (!this._hass || !this._hass.states) return null;
    const stateObj = this._hass.states[entityId];
    return stateObj ? stateObj.state : null;
  }

  // 判断实体是否开启
  isEntityOn(state, entityConfig) {
    if (state === undefined || state === null) return false;
    
    if (entityConfig.on_state) {
      const onStates = entityConfig.on_state.split(',').map(s => s.trim());
      return onStates.includes(state);
    }
    
    if (entityConfig.entity.includes('input_boolean')) return state === 'on';
    
    const onStates = ['on', 'open', 'true', 'home', 'active', 'playing', 'cooling', 'heating'];
    const offStates = ['off', 'closed', 'false', 'away', 'idle', 'paused', 'unavailable', 'unknown'];
    
    const stateLower = String(state).toLowerCase();
    
    if (onStates.includes(stateLower)) return true;
    if (offStates.includes(stateLower)) return false;
    
    if (!isNaN(state) && state !== '') return parseFloat(state) > 0;
    
    return !offStates.includes(stateLower);
  }

  // 初始化轨道
  // 处理轨道点击事件
  handleTrackClick(e, deviceName) {
    if (!this.eventTooltip) return;

    const trackWrapper = e.target.closest('.track-bar-wrapper');
    if (!trackWrapper) {
      this.hideTooltip();
      return;
    }

    const trackBounds = trackWrapper.getBoundingClientRect();
    const clickX = e.clientX;
    
    const clickOffset = clickX - trackBounds.left;
    const trackWidth = trackBounds.width;
    const clickRatio = Math.max(0, Math.min(1, clickOffset / trackWidth));
    const newTimeSeconds = Math.round(clickRatio * 86400 / 60) * 60; 

    const events = this.deviceEvents.filter(ev => ev.device === deviceName);
    
    this.showDetailedTooltip(e, deviceName, events, trackBounds, clickX, clickRatio, newTimeSeconds);
    e.stopPropagation();
  }

  // 显示详细提示框
  showDetailedTooltip(e, deviceName, events, trackBounds, clickX, clickRatio, newTimeSeconds) {
    if (!this.eventTooltip) return;
    
    e.preventDefault();

    // 清理之前的正在运行事件定时器
    this.clearOngoingEventTimers();

    // 确保主题变量已应用到 document.documentElement（供 tooltip 使用）
    if (this.lastThemeName && document.documentElement) {
      const theme = ElectricityInfoCard.COLOR_SCHEMES[this.lastThemeName] || ElectricityInfoCard.COLOR_SCHEMES.light;
      Object.keys(theme).forEach(key => {
        document.documentElement.style.setProperty(key, theme[key]);
      });
    }

    // 先将 tooltip 移出视野外
    this.eventTooltip.style.display = 'block';
    this.eventTooltip.style.left = '-1000px';
    this.eventTooltip.style.top = '-1000px';

    // 计算总时长
    let totalDurationSeconds = 0;
    events.forEach(event => {
      const startSec = this.timeToSeconds(event.start);
      let endSec;
      
      // 如果是正在运行的事件，使用当前时间计算时长
      if (event.isOngoing) {
        const now = new Date();
        endSec = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
      } else {
        endSec = event.end ? this.timeToSeconds(event.end) : 86400;
      }
      
      if (endSec < startSec) {
        totalDurationSeconds += (86400 - startSec) + endSec;
      } else {
        totalDurationSeconds += Math.max(0, endSec - startSec);
      }
    });
    const totalDurationFormatted = this.formatDuration(totalDurationSeconds);
    
    this.tooltipDeviceName.textContent = `${deviceName} (${totalDurationFormatted})`;
    this.tooltipEventsList.innerHTML = '';
    
    const TOOLTIP_MIN_WIDTH = 160;
    const TOOLTIP_MAX_WIDTH = 200;
    const ARROW_SIZE = 7;
    const HORIZONTAL_CLEARANCE = 25;
    const MARGIN = 10;
    const TOOLTIP_MAX_HEIGHT = 150;
    
    let highlightedElement = null;
    
    if (events.length === 0) {
      const li = document.createElement('li');
      li.textContent = '本日无运行记录';
      this.tooltipEventsList.appendChild(li);
    } else {
      events.forEach(ev => {
        const li = document.createElement('li');
        const startSec = this.timeToSeconds(ev.start);
        let endSec;
        let endStr;
        
        // 如果是正在运行的事件，使用当前时间计算时长
        if (ev.isOngoing) {
          const now = new Date();
          endSec = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
          endStr = '正在运行';
          
          // 为正在运行的事件添加动画效果
          li.classList.add('on-going-event');
          
          // 添加实时更新的定时器
          this.startOngoingEventTimer(li, ev, startSec);
        } else {
          endSec = ev.end ? this.timeToSeconds(ev.end) : 86400;
          endStr = ev.end ? ev.end : '23:59';
        }
        
        let durationSeconds;
        if (endSec < startSec) {
          durationSeconds = (86400 - startSec) + endSec;
        } else {
          durationSeconds = Math.max(0, endSec - startSec);
        }
        
        const duration = this.formatDuration(durationSeconds);
        
        li.innerHTML = `[${ev.start} - ${endStr}] <span>(${duration})</span>`;
        
        // 检查点击时间是否在该事件内（使用10分钟容差）
        const TOLERANCE = 60 * 10;
        let isCurrentTimeInEvent = false;
        
        if (endSec < startSec) {
          if (newTimeSeconds >= startSec - TOLERANCE || newTimeSeconds <= endSec + TOLERANCE) {
            isCurrentTimeInEvent = true;
          }
        } else if (newTimeSeconds >= startSec - TOLERANCE && newTimeSeconds <= endSec + TOLERANCE) {
          isCurrentTimeInEvent = true;
        }
        
        if (isCurrentTimeInEvent) {
          li.classList.add('highlighted-event');
          highlightedElement = li;
        }
        
        this.tooltipEventsList.appendChild(li);
      });
    }

    // 获取tooltip的实际尺寸
    // 不再设置固定宽度，让tooltip自适应内容宽度
    this.eventTooltip.style.width = 'auto';
    const TOOLTIP_WIDTH = this.eventTooltip.offsetWidth;
    const TOOLTIP_HEIGHT = Math.min(this.eventTooltip.offsetHeight, TOOLTIP_MAX_HEIGHT);

    // 使用 fixed 定位，相对于视口，但计算时考虑滚动
    // 保存初始位置用于滚动时更新
    this.tooltipInitialTrackBounds = trackBounds;
    this.tooltipInitialClickX = clickX;
    this.tooltipInitialClickY = e.clientY;
    this.tooltipInitialClickRatio = clickRatio;
    this.tooltipInitialModalScrollTop = this.dayModalContentEl.scrollTop;
    this.tooltipInitialModalScrollLeft = this.dayModalContentEl.scrollLeft;

    // 保存 tooltip 垂直位置相对于 track 的偏移量
    // 这样滚动时可以保持 tooltip 在 track 的相同相对位置
    const trackCenterY = trackBounds.top + trackBounds.height / 2;
    this.tooltipOffsetFromTrackCenter = e.clientY - trackCenterY;

    const trackCenterX = trackBounds.left + trackBounds.width / 2;

    let targetLeft, targetTop;
    let arrowSide;

    if (clickX < trackCenterX) {
      arrowSide = 'left';
      targetLeft = clickX + HORIZONTAL_CLEARANCE;
    } else {
      arrowSide = 'right';
      const adjustment = 5;
      targetLeft = clickX - TOOLTIP_WIDTH - HORIZONTAL_CLEARANCE - adjustment;
    }

    // 关键修复：初始显示时也使用 track 的相对位置，并加上滚动偏移
    const scrollX = window.scrollX || window.pageXOffset;
    const scrollY = window.scrollY || window.pageYOffset;

    targetTop = trackCenterY + this.tooltipOffsetFromTrackCenter - (TOOLTIP_HEIGHT / 2) + scrollY;
    targetLeft = targetLeft + scrollX;

    // 确保tooltip不超出视口边界
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    targetTop = Math.max(scrollY + MARGIN, targetTop);
    targetTop = Math.min(scrollY + viewportHeight - TOOLTIP_HEIGHT - MARGIN, targetTop);
    targetLeft = Math.max(scrollX + MARGIN, targetLeft);
    targetLeft = Math.min(scrollX + viewportWidth - TOOLTIP_WIDTH - MARGIN, targetLeft);

    let arrowY = trackCenterY + this.tooltipOffsetFromTrackCenter - targetTop + scrollY;
    arrowY = Math.max(ARROW_SIZE, Math.min(TOOLTIP_HEIGHT - ARROW_SIZE, arrowY));

    this.eventTooltip.style.left = `${targetLeft}px`;
    this.eventTooltip.style.top = `${targetTop}px`;
    this.eventTooltip.style.width = `${TOOLTIP_WIDTH}px`;
    this.eventTooltip.style.maxHeight = `${TOOLTIP_MAX_HEIGHT}px`;
    this.eventTooltip.style.setProperty('--arrow-y', `${arrowY}px`);
    this.eventTooltip.dataset.arrow = arrowSide;
    this.eventTooltip.classList.add('active');

    // 添加滚动监听器，让 tooltip 跟随滚动
    this.addScrollListeners();
  }

  // 添加滚动监听器
  addScrollListeners() {
    if (!this.tooltipScrollHandler) {
      this.tooltipScrollHandler = () => {
        if (!this.eventTooltip || this.eventTooltip.style.display === 'none') return;

        // 重新计算 track 的位置（滚动后位置已改变）
        const trackWrapper = this.dayModalContentEl.querySelector('.track-bar-wrapper');
        if (!trackWrapper) return;

        const currentTrackBounds = trackWrapper.getBoundingClientRect();

        // 使用新的 track 位置，但保持与原始点击的相对关系
        const trackCenterX = currentTrackBounds.left + currentTrackBounds.width / 2;
        const trackCenterY = currentTrackBounds.top + currentTrackBounds.height / 2;
        const currentClickX = currentTrackBounds.left + this.tooltipInitialClickRatio * currentTrackBounds.width;

        const ARROW_SIZE = 7;
        const HORIZONTAL_CLEARANCE = 25;
        const MARGIN = 10;
        const TOOLTIP_MAX_HEIGHT = 150;

        // 不再设置固定宽度，让tooltip自适应内容宽度
        this.eventTooltip.style.width = 'auto';
        const TOOLTIP_WIDTH = this.eventTooltip.offsetWidth;
        const TOOLTIP_HEIGHT = Math.min(this.eventTooltip.offsetHeight, TOOLTIP_MAX_HEIGHT);

        let targetLeft, targetTop;
        let arrowSide;

        if (currentClickX < trackCenterX) {
          arrowSide = 'left';
          targetLeft = currentClickX + HORIZONTAL_CLEARANCE;
        } else {
          arrowSide = 'right';
          const adjustment = 5;
          targetLeft = currentClickX - TOOLTIP_WIDTH - HORIZONTAL_CLEARANCE - adjustment;
        }

        // 对于 absolute 定位，需要加上 window 的滚动偏移
        const scrollX = window.scrollX || window.pageXOffset;
        const scrollY = window.scrollY || window.pageYOffset;

        targetTop = trackCenterY + this.tooltipOffsetFromTrackCenter - (TOOLTIP_HEIGHT / 2) + scrollY;
        targetLeft = targetLeft + scrollX;

        // 计算箭头位置（箭头应该指向 track 中心）
        let arrowY = trackCenterY - targetTop + scrollY;
        arrowY = Math.max(ARROW_SIZE, Math.min(TOOLTIP_HEIGHT - ARROW_SIZE, arrowY));

        this.eventTooltip.style.left = `${targetLeft}px`;
        this.eventTooltip.style.top = `${targetTop}px`;
        this.eventTooltip.style.setProperty('--arrow-y', `${arrowY}px`);
        this.eventTooltip.dataset.arrow = arrowSide;
      };

      // 监听 window 的滚动事件
      window.addEventListener('scroll', this.tooltipScrollHandler);
    }
  }

  // 隐藏提示框
  hideTooltip() {
    if (this.eventTooltip) {
      this.eventTooltip.style.display = 'none';
      this.eventTooltip.classList.remove('active');
    }
    // 移除滚动监听器
    if (this.tooltipScrollHandler) {
      window.removeEventListener('scroll', this.tooltipScrollHandler);
      this.tooltipScrollHandler = null;
    }
    // 清理正在运行事件的定时器
    this.clearOngoingEventTimers();
  }

  // 格式化时长 - 统一显示为x.xh格式
  formatDuration(totalSeconds) {
    if (totalSeconds < 60) return `${(totalSeconds / 3600).toFixed(1)}h`;
    
    const hours = totalSeconds / 3600;
    return `${hours.toFixed(1)}h`;
  }

  // 为正在运行的事件启动定时器
  startOngoingEventTimer(liElement, event, startSec) {
    // 清除之前的定时器
    if (liElement.ongoingTimer) {
      clearInterval(liElement.ongoingTimer);
    }
    
    // 每秒更新一次时长
    liElement.ongoingTimer = setInterval(() => {
      const now = new Date();
      const currentSeconds = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
      
      let durationSeconds;
      if (currentSeconds < startSec) {
        durationSeconds = (86400 - startSec) + currentSeconds;
      } else {
        durationSeconds = Math.max(0, currentSeconds - startSec);
      }
      
      const duration = this.formatDuration(durationSeconds);
      
      // 更新显示内容
      const span = liElement.querySelector('span');
      if (span) {
        span.textContent = `(${duration})`;
      }
    }, 1000);
    
    // 保存定时器引用以便清理
    this.ongoingEventTimers = this.ongoingEventTimers || [];
    this.ongoingEventTimers.push(liElement.ongoingTimer);
  }

  // 清理正在运行事件的定时器
  clearOngoingEventTimers() {
    if (this.ongoingEventTimers) {
      this.ongoingEventTimers.forEach(timer => clearInterval(timer));
      this.ongoingEventTimers = [];
    }
  }

  async initializeTracks() {
    const deviceTracksContainer = this.dayModalBodyEl.querySelector('#device-tracks-container');
    if (!deviceTracksContainer) return;
    
    deviceTracksContainer.innerHTML = '';
    
    const activeDeviceNames = new Set(this.deviceEvents.map(event => event.device));
    
    if (activeDeviceNames.size === 0) {
      deviceTracksContainer.innerHTML = `<div style="text-align:center; padding:10px; color:#999; font-size:12px;">没有找到设备事件记录</div>`;
      return;
    }

    // 获取当前日期
    const currentDate = this.dayModalTitleEl.textContent.match(/\d{4}年\d{1,2}月\d{1,2}日/);
    if (!currentDate) return;
    
    // 解析日期并确保月份和日期是两位数
    const dateMatch = currentDate[0].match(/(\d{4})年(\d{1,2})月(\d{1,2})日/);
    if (!dateMatch) return;
    
    const year = dateMatch[1];
    const month = String(dateMatch[2]).padStart(2, '0');
    const day = String(dateMatch[3]).padStart(2, '0');
    const dateStr = `${year}-${month}-${day}`;
    
    const startOfDay = new Date(`${dateStr}T00:00:00`);
    const endOfDay = new Date(`${dateStr}T23:59:59`);
    
    // 初始化设备轨道数据
    this.deviceTracks = [];

    // 调试信息



    // 为每个设备创建轨道
    for (const deviceName of Array.from(activeDeviceNames).sort((a, b) => a.localeCompare(b, 'zh-CN'))) {
      const trackDiv = document.createElement('div');
      trackDiv.className = 'device-track';
      
      const labelSpan = document.createElement('span');
      labelSpan.className = 'device-label';
      labelSpan.textContent = deviceName;
      
      // 创建用电量和使用时长的容器
      const powerUsageContainer = document.createElement('div');
      powerUsageContainer.className = 'power-usage-container';
      
      // 用电量显示元素
      const powerUsageSpan = document.createElement('span');
      
      // 使用时长显示元素
      const usageDurationSpan = document.createElement('span');
      usageDurationSpan.className = 'usage-duration';
      
      // 查找设备配置
      const deviceConfig = this.deviceEntityConfig?.find(config => config.name === deviceName);
      let powerUsage = null;
      let usageDuration = null;
      let isEstimate = false; // 标记是否为估算值
      
      // 调试信息

      
      // 如果有power_entity，查询用电量数据，使用最大值减去最小值计算
      if (deviceConfig && deviceConfig.power_entity) {

        try {
          // 判断是否为当日
          const now = new Date();
          const isToday = startOfDay.toDateString() === new Date(now.getFullYear(), now.getMonth(), now.getDate()).toDateString();
          
          // 如果是当日，查询到当前时间；否则查询到23:59:59
          const queryEndTime = isToday ? now : endOfDay;
          const history = await this.getHistory(deviceConfig.power_entity, startOfDay, queryEndTime);

          if (history && history.length >= 1) {
            // 收集所有有效的状态值
            const validValues = [];
            
            for (const state of history) {
              const stateValue = this.getStateValue(state);
              if (stateValue !== null && stateValue !== undefined && stateValue !== 'unavailable') {
                const value = parseFloat(stateValue);
                if (!isNaN(value)) {
                  validValues.push(value);
                }
              }
            }
            
            if (validValues.length > 0) {
              // 计算最大值和最小值
              const maxValue = Math.max(...validValues);
              const minValue = Math.min(...validValues);
              
              // 计算用电量 = 最大值 - 最小值
              const dailyUsage = maxValue - minValue;
              if (dailyUsage >= 0) {
                powerUsage = dailyUsage.toFixed(2);
                // 实际测量值，使用 power-usage 类
                powerUsageSpan.className = 'power-usage';
              } else {
                powerUsage = '0.00';
                powerUsageSpan.className = 'power-usage';
              }
            } else {
              powerUsageSpan.className = 'power-usage';
            }
          } else {
            powerUsageSpan.className = 'power-usage';
          }
        } catch (error) {
          powerUsageSpan.className = 'power-usage';
        }
      } else if (deviceConfig && deviceConfig.power) {
        // 如果有power配置，使用功率乘以使用时长计算用电量
        const powerValue = parseFloat(deviceConfig.power);
        if (!isNaN(powerValue) && powerValue > 0) {
          // 计算使用时长（从设备事件中获取）
          const deviceEventsForTrack = this.deviceEvents.filter(event => event.device === deviceName);
          if (deviceEventsForTrack.length > 0) {
            let totalSeconds = 0;
            deviceEventsForTrack.forEach(event => {
              const startSec = this.timeToSeconds(event.start);
              
              // 对于正在运行的事件，使用当前时间作为结束时间
              let endSec;
              if (event.isOngoing) {
                const now = new Date();
                const currentSeconds = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
                endSec = currentSeconds;
              } else {
                endSec = event.end ? this.timeToSeconds(event.end) : 86400;
              }
              
              // 处理跨越午夜的情况
              if (endSec < startSec) {
                totalSeconds += (86400 - startSec) + endSec;
              } else {
                totalSeconds += Math.max(0, endSec - startSec);
              }
            });
            
            // 计算用电量：功率 × 时长（小时）÷ 1000
            const totalHours = totalSeconds / 3600;
            const calculatedUsage = (powerValue * totalHours) / 1000;
            powerUsage = calculatedUsage.toFixed(2);
            
            // 估算值，使用 power-usage-estimate 类
            powerUsageSpan.className = 'power-usage-estimate';
            isEstimate = true;
          }
        }
      } else {
        // 默认使用 power-usage 类
        powerUsage = '0.00';
        powerUsageSpan.className = 'power-usage';
      }
      
      // 计算使用时长（从设备事件中获取）
      const deviceEventsForTrack = this.deviceEvents.filter(event => event.device === deviceName);
      if (deviceEventsForTrack.length > 0) {
        let totalSeconds = 0;
        deviceEventsForTrack.forEach(event => {
          const startSec = this.timeToSeconds(event.start);
          
          // 对于正在运行的事件，使用当前时间作为结束时间
          let endSec;
          if (event.isOngoing) {
            const now = new Date();
            const currentSeconds = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
            endSec = currentSeconds;
          } else {
            endSec = event.end ? this.timeToSeconds(event.end) : 86400;
          }
          
          // 处理跨越午夜的情况
          if (endSec < startSec) {
            totalSeconds += (86400 - startSec) + endSec;
          } else {
            totalSeconds += Math.max(0, endSec - startSec);
          }
        });
        usageDuration = this.formatDuration(totalSeconds);


      }
      
      // 获取单位（从统一数据格式中获取）
      const usageUnit = this.standardData.unit || '';
      powerUsageSpan.textContent = powerUsage !== null ? `${powerUsage}${usageUnit}` : '';
      usageDurationSpan.textContent = usageDuration !== null ? usageDuration : '';
      
      // 将用电量和时长添加到容器中
      powerUsageContainer.appendChild(powerUsageSpan);
      powerUsageContainer.appendChild(usageDurationSpan);
      
      // 保存设备轨道数据
      if (powerUsage !== null) {
        this.deviceTracks.push({
          device: deviceName,
          powerUsage: powerUsage,
          usageDuration: usageDuration,
          isEstimate: isEstimate
        });
      }
      
      const barWrapperDiv = document.createElement('div');
      barWrapperDiv.className = 'track-bar-wrapper';
      barWrapperDiv.dataset.device = deviceName;
      barWrapperDiv.style.cursor = 'pointer';
      
      // 添加点击事件监听器
      barWrapperDiv.addEventListener('click', (e) => this.handleTrackClick(e, deviceName));
      
      const barDiv = document.createElement('div');
      barDiv.className = 'track-bar';
      
      barWrapperDiv.appendChild(barDiv);
      trackDiv.appendChild(labelSpan);
      trackDiv.appendChild(powerUsageContainer);
      trackDiv.appendChild(barWrapperDiv);
      deviceTracksContainer.appendChild(trackDiv);

      // 为轨道添加事件块
      deviceEventsForTrack.forEach(event => {
        const startSec = this.timeToSeconds(event.start);
        
        // 如果是正在运行的事件，使用当前时间作为结束时间
        let endSec;
        if (event.isOngoing) {
          const now = new Date();
          const currentSeconds = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
          endSec = currentSeconds;
        } else {
          endSec = event.end ? this.timeToSeconds(event.end) : 86400;
        }
        
        const left = (startSec / 86400) * 100;
        const fill = document.createElement("div");
        fill.className = `track-fill`;
        
        // 如果是正在运行的事件，添加on-going类
        if (event.isOngoing) {
          fill.classList.add('on-going');
        }
        
        // 获取设备颜色
        const color = this.getDeviceColor(deviceName);
        fill.style.backgroundColor = color;
        fill.style.left = `${left}%`;
        
        const durationSec = endSec - startSec;
        
        if (durationSec < 300) {
          fill.style.width = "4px";
        } else {
          const width = (durationSec / 86400) * 100;
          fill.style.width = `${width}%`;
        }
        
        barDiv.appendChild(fill);
      });
    }

    // 创建合计行
    this.createTotalRow(activeDeviceNames);
  }

  // 创建合计行
  createTotalRow(activeDeviceNames) {
    const totalRowContainer = this.dayModalBodyEl.querySelector('#total-row-container');
    if (!totalRowContainer) return;

    totalRowContainer.innerHTML = '';

    // 格式化时长为中文格式（xx小时xx分钟）
    const formatDurationChinese = (totalSeconds) => {
      if (totalSeconds < 60) return `${Math.round(totalSeconds)}秒`;
      
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      
      if (hours > 0) {
        if (minutes > 0) {
          return `${hours}小时${minutes}分钟`;
        } else {
          return `${hours}小时`;
        }
      } else {
        return `${minutes}分钟`;
      }
    };

    // 计算合计数据
    let totalDeviceCount = 0;
    let totalPowerUsage = 0;
    let totalDurationSeconds = 0;

    // 遍历所有活跃设备
    for (const deviceName of Array.from(activeDeviceNames)) {
      // 查找设备配置
      const deviceConfig = this.deviceEntityConfig?.find(config => config.name === deviceName);
      if (!deviceConfig) continue;

      totalDeviceCount++;

      // 获取设备用电量
      const deviceEventsForTrack = this.deviceEvents.filter(event => event.device === deviceName);
      let devicePowerUsage = 0;
      let deviceDurationSeconds = 0;

      // 计算设备使用时长
      deviceEventsForTrack.forEach(event => {
        const startSec = this.timeToSeconds(event.start);
        
        // 对于正在运行的事件，使用当前时间作为结束时间
        let endSec;
        if (event.isOngoing) {
          const now = new Date();
          const currentSeconds = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
          endSec = currentSeconds;
        } else {
          endSec = event.end ? this.timeToSeconds(event.end) : 86400;
        }
        
        // 处理跨越午夜的情况
        if (endSec < startSec) {
          deviceDurationSeconds += (86400 - startSec) + endSec;
        } else {
          deviceDurationSeconds += Math.max(0, endSec - startSec);
        }
      });

      totalDurationSeconds += deviceDurationSeconds;

      // 使用设备轨道中已经计算好的用电量（包括实际值和估算值）
      const deviceTrack = this.deviceTracks?.find(track => track.device === deviceName);
      if (deviceTrack && deviceTrack.powerUsage !== null) {
        // 使用设备轨道中已经计算好的用电量
        devicePowerUsage = parseFloat(deviceTrack.powerUsage) || 0;
      } else {
        // 如果找不到设备轨道数据，使用功率估算作为备用方案
        const powerValue = parseFloat(deviceConfig.power) || 0;
        if (powerValue > 0) {
          const totalHours = deviceDurationSeconds / 3600;
          devicePowerUsage = (powerValue * totalHours) / 1000;
        }
      }

      totalPowerUsage += devicePowerUsage;
    }

    // 格式化时长 - 使用专门的格式显示"xx小时xx分钟"
    const totalDurationFormatted = formatDurationChinese(totalDurationSeconds);

    // 创建合计行
    const totalRow = document.createElement('div');
    totalRow.className = 'total-row';

    // 设备数量
    const totalLabel = document.createElement('span');
    totalLabel.className = 'total-label';
    totalLabel.textContent = `${totalDeviceCount}个设备`;

    // 用电量合计
    const totalPowerSpan = document.createElement('span');
    totalPowerSpan.className = 'total-value';
    const usageUnit = this.standardData.unit || '';
    totalPowerSpan.textContent = `${totalPowerUsage.toFixed(2)}${usageUnit}`;

    // 使用时长合计
    const totalDurationSpan = document.createElement('span');
    totalDurationSpan.className = 'total-value';
    totalDurationSpan.textContent = totalDurationFormatted;

    // 创建空的轨道占位符
    const trackPlaceholder = document.createElement('div');
    trackPlaceholder.style.flexGrow = '1';

    totalRow.appendChild(totalLabel);
    totalRow.appendChild(totalPowerSpan);
    totalRow.appendChild(totalDurationSpan);
    totalRow.appendChild(trackPlaceholder);

    totalRowContainer.appendChild(totalRow);
    
    // 提取设备数据供其他函数使用
    this.extractDeviceData();
  }
  
  // 提取设备数据供其他函数使用
  extractDeviceData() {
    if (!this.deviceTracks || this.deviceTracks.length === 0) {
      this.dayDeviceData = null;
      return;
    }
    
    const deviceData = [];
    const roomMap = new Map(); // 用于按房间聚合
    let totalPowerUsage = 0; // 总用电量
    
    for (const track of this.deviceTracks) {
      const deviceName = track.device;
      const powerUsage = track.powerUsage;
      const usageDuration = track.usageDuration;
      
      // 从deviceName中提取房间和设备名称
      // 格式：房间-设备名称（如：客厅-灯、厨房-油烟机）
      let room = '';
      let device = deviceName;
      
      const separatorIndex = deviceName.indexOf('-');
      if (separatorIndex > -1) {
        room = deviceName.substring(0, separatorIndex);
        device = deviceName.substring(separatorIndex + 1);
      }
      
      // 将数据添加到数组
      deviceData.push({
        room: room,
        deviceName: device,
        fullName: deviceName,
        powerUsage: powerUsage,
        usageDuration: usageDuration
      });
      
      // 按房间聚合使用时长和用电量
      if (room) {
        const durationSeconds = this.durationToSeconds(usageDuration);
        const powerValue = parseFloat(powerUsage) || 0;
        
        if (roomMap.has(room)) {
          const existing = roomMap.get(room);
          existing.usageDuration += durationSeconds;
          existing.powerUsage += powerValue;
          roomMap.set(room, existing);
        } else {
          roomMap.set(room, {
            usageDuration: durationSeconds,
            powerUsage: powerValue
          });
        }
      }
      
      // 累加总用电量（去除单位）
      const powerValue = parseFloat(powerUsage) || 0;
      totalPowerUsage += powerValue;
    }
    
    // 1. 存储设备详细数据
    const result = {
      devices: deviceData,
      roomAggregation: [],
      dayConsumption: null
    };
    
    // 2. 按房间聚合数据（包含usageDuration、powerUsage，其中usageDuration转换为秒）
    for (const [room, data] of roomMap.entries()) {
      result.roomAggregation.push({
        room: room,
        usageDuration: data.usageDuration, // 以秒为单位
        powerUsage: data.powerUsage
      });
    }
    
    // 3. 提取选择日的用电数据
    // 从统一数据格式转换方法中读取点击日是否有数据
    const currentDateStr = this.getCurrentModalDateStr();
    
    if (currentDateStr && this.standardData) {
      // 在 standardData.dayUsage 中查找点击日期的用电数据
      const dayUsageItem = this.standardData.dayUsage.find(item => item.time === currentDateStr);
      
      if (dayUsageItem && dayUsageItem.total_usage > 0) {
        // 当有点击日的用电数据时，显示分时数据
        result.dayConsumption = {
          source: 'time_distribution', // 数据来源：分时用电
          totalUsage: dayUsageItem.total_usage || 0,
          totalCost: dayUsageItem.total_amount || 0,
          timeDistribution: {
            valley: dayUsageItem.usage_ele_valley || 0,
            peak: dayUsageItem.usage_ele_peak || 0,
            tip: dayUsageItem.usage_ele_tip || 0,
            normal: dayUsageItem.usage_ele_norm || 0
          },
          unit: dayUsageItem.unit || this.standardData.unit || '',
          hasDetailedData: true
        };
      } else {
        // 当没有点击日的用电数据时，显示powerUsage的总计
        result.dayConsumption = {
          source: 'power_usage_sum', // 数据来源：设备用电量合计
          totalUsage: totalPowerUsage,
          totalCost: null, // 无法计算费用
          timeDistribution: null,
          unit: this.standardData.unit || '',
          hasDetailedData: false
        };
      }
    }
    
    // 存储完整数据供其他函数使用
    this.dayDeviceData = result;
    
    // 调试用：输出提取的数据
    if (this.showDebug) {
      console.log('========== 提取的设备数据 ==========');
      console.log('设备详细数据:', this.dayDeviceData.devices);
      console.log('房间聚合数据:', this.dayDeviceData.roomAggregation);
      console.log('选择日用电数据:', this.dayDeviceData.dayConsumption);
      console.log('=====================================');
    }
  }
  
  // 将时长字符串转换为秒数
  durationToSeconds(durationStr) {
    if (!durationStr || typeof durationStr !== 'string') return 0;
    
    // 格式："5h30m" 或 "30m" 或 "2h"
    const hoursMatch = durationStr.match(/(\d+)h/);
    const minutesMatch = durationStr.match(/(\d+)m/);
    
    let totalSeconds = 0;
    
    if (hoursMatch) {
      totalSeconds += parseInt(hoursMatch[1]) * 3600;
    }
    
    if (minutesMatch) {
      totalSeconds += parseInt(minutesMatch[1]) * 60;
    }
    
    return totalSeconds;
  }
  
  // 获取当前模态框的日期字符串
  getCurrentModalDateStr() {
    const titleText = this.dayModalTitleEl.textContent;
    const dateMatch = titleText.match(/(\d{4})年(\d{1,2})月(\d{1,2})日/);
    
    if (dateMatch) {
      const year = dateMatch[1];
      const month = String(dateMatch[2]).padStart(2, '0');
      const day = String(dateMatch[3]).padStart(2, '0');
      return `${year}-${month}-${day}`;
    }
    
    return null;
  }
  
  // 查找指定日期的用电数据
  findDayData(dateStr) {
    if (!this.historicalData || !this.historicalData.dayUsage) return null;
    
    // 在日历数据或历史数据中查找
    if (this.calendarData) {
      const dayItem = this.calendarData.find(item => item.date === dateStr);
      return dayItem || null;
    }
    
    return null;
  }
  
  // 渲染桑基图
  renderSankeyChart() {
    if (!this.dayDeviceData) {
      return;
    }
    
    // 检查ECharts是否可用
    if (typeof echarts === 'undefined') {
      console.error('ECharts 库未加载，无法渲染桑基图');
      return;
    }
    
    // 获取桑基图容器
    const sankeyContainer = this.dayModalBodyEl.querySelector('#sankey-chart-container');
    if (!sankeyContainer) {
      return;
    }
    
    // 销毁之前的图表实例
    if (this.sankeyChart) {
      this.sankeyChart.dispose();
      this.sankeyChart = null;
    }
    
    // 初始化图表
    this.sankeyChart = echarts.init(sankeyContainer, null, { 
      width: 'auto', 
      height: 400 
    });
    
    // 准备桑基图数据
    const nodes = [];
    const links = [];
    const nodeIndexMap = new Map();
    let nodeIndex = 0;
    
    // 获取消费数据
    const dayConsumption = this.dayDeviceData.dayConsumption;
    const hasDetailedData = dayConsumption && dayConsumption.hasDetailedData && dayConsumption.timeDistribution;
    
    // 根据是否有分时数据决定层级结构
    if (hasDetailedData) {
      // 四层级结构：总量 -> 分时 -> 房间 -> 设备
      
      // 第一层：总量
      const totalNodeName = '总量';
      nodes.push({
        name: totalNodeName,
        itemStyle: {
          color: '#804AFF'
        }
      });
      nodeIndexMap.set(totalNodeName, nodeIndex++);
      
      // 第二层：分时数据（尖、峰、平、谷）
      const timeDist = dayConsumption.timeDistribution;
      const timeLabels = {
        tip: '尖',
        peak: '峰',
        normal: '平',
        valley: '谷'
      };
      const timeColors = {
        tip: '#F44336',
        peak: '#FF9800',
        normal: '#2196F3',
        valley: '#4CAF50'
      };
      
      for (const [key, value] of Object.entries(timeDist)) {
        if (value > 0) {
          const nodeName = timeLabels[key] || key;
          nodes.push({
            name: nodeName,
            itemStyle: {
              color: timeColors[key] || '#9E9E9E'
            }
          });
          nodeIndexMap.set(nodeName, nodeIndex++);
          
          // 连接到总量节点
          links.push({
            source: nodeIndexMap.get(nodeName),
            target: nodeIndexMap.get(totalNodeName),
            value: value
          });
        }
      }
      
      // 第三层：房间聚合（连接到总量节点）
      const roomAggregation = this.dayDeviceData.roomAggregation || [];
      let totalRoomUsage = 0;
      
      for (const roomData of roomAggregation) {
        if (roomData.powerUsage > 0) {
          nodes.push({
            name: roomData.room,
            itemStyle: {
              color: this.getDeviceColor(roomData.room) || '#AA4C8F'
            }
          });
          nodeIndexMap.set(roomData.room, nodeIndex++);
          
          // 连接到总量节点
          links.push({
            source: nodeIndexMap.get(totalNodeName),
            target: nodeIndexMap.get(roomData.room),
            value: roomData.powerUsage
          });
          
          totalRoomUsage += roomData.powerUsage;
        }
      }
      
      // 检查分时用电总量与房间合计的差异，添加"其他"节点
      const totalTimeUsage = dayConsumption.totalUsage || 0;
      const otherUsage = totalTimeUsage - totalRoomUsage;
      
      if (otherUsage > 0) {
        const otherNodeName = '其他';
        nodes.push({
          name: otherNodeName,
          itemStyle: {
            color: '#9E9E9E'
          }
        });
        nodeIndexMap.set(otherNodeName, nodeIndex++);
        
        // 连接到总量节点
        links.push({
          source: nodeIndexMap.get(totalNodeName),
          target: nodeIndexMap.get(otherNodeName),
          value: otherUsage
        });
      }
      
      // 第四层：设备详细数据（连接到对应的房间）
      const devices = this.dayDeviceData.devices || [];
      
      for (const device of devices) {
        const powerValue = parseFloat(device.powerUsage) || 0;
        if (powerValue > 0) {
          // 使用唯一标识符作为节点名称
          const deviceNodeName = `${device.room}-${device.deviceName}`;
          nodes.push({
            name: deviceNodeName,
            itemStyle: {
              color: this.getDeviceColor(device.deviceName) || '#AA4C8F'
            }
          });
          nodeIndexMap.set(deviceNodeName, nodeIndex++);
          
          // 连接到对应的房间节点
          if (nodeIndexMap.has(device.room)) {
            links.push({
              source: nodeIndexMap.get(device.room),
              target: nodeIndexMap.get(deviceNodeName),
              value: powerValue
            });
          }
        }
      }
      
      // 在links创建完成后，添加节点标签格式化（确保唯一性）
      for (const device of devices) {
        const powerValue = parseFloat(device.powerUsage) || 0;
        if (powerValue > 0) {
          const deviceNodeName = `${device.room}-${device.deviceName}`;
          const nodeIndex = nodeIndexMap.get(deviceNodeName);
          if (nodeIndex !== undefined) {
            nodes[nodeIndex].label = {
              formatter: function(params) {
                // 从节点名称中提取设备名称（去掉房间前缀）
                const fullName = params.name;
                const dashIndex = fullName.indexOf('-');
                return dashIndex > 0 ? fullName.substring(dashIndex + 1) : fullName;
              }
            };
          }
        }
      }
    } else {
      // 三层级结构：总用电量 -> 房间 -> 设备
      
      // 第一层：总用电量（顶层节点）
      const totalNodeName = '总用电量';
      nodes.push({
        name: totalNodeName,
        itemStyle: {
          color: '#804AFF'
        }
      });
      nodeIndexMap.set(totalNodeName, nodeIndex++);
      
      // 第二层：房间聚合（连接到总用电量）
      const roomAggregation = this.dayDeviceData.roomAggregation || [];
      let totalRoomUsage = 0;
      
      for (const roomData of roomAggregation) {
        if (roomData.powerUsage > 0) {
          nodes.push({
            name: roomData.room,
            itemStyle: {
              color: this.getDeviceColor(roomData.room) || '#AA4C8F'
            }
          });
          nodeIndexMap.set(roomData.room, nodeIndex++);
          
          // 连接到总用电量节点
          links.push({
            source: nodeIndexMap.get(totalNodeName),
            target: nodeIndexMap.get(roomData.room),
            value: roomData.powerUsage
          });
          
          totalRoomUsage += roomData.powerUsage;
        }
      }
      
      // 检查总用电量与房间合计的差异，添加"其他"节点
      const totalPowerUsage = dayConsumption.totalUsage || 0;
      const otherUsage = totalPowerUsage - totalRoomUsage;
      
      if (otherUsage > 0) {
        const otherNodeName = '其他';
        nodes.push({
          name: otherNodeName,
          itemStyle: {
            color: '#9E9E9E'
          }
        });
        nodeIndexMap.set(otherNodeName, nodeIndex++);
        
        // 连接到总用电量节点
        links.push({
          source: nodeIndexMap.get(totalNodeName),
          target: nodeIndexMap.get(otherNodeName),
          value: otherUsage
        });
      }
      
      // 第三层：设备详细数据（连接到对应的房间）
      const devices = this.dayDeviceData.devices || [];
      
      for (const device of devices) {
        const powerValue = parseFloat(device.powerUsage) || 0;
        if (powerValue > 0) {
          // 使用唯一标识符作为节点名称
          const deviceNodeName = `${device.room}-${device.deviceName}`;
          nodes.push({
            name: deviceNodeName,
            itemStyle: {
              color: this.getDeviceColor(device.deviceName) || '#AA4C8F'
            }
          });
          nodeIndexMap.set(deviceNodeName, nodeIndex++);
          
          // 连接到对应的房间节点
          if (nodeIndexMap.has(device.room)) {
            links.push({
              source: nodeIndexMap.get(device.room),
              target: nodeIndexMap.get(deviceNodeName),
              value: powerValue
            });
          }
        }
      }
      
      // 在links创建完成后，添加节点标签格式化（确保唯一性）
      for (const device of devices) {
        const powerValue = parseFloat(device.powerUsage) || 0;
        if (powerValue > 0) {
          const deviceNodeName = `${device.room}-${device.deviceName}`;
          const nodeIndex = nodeIndexMap.get(deviceNodeName);
          if (nodeIndex !== undefined) {
            nodes[nodeIndex].label = {
              formatter: function(params) {
                // 从节点名称中提取设备名称（去掉房间前缀）
                const fullName = params.name;
                const dashIndex = fullName.indexOf('-');
                return dashIndex > 0 ? fullName.substring(dashIndex + 1) : fullName;
              }
            };
          }
        }
      }
    }
    
    // 配置选项（美化）
    const option = {
      backgroundColor: 'transparent',
      title: {
        text: '日用电量分布',
        left: 'center',
        textStyle: {
          fontSize: 16,
          color: 'var(--text-color)',
          fontWeight: 600
        }
      },
      tooltip: {
        trigger: 'item',
        triggerOn: 'mousemove',
        backgroundColor: 'var(--card-bg)',
        borderColor: 'var(--button-color)',
        borderWidth: 1,
        textStyle: {
          color: 'var(--text-color)',
          fontSize: 12
        },
        formatter: function(params) {
          const unit = dayConsumption?.unit || 'kWh';
          return `<div style="font-weight:600">${params.name}</div><div>${params.value.toFixed(2)} ${unit}</div>`;
        }
      },
      series: {
        type: 'sankey',
        layout: 'none',
        emphasis: {
          focus: 'adjacency'
        },
        nodeAlign: 'center',
        nodeGap: 15,
        nodeWidth: 24,
        layoutIterations: 0,
        data: nodes,
        links: links,
        label: {
          color: 'var(--text-color)',
          fontSize: 12,
          fontWeight: 500,
          position: 'right'
        },
        lineStyle: {
          color: 'gradient',
          curveness: 0.5,
          opacity: 0.7
        },
        itemStyle: {
          borderWidth: 0
        },
        animationDuration: 1000,
        animationEasing: 'cubicOut'
      }
    };
    
    // 数据验证：检查是否有重复节点名称
    const nodeNames = nodes.map(node => node.name);
    const duplicateNames = nodeNames.filter((name, index) => nodeNames.indexOf(name) !== index);
    if (duplicateNames.length > 0) {
      console.error('桑基图错误：发现重复节点名称', duplicateNames);
      // 如果有重复，不渲染图表
      return;
    }
    
    // 验证所有必需的字段
    if (!nodes || nodes.length === 0) {
      console.warn('桑基图警告：没有节点数据');
      return;
    }
    
    if (!links || links.length === 0) {
      console.warn('桑基图警告：没有连接数据');
      return;
    }
    
    // 设置选项并渲染
    this.sankeyChart.setOption(option);
    
    // 调试用：输出数据
    if (this.showDebug) {
      console.log('桑基图数据:', { nodes, links, hasDetailedData });
    }
  }
  
  // 切换 timeline-container 显示内容
  toggleTimelineContent(showSankey) {
    const timelineContainer = this.dayModalBodyEl.querySelector('#timeline-container');
    const sankeyContainer = this.dayModalBodyEl.querySelector('#sankey-chart-container');
    
    if (!timelineContainer || !sankeyContainer) {
      return;
    }
    
    if (showSankey) {
      // 显示桑基图，隐藏设备轨道
      timelineContainer.style.display = 'none';
      sankeyContainer.style.display = 'block';
      
      // 渲染桑基图
      this.renderSankeyChart();
    } else {
      // 显示设备轨道，隐藏桑基图
      timelineContainer.style.display = 'block';
      sankeyContainer.style.display = 'none';
    }
  }


  // 获取设备颜色
  getDeviceColor(deviceName) {
    if (deviceName.includes('灯')) return '#fcc800';
    if (deviceName.includes('插座')) return '#1e2a78';
    if (deviceName.includes('人在')) return '#9079ad';
    if (deviceName.includes('监控')) return '#ff5959';
    if (deviceName.includes('空调')) return '#21e6c1';
    return '#aa4c8f';
  }

  // 时间转秒数
  timeToSeconds(time) {
    if (!time) return 0;
    const [hours, minutes] = time.split(":").map(Number);
    return hours * 3600 + minutes * 60;
  }

  // 格式化时间
  formatTime(date) {
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  }
  
  // 初始化ECharts - 使用新的加载函数
  initializeECharts() {
    // 使用全局的loadECharts函数
    return loadECharts().then(() => {
      this.echartsLoaded = true;
    }).catch(err => {
      console.error('ECharts初始化失败:', err);
      this.echartsLoaded = false;
    });
  }

  // 统一的配置更新函数，同时处理阶梯电价和计费周期（仅非电力类型使用）
  updateTierAndPeriodConfig(config, updateDisplay = true) {
    // 当 utility_type 为 'ele' 时，此方法不应被调用
    if (this.utilityType === 'ele') {
      console.warn('updateTierAndPeriodConfig 被调用，但 utility_type 为 ele，此方法不应被调用');
      return;
    }
    
    // 更新阶梯配置
    if (config.tier1_max !== undefined || config.tier1_price !== undefined) {
      this.tierConfig.tiers[0].max = parseFloat(config.tier1_max) || 2160;
      this.tierConfig.tiers[0].price = parseFloat(config.tier1_price) || 0.4983;
    }
    
    if (config.tier2_max !== undefined || config.tier2_price !== undefined) {
      this.tierConfig.tiers[1].max = parseFloat(config.tier2_max) || 4200;
      this.tierConfig.tiers[1].price = parseFloat(config.tier2_price) || 0.5483;
    }
    
    if (config.tier3_price !== undefined) {
      this.tierConfig.tiers[2].price = parseFloat(config.tier3_price) || 0.7983;
    }
    
    // 更新计费周期配置
    let periodConfig;
    if (config.billing_cycle !== undefined) {
      periodConfig = this.parseBillingCycle(config.billing_cycle);
    } else if (config.period_start_month !== undefined || config.period_end_month !== undefined) {
      periodConfig = {
        periodStartMonth: parseInt(config.period_start_month) || 7,
        periodStartDay: parseInt(config.period_start_day) || 1,
        periodEndMonth: parseInt(config.period_end_month) || 6,
        periodEndDay: parseInt(config.period_end_day) || 30
      };
    }
    
    if (periodConfig) {
      this.tierConfig.periodStartMonth = periodConfig.periodStartMonth;
      this.tierConfig.periodStartDay = periodConfig.periodStartDay;
      this.tierConfig.periodEndMonth = periodConfig.periodEndMonth;
      this.tierConfig.periodEndDay = periodConfig.periodEndDay;
    }
    
    // 更新阶梯显示
    if (updateDisplay) {
      this.updateTierDisplay();
    }
  }
  
  // 更新阶梯电价配置（仅非电力类型使用） - 已合并到 updateTierAndPeriodConfig
  updateTierConfig(config) {
    this.updateTierAndPeriodConfig(config, true);
  }

  // 更新背景色配置
  updateBackgroundConfig(config) {
    if (config.background) {
      // 设置卡片背景
      this.electricityCardEl.style.background = config.background;
    } else {
      // 使用默认背景
      this.electricityCardEl.style.background = this.defaultConfig.background;
    }
  }

  // 解析计费周期字符串 (格式: M.D-M.D 如: 7.1-6.30, 1.1-12.31, 12.1-11.30)
  parseBillingCycle(billingCycleStr) {
    // 默认值
    let periodStartMonth = 7;
    let periodStartDay = 1;
    let periodEndMonth = 6;
    let periodEndDay = 30;
    
    if (billingCycleStr) {
      try {
        // 分割开始和结束日期
        const parts = billingCycleStr.split('-');
        if (parts.length === 2) {
          // 解析开始日期
          const startParts = parts[0].split('.');
          if (startParts.length === 2) {
            periodStartMonth = parseInt(startParts[0]);
            periodStartDay = parseInt(startParts[1]);
          }
          
          // 解析结束日期
          const endParts = parts[1].split('.');
          if (endParts.length === 2) {
            periodEndMonth = parseInt(endParts[0]);
            periodEndDay = parseInt(endParts[1]);
          }
        }
    } catch (error) {
      // Use default values silently
    }
    }
    
    return {
      periodStartMonth,
      periodStartDay,
      periodEndMonth,
      periodEndDay
    };
  }

  // 更新计费周期配置（仅非电力类型使用） - 已合并到 updateTierAndPeriodConfig
  updatePeriodConfig(config) {
    this.updateTierAndPeriodConfig(config, false);
  }

  // 统一的计费标准数据获取工具函数（消除重复代码）
  getBillingStandardData() {
    // 检查基本条件
    if (this.utilityType !== 'ele' || !this._hass || !this.entityId) {
      return null;
    }

    const entity = this._hass.states[this.entityId];
    const billingStandard = this.getBillingStandardObject(entity);
    
    if (!billingStandard || typeof billingStandard !== 'object') {
      return null;
    }

    return billingStandard;
  }

  // 更新阶梯显示（重构版本 - 使用统一的数据获取）
  updateTierDisplay() {
    const billingStandard = this.getBillingStandardData();
    
    // 【集中处理 utility_type 为 'ele' 的逻辑】从计费标准获取阶梯配置
    if (billingStandard) {
      // 判断计费标准类型，支持年阶梯、月阶梯和平均单价
      const billingStandardType = billingStandard['计费标准'] || '';
      
      // 处理平均单价计费方式
      if (billingStandardType === '平均单价' || billingStandard['平均单价'] !== undefined) {
        const usageUnit = this.standardData.unit || '度';
        const avgPrice = billingStandard['平均单价'];
        
        if (avgPrice !== undefined) {
          // 对于平均单价，所有阶梯显示相同的价格
          const priceHtml = `<div class="price-item-block">单价：${parseFloat(avgPrice).toFixed(4)}元/${usageUnit}</div>`;
          
          // 更新阶梯范围（显示为不适用）
          this.tier1RangeEl.textContent = `不适用`;
          this.tier2RangeEl.textContent = `不适用`;
          this.tier3RangeEl.textContent = `不适用`;
          
          // 更新电价显示（所有阶梯相同）
          this.tier1PriceEl.innerHTML = priceHtml;
          this.tier2PriceEl.innerHTML = priceHtml;
          this.tier3PriceEl.innerHTML = priceHtml;
          
          // 更新阶梯周期显示
          this.tierPeriodEl.textContent = `计费方式: 平均单价`;
          
          this.debugLog(`[updateTierDisplay] 平均单价: ${avgPrice}元/${usageUnit}`);
          return;
        }
      }
      
      const isMonthlyTier = billingStandardType.includes('月阶梯');
      
      // 根据计费标准类型选择正确的字段名
      const tier2Start = billingStandard[isMonthlyTier ? '月阶梯第2档起始电量' : '年阶梯第2档起始电量'];
      const tier3Start = billingStandard[isMonthlyTier ? '月阶梯第3档起始电量' : '年阶梯第3档起始电量'];

      if (tier2Start !== undefined && tier3Start !== undefined) {
        // 更新 tierConfig（从计费标准）
        this.tierConfig.tiers[0].max = parseFloat(tier2Start);
        this.tierConfig.tiers[1].max = parseFloat(tier3Start);

        // 获取用电量单位
        const usageUnit = this.standardData.unit || '度';

        // 生成阶梯范围文本
        const tier1RangeText = `0-${tier2Start}${usageUnit}`;
        const tier2RangeText = `${tier2Start + 1}-${tier3Start}${usageUnit}`;
        const tier3RangeText = `${tier3Start + 1}${usageUnit}以上`;

        this.tier1RangeEl.textContent = tier1RangeText;
        this.tier2RangeEl.textContent = tier2RangeText;
        this.tier3RangeEl.textContent = tier3RangeText;

        // 更新电价显示（支持6种计费标准：年阶梯峰平谷、年阶梯、月阶梯峰平谷、月阶梯峰平谷变动价格、月阶梯、平均单价）
        this.tier1PriceEl.innerHTML = this.renderPriceBlock({}, 1);
        this.tier2PriceEl.innerHTML = this.renderPriceBlock({}, 2);
        this.tier3PriceEl.innerHTML = this.renderPriceBlock({}, 3);
        
        // 更新阶梯周期显示（从计费标准获取）- 支持年阶梯和月阶梯
        const billingStandardType = billingStandard['计费标准'] || '未知';
        let startDate, endDate;
        
        if (billingStandardType.includes('月阶梯')) {
          // 月阶梯：周期为本月1日到本月最后一日
          const currentDate = new Date();
          const currentYear = currentDate.getFullYear();
          const currentMonth = currentDate.getMonth() + 1;
          const lastDay = new Date(currentYear, currentMonth, 0).getDate();
          
          startDate = `${currentYear}.${currentMonth}.1`;
          endDate = `${currentYear}.${currentMonth}.${lastDay}`;
          
          // 更新 tierConfig 中的周期配置
          this.tierConfig.periodStartMonth = currentMonth;
          this.tierConfig.periodStartDay = 1;
          this.tierConfig.periodEndMonth = currentMonth;
          this.tierConfig.periodEndDay = lastDay;
        } else {
          // 年阶梯：从计费标准读取
          startDate = billingStandard['当前年阶梯起始日期'];
          endDate = billingStandard['当前年阶梯结束日期'];
        }
        
        if (startDate && endDate) {
          // 解析日期格式 YYYY.MM.DD 并转换为 MM.DD
          const startParts = startDate.split('.');
          const endParts = endDate.split('.');
          
          if (startParts.length >= 3 && endParts.length >= 3) {
            const startMMDD = `${startParts[1]}.${startParts[2]}`;
            const endMMDD = `${endParts[1]}.${endParts[2]}`;
            this.tierPeriodEl.textContent = `阶梯周期: ${startMMDD}-${endMMDD}`;
            
            // === 重要：同时更新 tierConfig 中的周期配置，供 getCurrentTierPeriod 使用 ===
            if (!billingStandardType.includes('月阶梯')) {
              this.tierConfig.periodStartMonth = parseInt(startParts[1]) || 7;
              this.tierConfig.periodStartDay = parseInt(startParts[2]) || 1;
              this.tierConfig.periodEndMonth = parseInt(endParts[1]) || 6;
              this.tierConfig.periodEndDay = parseInt(endParts[2]) || 30;
            }
          }
        }
        
        return;
      }
      
      // 【重要】当 utility_type 为 'ele' 但无法获取计费标准数据时，直接返回，不执行回退逻辑
      return;
    }
    
    // 当 utility_type 不为 'ele' 时，使用原有逻辑
    const tier1 = this.tierConfig.tiers[0];
    const tier2 = this.tierConfig.tiers[1];
    const tier3 = this.tierConfig.tiers[2];
    
    // 获取用电量单位（从统一数据格式中获取，不设置默认值）
    const usageUnit = this.standardData.unit || '';
    
    // 更新tier-range元素（用于tier-content中）
    const tier1RangeText = usageUnit ? `0-${tier1.max}${usageUnit}` : `0-${tier1.max}`;
    const tier2RangeText = usageUnit ? `${tier1.max + 1}-${tier2.max}${usageUnit}` : `${tier1.max + 1}-${tier2.max}`;
    const tier3RangeText = usageUnit ? `${tier2.max + 1}${usageUnit}以上` : `${tier2.max + 1}以上`;
    
    this.tier1RangeEl.textContent = tier1RangeText;
    this.tier2RangeEl.textContent = tier2RangeText;
    this.tier3RangeEl.textContent = tier3RangeText;
    
    this.tier1PriceEl.textContent = usageUnit ? `${tier1.price.toFixed(4)}元/${usageUnit}` : `${tier1.price.toFixed(4)}元`;
    this.tier2PriceEl.textContent = usageUnit ? `${tier2.price.toFixed(4)}元/${usageUnit}` : `${tier2.price.toFixed(4)}元`;
    this.tier3PriceEl.textContent = usageUnit ? `${tier3.price.toFixed(4)}元/${usageUnit}` : `${tier3.price.toFixed(4)}元`;
  }

  // 【集中处理 utility_type 为 'ele' 的逻辑】从计费标准获取阶梯配置并更新 tierConfig - 已重构
  updateTierConfigFromBillingStandard() {
    const billingStandard = this.getBillingStandardData();
    if (!billingStandard) {
      return false; // 没有计费标准数据
    }

    // 判断计费标准类型，支持年阶梯和月阶梯
    const billingStandardType = billingStandard['计费标准'] || '';
    const isMonthlyTier = billingStandardType.includes('月阶梯');
    
    // 根据计费标准类型选择正确的字段名
    const tier2Start = billingStandard[isMonthlyTier ? '月阶梯第2档起始电量' : '年阶梯第2档起始电量'];
    const tier3Start = billingStandard[isMonthlyTier ? '月阶梯第3档起始电量' : '年阶梯第3档起始电量'];

    if (tier2Start === undefined || tier3Start === undefined) {
      return false; // 缺少必要的阶梯数据
    }

    // 更新 tierConfig
    this.tierConfig.tiers[0].max = parseFloat(tier2Start);
    this.tierConfig.tiers[1].max = parseFloat(tier3Start);
    
    return true; // 更新成功
  }

  // 获取计费标准对象（兼容两种属性名）
  getBillingStandardObject(entity) {
    // 优先使用 entity.attributes.计费标准
    if (entity.attributes && entity.attributes.计费标准) {
      return entity.attributes.计费标准;
    }
    // 如果不存在，尝试使用 entity.attributes.data.计费标准
    if (entity.attributes && entity.attributes.data.计费标准) {
      return entity.attributes.data.计费标准;
    }
    // 如果都不存在，返回null
    return null;
  }

  // 根据当前时刻匹配配置的尖、峰、平、谷时段；没有明确配置的时间按平段处理。
  getCurrentTouPeriod(billingStandard) {
    const now = new Date();
    const current = now.getHours() * 60 + now.getMinutes();
    const inPeriods = (value) => String(value || '').replace(/，/g, ',').split(',').some((item) => {
      const [start, end] = item.trim().split('-', 2).map((part) => part && part.trim());
      if (!start || !end) return false;
      const toMinutes = (time) => {
        const [hour, minute] = time.split(':').map(Number);
        return Number.isInteger(hour) && Number.isInteger(minute) && hour >= 0 && hour < 24 && minute >= 0 && minute < 60
          ? hour * 60 + minute : null;
      };
      const begin = toMinutes(start);
      const finish = toMinutes(end);
      if (begin === null || finish === null) return false;
      return begin <= finish ? current >= begin && current < finish : current >= begin || current < finish;
    });

    for (const [period, key] of [['tip', '尖峰时段'], ['peak', '峰时段'], ['valley', '谷时段'], ['flat', '平时段']]) {
      if (inPeriods(billingStandard[key])) return period;
    }

    // 黑龙江充电桩旧版配置没有将时段写入标准实体，使用当地官方时段兜底。
    if (billingStandard['计费标准'] === '充电桩计费' && billingStandard['省份'] === '黑龙江省') {
      if (inPeriods('07:00-08:00,09:00-11:30,15:30-20:00')) return 'peak';
      if (inPeriods('12:00-14:00,23:30-05:30')) return 'valley';
      return 'flat';
    }

    // 兼容没有保存分时时段的旧版峰谷模式。
    return (now.getHours() >= 23 || now.getHours() < 7) ? 'valley' : 'peak';
  }

  // 【集中处理 utility_type 为 'ele' 的逻辑】从计费标准获取当前时段的阶梯电价
  getCurrentTierPriceFromBillingStandard(tierNumber, defaultPrice = 0.4983) {
    const billingStandard = this.getBillingStandardData();
    
    // 如果是电力类型且实体有计费标准数据，从实体获取
    if (billingStandard) {
      // 判断计费标准类型，支持年阶梯、月阶梯和平均单价
      const billingStandardType = billingStandard['计费标准'] || '';
      
      // 处理平均单价计费方式（直接返回平均单价，不区分阶梯）
      if (billingStandardType === '平均单价' || billingStandard['平均单价'] !== undefined) {
        const avgPrice = billingStandard['平均单价'];
        if (avgPrice !== undefined) {
          const currentPrice = parseFloat(avgPrice);
          this.debugLog(`[平均单价] 直接返回平均单价:`, currentPrice);
          return currentPrice;
        }
      }
      
      const isMonthlyTier = billingStandardType.includes('月阶梯');
      
      // 根据计费标准类型选择正确的字段前缀
      const tierPrefix = isMonthlyTier ? '月阶梯' : '年阶梯';
      
      // 尝试获取当前阶梯的4个分时电价（尖、峰、平、谷）
      const sharpPrice = billingStandard[`${tierPrefix}第${tierNumber}档尖电价`];
      const peakPrice = billingStandard[`${tierPrefix}第${tierNumber}档峰电价`];
      const normalPrice = billingStandard[`${tierPrefix}第${tierNumber}档平电价`];
      const valleyPrice = billingStandard[`${tierPrefix}第${tierNumber}档谷电价`];

      // 有时段配置时必须按当前时段取价，不能固定显示最高的峰价。
      const period = this.getCurrentTouPeriod(billingStandard);
      const periodPrices = { tip: sharpPrice, peak: peakPrice, flat: normalPrice, valley: valleyPrice };
      if (periodPrices[period] !== undefined && Number.isFinite(parseFloat(periodPrices[period]))) {
        return parseFloat(periodPrices[period]);
      }

      // 收集所有有效的分时电价
      const prices = [];
      if (sharpPrice !== undefined) prices.push(parseFloat(sharpPrice));
      if (peakPrice !== undefined) prices.push(parseFloat(peakPrice));
      if (normalPrice !== undefined) prices.push(parseFloat(normalPrice));
      if (valleyPrice !== undefined) prices.push(parseFloat(valleyPrice));

      // 仅旧数据缺少当前时段对应价格时，才回退到最高价。
      if (prices.length > 0) {
        // 排序（从高到低）
        prices.sort((a, b) => b - a);
        const currentPrice = prices[0]; // 取第一个（最高的）
        return currentPrice;
      }
      
      // 【降级匹配】如果没有分时电价，尝试获取统一的阶梯电价
      const unifiedPrice = billingStandard[`${tierPrefix}第${tierNumber}档电价`];
      if (unifiedPrice !== undefined) {
        const currentPrice = parseFloat(unifiedPrice);
        return currentPrice;
      }

      // 【重要】如果是电力类型但无法从计费标准获取数据，返回0（不再回退到tierConfig或默认值）
      return 0;
    }
    
    // 对于非电力类型（如燃气），从阶梯配置获取价格
    if (this.tierConfig && this.tierConfig.tiers && this.tierConfig.tiers[tierNumber - 1]) {
      const tierPrice = this.tierConfig.tiers[tierNumber - 1].price;
      return tierPrice;
    }
    
    return defaultPrice; // 如果没有有效的价格，返回默认值
  }

  /* 根据计费标准和用电类型获取对应的电价信息
   * 支持6种不同的计费标准：年阶梯峰平谷、年阶梯、月阶梯峰平谷、月阶梯峰平谷变动价格、月阶梯、平均单价*/
  getElectricityPrices(billingStandard, currentLevel, electricityTypes) {
    // 检查基本条件
    if (this.utilityType !== 'ele' || !this._hass || !this.entityId) {
      return {};
    }
    
    const entity = this._hass.states[this.entityId];
    const billingStandardObj = this.getBillingStandardObject(entity);
    if (!billingStandardObj) return {};
    
    const prices = {};
    if (!electricityTypes || electricityTypes.length === 0) return prices;
    
    electricityTypes.forEach(type => {
      switch (billingStandard) {
        case '年阶梯峰平谷':
        case '月阶梯峰平谷季节电价':
        case '充电桩计费':
          if (type === 'tip') prices.tip = billingStandardObj[`年阶梯第${currentLevel}档尖电价`];
          if (type === 'peak') prices.peak = billingStandardObj[`年阶梯第${currentLevel}档峰电价`];
          if (type === 'normal') prices.normal = billingStandardObj[`年阶梯第${currentLevel}档平电价`];
          if (type === 'valley') prices.valley = billingStandardObj[`年阶梯第${currentLevel}档谷电价`];
          break;
        case '年阶梯':
          prices.single = billingStandardObj[`年阶梯第${currentLevel}档电价`];
          break;
        case '月阶梯峰平谷':
          if (type === 'tip') prices.tip = billingStandardObj[`月阶梯第${currentLevel}档尖电价`];
          if (type === 'peak') prices.peak = billingStandardObj[`月阶梯第${currentLevel}档峰电价`];
          if (type === 'normal') prices.normal = billingStandardObj[`月阶梯第${currentLevel}档平电价`];
          if (type === 'valley') prices.valley = billingStandardObj[`月阶梯第${currentLevel}档谷电价`];
          break;
        case '月阶梯峰平谷变动价格':
          if (type === 'tip') prices.tip = billingStandardObj[`月阶梯第${currentLevel}档尖电价`];
          if (type === 'peak') prices.peak = billingStandardObj[`月阶梯第${currentLevel}档峰电价`];
          if (type === 'normal') prices.normal = billingStandardObj[`月阶梯第${currentLevel}档平电价`];
          if (type === 'valley') {
            const currentMonth = new Date().getMonth() + 1;
            const monthKey = `${currentMonth}月`;
            prices.valley = billingStandardObj[`${monthKey}阶梯第${currentLevel}档谷电价`];
          }
          break;
        case '月阶梯':
          prices.single = billingStandardObj[`月阶梯第${currentLevel}档电价`];
          break;
        case '平均单价':
          prices.single = billingStandardObj.平均单价;
          break;
      }
    });
    
    return prices;
  }

  /*渲染价格区块*/
  renderPriceBlock(prices, level) {
    // 检查基本条件
    if (this.utilityType !== 'ele' || !this._hass || !this.entityId) {
      return '';
    }
    
    const entity = this._hass.states[this.entityId];
    const billingStandardObj = this.getBillingStandardObject(entity);
    if (!billingStandardObj) return `<div class="price-item-block">0.0000元/度</div>`;
    
    // 获取计费标准类型（支持两种属性名）
    const billingStandard = billingStandardObj.计费标准 || billingStandardObj.计费标准类型 || '未知';
    const usageUnit = this.standardData.unit || '度';
    
    // 如果是平均单价，直接显示
    if (billingStandard === '平均单价' || billingStandardObj.平均单价) {
      const singlePrice = billingStandardObj.平均单价;
      if (singlePrice) {
        return `<div class="price-item-block">单价：${parseFloat(singlePrice).toFixed(4)}元/${usageUnit}</div>`;
      }
    }
    
    let blockPrices = {};
    let hasPrice = false;
    
    // 根据计费标准类型获取对应的价格
    switch (billingStandard) {
      case '年阶梯峰平谷':
      case '月阶梯峰平谷季节电价':
      case '充电桩计费':
        blockPrices.tip = billingStandardObj[`年阶梯第${level}档尖电价`];
        blockPrices.peak = billingStandardObj[`年阶梯第${level}档峰电价`];
        blockPrices.normal = billingStandardObj[`年阶梯第${level}档平电价`];
        blockPrices.valley = billingStandardObj[`年阶梯第${level}档谷电价`];
        hasPrice = true;
        break;
      case '年阶梯':
        blockPrices.single = billingStandardObj[`年阶梯第${level}档电价`];
        hasPrice = true;
        break;
      case '月阶梯峰平谷':
        blockPrices.tip = billingStandardObj[`月阶梯第${level}档尖电价`];
        blockPrices.peak = billingStandardObj[`月阶梯第${level}档峰电价`];
        blockPrices.normal = billingStandardObj[`月阶梯第${level}档平电价`];
        blockPrices.valley = billingStandardObj[`月阶梯第${level}档谷电价`];
        hasPrice = true;
        break;
      case '月阶梯峰平谷变动价格':
        blockPrices.tip = billingStandardObj[`月阶梯第${level}档尖电价`];
        blockPrices.peak = billingStandardObj[`月阶梯第${level}档峰电价`];
        blockPrices.normal = billingStandardObj[`月阶梯第${level}档平电价`];
        const currentMonth = new Date().getMonth() + 1;
        const monthKey = `${currentMonth}月`;
        blockPrices.valley = billingStandardObj[`${monthKey}阶梯第${level}档谷电价`];
        hasPrice = true;
        break;
      case '月阶梯':
        blockPrices.single = billingStandardObj[`月阶梯第${level}档电价`];
        hasPrice = true;
        break;
      default:
        // 如果没有匹配到计费标准类型，尝试直接读取价格字段
        this.debugLog(`[renderPriceBlock] 未知计费标准类型: ${billingStandard}，尝试直接读取价格字段`);
        blockPrices.single = billingStandardObj[`第${level}档电价`] || billingStandardObj[`阶梯第${level}档电价`];
        blockPrices.tip = billingStandardObj[`第${level}档尖电价`];
        blockPrices.peak = billingStandardObj[`第${level}档峰电价`];
        blockPrices.normal = billingStandardObj[`第${level}档平电价`];
        blockPrices.valley = billingStandardObj[`第${level}档谷电价`];
        hasPrice = true;
        break;
    }
    
    // 生成HTML
    let html = '';
    let foundPrice = false;
    
    if (blockPrices.single) {
      html = `<div class="price-item-block">单价：${parseFloat(blockPrices.single).toFixed(4)}元/${usageUnit}</div>`;
      foundPrice = true;
    } else {
      // 分时电价
      if (blockPrices.tip) {
        html += `<div class="price-item-block">尖：${parseFloat(blockPrices.tip).toFixed(4)}元/${usageUnit}</div>`;
        foundPrice = true;
      }
      if (blockPrices.peak) {
        html += `<div class="price-item-block">峰：${parseFloat(blockPrices.peak).toFixed(4)}元/${usageUnit}</div>`;
        foundPrice = true;
      }
      if (blockPrices.normal) {
        html += `<div class="price-item-block">平：${parseFloat(blockPrices.normal).toFixed(4)}元/${usageUnit}</div>`;
        foundPrice = true;
      }
      if (blockPrices.valley) {
        html += `<div class="price-item-block">谷：${parseFloat(blockPrices.valley).toFixed(4)}元/${usageUnit}</div>`;
        foundPrice = true;
      }
    }
    
    if (foundPrice) {
      return html;
    } else {
      this.debugLog(`[renderPriceBlock] 未找到第${level}档的价格数据`);
      return `<div class="price-item-block">0.0000元/${usageUnit}</div>`;
    }
  }

  // 计算分时用电比例和用量
  calculateTimeDistribution(data) {
    const total = data.total || 0;
    const distributions = [];
    let hasNonZeroValue = false;
    
    // 计算各分时用电量，过滤掉0值的时段
    for (const type of this.timeConfig.types) {
      const value = data[type.key] || 0;
      
      // 只有当用电量大于0时才添加
      if (value > 0) {
        hasNonZeroValue = true;
        distributions.push({
          ...type,
          value: value,
          // 不计算百分比，只记录原始值
          percentage: 0,
          width: 0 // 宽度将在后续计算
        });
      }
    }
    
    // 如果没有非零值，返回空数组
    if (!hasNonZeroValue) {
      return [];
    }
    
    // 计算总用电量（仅非零值）
    const sum = distributions.reduce((total, dist) => total + dist.value, 0);
    
    // 计算每个时段的宽度百分比
    distributions.forEach(dist => {
      dist.percentage = (dist.value / sum) * 100;
      dist.width = dist.percentage;
    });
    
    return distributions;
  }

  // 创建分时用电条 - 修改：只显示用量，0值不显示
  createTimeDistributionBar(distributions, containerEl, labelsEl) {
    // 清空现有内容
    containerEl.innerHTML = '';
    labelsEl.innerHTML = '';
    
    // 如果没有数据，隐藏整个分时条区域
    if (distributions.length === 0) {
      containerEl.classList.add('empty');
      labelsEl.classList.add('empty');
      return;
    }
    
    // 显示分时条区域
    containerEl.classList.remove('empty');
    labelsEl.classList.remove('empty');
    
    // 创建分时段条
    distributions.forEach(dist => {
      const segment = document.createElement('div');
      segment.className = `time-segment ${dist.colorClass}`;
      segment.style.width = `${dist.width}%`;
      
      // 只显示用量，不显示百分比
      const displayText = `${Math.round(dist.value)}`;
      segment.textContent = displayText;
      segment.title = `${dist.name}: ${Math.round(dist.value)}度`;
      containerEl.appendChild(segment);
    });
    
    // 创建标签 - 只显示对应的分时名称
    distributions.forEach(dist => {
      const label = document.createElement('div');
      label.className = 'time-label';
      
      const text = document.createElement('span');
      text.textContent = dist.name;
      text.title = `${dist.name}: ${Math.round(dist.value)}度`;
      
      label.appendChild(text);
      labelsEl.appendChild(label);
    });
  }

  set hass(hass) {
    this._hass = hass;
    
    // 首次加载时应用主题（如果还没有应用过）
    if (this._config && this._config.theme && !this.lastThemeName) {
      this.updateTheme(this._config);
    }
    
    // 检查主题实体状态是否变化，实时响应主题变化
    if (this._config && this._config.theme) {
      this.updateThemeFromEntity();
    }
    
    this.updateCardWithThrottle();
  }

  // 节流更新函数，限制10分钟更新一次
  updateCardWithThrottle() {
    const now = Date.now();
    
    // 如果是第一次更新或者距离上次更新超过10分钟，则更新卡片
    if (!this.lastUpdateTime || (now - this.lastUpdateTime) >= this.updateInterval) {
      this.lastUpdateTime = now;
      this.updateCard();
    
    } else {
      const remainingMinutes = Math.ceil((this.updateInterval - (now - this.lastUpdateTime)) / 60000);
    }
  }

  // 获取当前年月字符串（格式：YYYY-MM）
  getCurrentMonthStr() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    return `${year}-${month}`;
  }

  /**
   * 更新趋势箭头（月/年同比）
   */
  updateTrendArrows() {
    this._updateMonthTrendArrow();
    this._updateLastMonthTrendArrow();
    this._updateYearTrendArrow();
  }

  /**
   * 本月同比：今年本月 vs 去年本月（相同日期范围）
   * 今年本月用 monthUsage（准确的运行合计）
   * 去年本月用 dayUsage 求和到与今年相同的截止日期
   */
  _updateMonthTrendArrow() {
    if (!this.monthTrendArrowEl || !this.standardData || !this.standardData.monthUsage) return;

    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonthStr = `${currentYear}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    const lastYear = currentYear - 1;
    const lastYearMonthStr = `${lastYear}-${String(now.getMonth() + 1).padStart(2, '0')}`;

    // 今年本月：使用月度合计（运行中的准确合计）
    const currentMonthData = this.standardData.monthUsage.find(m => m.time === currentMonthStr);
    const currentUsage = currentMonthData ? currentMonthData.total_usage : 0;

    // 找到今年本月有数据的最后日期
    const dayUsage = this.standardData.dayUsage || [];
    let latestDay = 0;
    dayUsage.forEach(day => {
      if (day.time && day.time.startsWith(currentMonthStr)) {
        const dayNum = parseInt(day.time.split('-')[2]);
        if (dayNum > latestDay) latestDay = dayNum;
      }
    });

    // 去年本月：用逐日数据求和到相同日期
    let lastYearUsage = 0;
    let hasData = false;
    if (latestDay > 0) {
      dayUsage.forEach(day => {
        if (day.time && day.time.startsWith(lastYearMonthStr)) {
          const dayNum = parseInt(day.time.split('-')[2]);
          if (dayNum <= latestDay) {
            lastYearUsage += day.total_usage || 0;
            hasData = true;
          }
        }
      });
    }

    this._setTrendArrow(this.monthTrendArrowEl, currentUsage, lastYearUsage, hasData);
  }

  /**
   * 上月同比：今年上月 vs 去年上月
   * 使用月度合计数据（monthUsage），两个完整月对比
   */
  _updateLastMonthTrendArrow() {
    if (!this.lastMonthTrendArrowEl || !this.standardData || !this.standardData.monthUsage) return;

    const now = new Date();
    const currentMonth = now.getMonth(); // 0-based
    const lastMonth = currentMonth === 0 ? 11 : currentMonth - 1;
    const lastMonthYear = currentMonth === 0 ? now.getFullYear() - 1 : now.getFullYear();
    const lastYearForCompare = lastMonthYear - 1;

    const lastMonthStr = `${lastMonthYear}-${String(lastMonth + 1).padStart(2, '0')}`;
    const lastYearMonthStr = `${lastYearForCompare}-${String(lastMonth + 1).padStart(2, '0')}`;

    const lastMonthData = this.standardData.monthUsage.find(m => m.time === lastMonthStr);
    const lastYearMonthData = this.standardData.monthUsage.find(m => m.time === lastYearMonthStr);

    const currentUsage = lastMonthData ? lastMonthData.total_usage : 0;
    const lastYearUsage = lastYearMonthData ? lastYearMonthData.total_usage : 0;
    const hasData = lastYearMonthData != null && lastYearUsage > 0;

    this._setTrendArrow(this.lastMonthTrendArrowEl, currentUsage, lastYearUsage, hasData);
  }

  /**
   * 本年同比：今年累计 vs 去年同期累计
   * 已完成的月份用 monthUsage（准确合计）
   * 当前月（未完成）用 dayUsage 求和到相同截止日期
   */
  _updateYearTrendArrow() {
    if (!this.yearTrendArrowEl || !this.standardData) return;

    const monthUsage = this.standardData.monthUsage || [];
    const dayUsage = this.standardData.dayUsage || [];
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1; // 1-based
    const lastYear = currentYear - 1;
    const prevMonth = currentMonth - 1; // 上一个完整月 (0-based: 0=Jan)

    let currentUsage = 0;
    let lastYearUsage = 0;
    let hasData = false;

    // 已完成的月份（1月到上月）：用月度合计
    monthUsage.forEach(m => {
      if (!m.time || !m.time.includes('-')) return;
      const parts = m.time.split('-');
      const year = parseInt(parts[0]);
      const month = parseInt(parts[1]);

      if (year === currentYear && month <= prevMonth) {
        currentUsage += m.total_usage || 0;
      }
      if (year === lastYear && month <= prevMonth) {
        lastYearUsage += m.total_usage || 0;
        hasData = true;
      }
    });

    // 当前月：用逐日数据求和到相同截止日期
    const currentMonthMM = String(currentMonth).padStart(2, '0');
    const currentMonthStr = `${currentYear}-${currentMonthMM}`;
    const lastYearMonthStr = `${lastYear}-${currentMonthMM}`;

    // 找到今年本月有数据的最后日期
    let latestDay = 0;
    dayUsage.forEach(day => {
      if (day.time && day.time.startsWith(currentMonthStr)) {
        const dayNum = parseInt(day.time.split('-')[2]);
        if (dayNum > latestDay) latestDay = dayNum;
      }
    });

    // 今年当前月：用月度合计（运行中的准确合计）
    const currentMonthData = monthUsage.find(m => m.time === currentMonthStr);
    if (currentMonthData) {
      currentUsage += currentMonthData.total_usage || 0;
    }

    // 去年当前月：用逐日数据求和到相同日期
    if (latestDay > 0) {
      dayUsage.forEach(day => {
        if (day.time && day.time.startsWith(lastYearMonthStr)) {
          const dayNum = parseInt(day.time.split('-')[2]);
          if (dayNum <= latestDay) {
            lastYearUsage += day.total_usage || 0;
            hasData = true;
          }
        }
      });
    }

    this._setTrendArrow(this.yearTrendArrowEl, currentUsage, lastYearUsage, hasData);
  }

  /**
   * 设置趋势箭头：增加红色↑，减少绿色↓，无数据则隐藏
   */
  _setTrendArrow(el, current, previous, hasData) {
    if (!hasData || previous === 0) {
      el.textContent = '';
      el.className = 'trend-arrow';
      return;
    }

    const diff = current - previous;
    if (diff > 0) {
      const pct = ((diff / previous) * 100).toFixed(0);
      el.textContent = `▲${pct}%`;
      el.className = 'trend-arrow up';
    } else if (diff < 0) {
      const pct = ((Math.abs(diff) / previous) * 100).toFixed(0);
      el.textContent = `▼${pct}%`;
      el.className = 'trend-arrow down';
    } else {
      el.textContent = '';
      el.className = 'trend-arrow';
    }
  }
  
  // 从标准格式获取当前月份数据
  getCurrentMonthStandardData() {
    const currentMonthStr = this.getCurrentMonthStr();
    const currentMonthData = this.standardData.monthUsage.find(item => item.time === currentMonthStr);
    
    if (currentMonthData) {
      return currentMonthData;
    }
    
    // 返回默认值
    return {
      user: 'ele_01',
      utility_type: this.utilityType,
      data_category: 'usage',
      date_granularity: 'month',
      time: currentMonthStr,
      data_source: 'entity',
      total_usage: 0,
      total_amount: 0,
      unit: this.standardData.unit || '',
      usage_ele_valley: 0,
      usage_ele_peak: 0,
      usage_ele_tip: 0,
      usage_ele_norm: 0,
      usage_ele_no: 0
    };
  }
  
  // 从标准格式获取上月数据
  getLastMonthStandardData() {
    const now = new Date();
    const lastMonthDate = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const lastMonthStr = `${lastMonthDate.getFullYear()}-${String(lastMonthDate.getMonth() + 1).padStart(2, '0')}`;
    
    const lastMonthData = this.standardData.monthUsage.find(item => item.time === lastMonthStr);
    
    if (lastMonthData) {
      return lastMonthData;
    }
    
    // 如果找不到，返回第二个数据（如果存在）
    if (this.standardData.monthUsage.length > 1) {
      return this.standardData.monthUsage[1];
    }
    
    // 返回默认值
    return {
      user: 'ele_01',
      utility_type: this.utilityType,
      data_category: 'usage',
      date_granularity: 'month',
      time: lastMonthStr,
      data_source: 'entity',
      total_usage: 0,
      total_amount: 0,
      unit: this.standardData.unit || '',
      usage_ele_valley: 0,
      usage_ele_peak: 0,
      usage_ele_tip: 0,
      usage_ele_norm: 0,
      usage_ele_no: 0
    };
  }
  
  // 从标准格式获取当前年度数据
  getCurrentYearStandardData() {
    const currentYear = new Date().getFullYear().toString();
    
    const currentYearData = this.standardData.yearUsage.find(item => item.time === currentYear);
    
    if (currentYearData) {
      return currentYearData;
    }
    
    // 如果找不到，返回第一个年份数据（如果存在）
    if (this.standardData.yearUsage.length > 0) {
      return this.standardData.yearUsage[0];
    }
    
    // 返回默认值
    return {
      user: 'ele_01',
      utility_type: this.utilityType,
      data_category: 'usage',
      date_granularity: 'year',
      time: currentYear,
      data_source: 'entity',
      total_usage: 0,
      total_amount: 0,
      unit: this.standardData.unit || '',
      usage_ele_valley: 0,
      usage_ele_peak: 0,
      usage_ele_tip: 0,
      usage_ele_norm: 0,
      usage_ele_no: 0
    };
  }

  // 获取当前月份用电数据（原始格式，保留兼容性）
  getCurrentMonthData(monthlist) {
    if (!monthlist || !Array.isArray(monthlist)) {
      return { 
        monthEleNum: 0, 
        monthEleCost: 0,
        total: 0,
        TPq: 0,
        PPq: 0,
        NPq: 0,
        VPq: 0
      };
    }
    
    const currentMonthStr = this.getCurrentMonthStr();
    
    // 查找当前月份的数据
    const currentMonthData = monthlist.find(item => item.month === currentMonthStr);
    
    if (currentMonthData) {
      return {
        monthEleNum: currentMonthData.monthEleNum || 0,
        monthEleCost: currentMonthData.monthEleCost || 0,
        total: currentMonthData.monthEleNum || 0,
        TPq: currentMonthData.monthTPq || 0,
        PPq: currentMonthData.monthPPq || 0,
        NPq: currentMonthData.monthNPq || 0,
        VPq: currentMonthData.monthVPq || 0
      };
    }
    
    return { 
      monthEleNum: 0, 
      monthEleCost: 0,
      total: 0,
      TPq: 0,
      PPq: 0,
      NPq: 0,
      VPq: 0
    };
  }

  // 获取当前阶梯电价周期
  getCurrentTierPeriod() {
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1; // 月份从0开始，所以+1
    
    // 使用默认值，避免 null 导致的错误
    const periodStartMonth = this.tierConfig.periodStartMonth || 7;
    const periodStartDay = this.tierConfig.periodStartDay || 1;
    const periodEndMonth = this.tierConfig.periodEndMonth || 6;
    const periodEndDay = this.tierConfig.periodEndDay || 30;
    
    let startYear, endYear;
    
    // 判断当前日期属于哪个计费周期
    // 比较当前月份和计费周期开始月份
    if (currentMonth >= periodStartMonth) {
      // 如果当前月份在计费周期开始月份之后或相同
      startYear = currentYear;
      
      // 计算结束年份：如果结束月份小于开始月份，说明跨年了
      if (periodEndMonth < periodStartMonth) {
        endYear = currentYear + 1;
      } else {
        endYear = currentYear;
      }
    } else {
      // 如果当前月份在计费周期开始月份之前
      // 说明当前属于上一个周期的后半段
      startYear = currentYear - 1;
      
      // 计算结束年份
      if (periodEndMonth < periodStartMonth) {
        endYear = currentYear;
      } else {
        endYear = currentYear;
      }
    }
    
    // 创建周期开始和结束日期
    const periodStart = new Date(startYear, periodStartMonth - 1, periodStartDay);
    const periodEnd = new Date(endYear, periodEndMonth - 1, periodEndDay);
    
    return {
      start: periodStart,
      end: periodEnd,
      startYear,
      endYear
    };
  }

  // 格式化日期为 MM.DD 格式
  formatDateMMDD(date) {
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${month}.${day}`;
  }

  // 从daylist计算当前周期累计用电量
  calculatePeriodUsageFromDaylist(daylist) {
    if (!daylist || !Array.isArray(daylist)) {
      return 0;
    }
    
    const period = this.getCurrentTierPeriod();
    const periodStart = period.start;
    const periodEnd = period.end;
    const now = new Date();
    
    // 使用今天的日期或周期结束日期中较早的那个
    const endDate = now < periodEnd ? now : periodEnd;
    
    let totalUsage = 0;
    
    // 根据 utility_type 获取对应的用量字段
    const usageField = this.getUsageFieldByUtilityType();
    
    // 获取配置的日期字段名（默认为 'day'）
    const dateField = this.getDateFieldByUtilityType();
    
    // 遍历daylist，累加在周期内的用电量
    for (const dayData of daylist) {
      const dayStr = dayData[dateField];
      
      if (!dayStr) {
        console.warn(`Daylist 数据中缺少日期字段 '${dateField}':`, dayData);
        continue;
      }
      
      // 解析日期字符串，假设格式为 "YYYY-MM-DD"
      try {
        const [year, month, day] = dayStr.split('-').map(Number);
        const date = new Date(year, month - 1, day);
        
        // 检查日期是否有效
        if (isNaN(date.getTime())) {
          console.warn(`Daylist 数据中日期格式无效: ${dayStr}`);
          continue;
        }
        
        // 检查日期是否在周期内
        if (date >= periodStart && date <= endDate) {
          // 根据 utility_type 使用不同的字段，确保是有效的数字
          const usageValue = dayData[usageField];
          if (usageValue !== undefined && usageValue !== null) {
            const parsedUsage = parseFloat(usageValue);
            if (!isNaN(parsedUsage)) {
              totalUsage += parsedUsage;
            }
          }
        }
      } catch (error) {
        console.warn(`解析日期 ${dayStr} 时出错:`, error);
        continue;
      }
    }
    
    // 确保返回的是有效的数字
    return isNaN(totalUsage) ? 0 : totalUsage;
  }
  
  // 根据 utility_type 获取日期字段名
  getDateFieldByUtilityType() {
    // 检查是否有自定义的字段映射（字段映射存储在 this.fieldMapping 中）
    if (this.fieldMapping && this.fieldMapping.date) {
      return this.fieldMapping.date;
    }
    
    // 默认字段名
    return 'day';
  }
  
  // 根据 utility_type 获取用量字段名
  getUsageFieldByUtilityType() {
    // 检查是否有自定义的字段映射（字段映射存储在 this.fieldMapping 中）
    if (this.fieldMapping && this.fieldMapping.usage) {
      return this.fieldMapping.usage;
    }
    
    // 默认字段名（向后兼容）
    switch (this.utilityType) {
      case 'ele':
        return 'dayEleNum';
      case 'gas':
        return 'f_gas';
      case 'water':
        return 'usge';
      default:
        return 'dayEleNum';
    }
  }

  // 计算当前阶梯
  calculateCurrentTier(usage) {
    const tiers = this.tierConfig.tiers;
    
    for (let i = 0; i < tiers.length; i++) {
      if (usage <= tiers[i].max) {
        return {
          tier: i + 1,
          price: tiers[i].price,
          maxUsage: tiers[i].max,
          remaining: Math.max(0, tiers[i].max - usage),
          isLastTier: i === tiers.length - 1
        };
      }
    }
    
    // 如果超过所有阶梯，返回最后一个阶梯
    const lastTier = tiers[tiers.length - 1];
    return {
      tier: tiers.length,
      price: lastTier.price,
      maxUsage: Infinity,
      remaining: 0,
      isLastTier: true
    };
  }

  // 计算当前指示器位置 - 简化方案
  // 由于tiers-container使用justify-content: center，我们假设三个tier平均分配可视区域
  // 虽然实际宽度略有不同，但这个近似足够准确
  calculateIndicatorPosition(usage, tierInfo) {
    // 获取 tier-block 的实际位置，基于实际布局计算
    const tierBlocks = this.shadowRoot.querySelectorAll('.tier-block');
    if (tierBlocks.length < 3) {
      // 如果找不到 tier-block，回退到固定计算

      return this.calculateIndicatorPositionFallback(usage, tierInfo);
    }
    
    const containerRect = this.tiersContainerEl.getBoundingClientRect();
    
    // 检查容器宽度是否有效
    if (!containerRect || containerRect.width <= 0) {

      return this.calculateIndicatorPositionFallback(usage, tierInfo);
    }
    
    const block1Rect = tierBlocks[0].getBoundingClientRect();
    const block2Rect = tierBlocks[1].getBoundingClientRect();
    const block3Rect = tierBlocks[2].getBoundingClientRect();
    
    // 检查 rect 是否有效
    if (!block1Rect || !block2Rect || !block3Rect) {

      return this.calculateIndicatorPositionFallback(usage, tierInfo);
    }
    
    // 计算每个 tier-block 的边界（相对于容器）
    const block1Left = ((block1Rect.left - containerRect.left) / containerRect.width) * 100;
    const block1Right = ((block1Rect.right - containerRect.left) / containerRect.width) * 100;
    const block2Left = ((block2Rect.left - containerRect.left) / containerRect.width) * 100;
    const block2Right = ((block2Rect.right - containerRect.left) / containerRect.width) * 100;
    const block3Left = ((block3Rect.left - containerRect.left) / containerRect.width) * 100;
    const block3Right = ((block3Rect.right - containerRect.left) / containerRect.width) * 100;
    
    // 检查结果是否有效
    if (isNaN(block1Left) || isNaN(block1Right) || isNaN(block2Left) || 
        isNaN(block2Right) || isNaN(block3Left) || isNaN(block3Right)) {

      return this.calculateIndicatorPositionFallback(usage, tierInfo);
    }


    // 基于阶梯配置计算位置
    const tier1Max = this.tierConfig.tiers[0].max;
    const tier2Max = this.tierConfig.tiers[1].max;
    
    let positionPercent = 0;
    
    if (tierInfo.tier === 1) {
      // 在第一阶梯内：映射到 block1 的范围内
      const progress = Math.min(usage / tier1Max, 1);
      positionPercent = block1Left + (progress * (block1Right - block1Left));
    } else if (tierInfo.tier === 2) {
      // 在第二阶梯内：映射到 block2 的范围内
      const progress = Math.min((usage - tier1Max) / (tier2Max - tier1Max), 1);
      positionPercent = block2Left + (progress * (block2Right - block2Left));
    } else {
      // 在第三阶梯内：映射到 block3 的范围内
      // 计算一个合理的最大值（tier2.max * 1.5 - tier2.max）
      const tier3Range = tier2Max * 0.5;
      const progress = Math.min((usage - tier2Max) / tier3Range, 1);
      positionPercent = block3Left + (progress * (block3Right - block3Left));

    }
    
    // 确保不超过实际边界
    const finalPosition = Math.min(Math.max(positionPercent, block1Left), block3Right);

    
    return finalPosition;
  }
  
  calculateIndicatorPositionFallback(usage, tierInfo) {
    // 回退方法：基于阶梯配置计算（用于 tier-block 不可用时）
    const tier1Max = this.tierConfig.tiers[0].max;
    const tier2Max = this.tierConfig.tiers[1].max;
    
    // 假设三个 tier-block 平均分配空间（每个约33.33%）
    // 由于居中对齐，假设左边有5%的空白
    const blockStartPercent = 5;
    const blockWidth = 30; // 每个 block 约 30%
    
    let positionPercent = 0;
    
    if (tierInfo.tier === 1) {
      // 在第一阶梯内
      const progress = Math.min(usage / tier1Max, 1);
      positionPercent = blockStartPercent + (progress * blockWidth);
    } else if (tierInfo.tier === 2) {
      // 在第二阶梯内
      const progress = Math.min((usage - tier1Max) / (tier2Max - tier1Max), 1);
      positionPercent = blockStartPercent + blockWidth + (progress * blockWidth);
    } else {
      // 在第三阶梯内
      const tier3Range = tier2Max * 0.5;
      const progress = Math.min((usage - tier2Max) / tier3Range, 1);
      positionPercent = blockStartPercent + (2 * blockWidth) + (progress * blockWidth);
    }
    
    return positionPercent;
  }

  // 更新阶梯指示器
  updateTierIndicator(usage) {
    // 当 utility_type 为 'ele' 时，从 entity 的"计费标准"节点获取当前阶梯档和累计用电量
    if (this.utilityType === 'ele' && this._hass && this.entityId) {
      const entity = this._hass.states[this.entityId];
      const billingStandard = this.getBillingStandardObject(entity);

      if (billingStandard) {
        // === 根据计费标准类型动态选择字段名 ===
        const billingStandardType = billingStandard['计费标准'] || '';
        const isMonthlyTier = billingStandardType.includes('月阶梯');

        // 动态选择字段名
        const currentTierField = isMonthlyTier ? '当前月阶梯档' : '当前年阶梯档';
        const accumulatedUsageField = isMonthlyTier ? '月阶梯累计用电量' : '年阶梯累计用电量';

        // 读取当前阶梯档和累计用电量
        const currentTierStr = billingStandard[currentTierField];
        const accumulatedUsage = billingStandard[accumulatedUsageField];

        // 将"第X档"转换为数字
        let tierNum = 1;
        if (typeof currentTierStr === 'string') {
          const match = currentTierStr.match(/第(\d+)档/);
          if (match) {
            tierNum = parseInt(match[1], 10);
          }
        }

        // 使用实体中的累计用电量
        const actualUsage = accumulatedUsage !== undefined ? parseFloat(accumulatedUsage) : usage;

        // 重新计算 tierInfo，使用实际用电量和阶梯档位
        const tierInfo = {
          tier: tierNum,
          price: this.tierConfig.tiers[tierNum - 1]?.price || 0.4983
        };
        const period = this.getCurrentTierPeriod();

        // 存储当前周期用电量和阶梯
        this.currentPeriodUsage = actualUsage;
        this.currentTier = tierInfo.tier;

        // 【集中处理 utility_type 为 'ele' 的逻辑】使用辅助方法获取当前阶梯的第一个单价
        const currentPrice = this.getCurrentTierPriceFromBillingStandard(tierInfo.tier, tierInfo.price);

        // 更新电价显示
        this.electricityPriceEl.textContent = currentPrice.toFixed(4);

        // 更新电价单位显示（元/单位）
        const usageUnit = this.standardData.unit || '';
        this.priceUnitEl.textContent = usageUnit ? `元/${usageUnit}` : '元';

        // 更新周期显示为 MM.DD-MM.DD 格式
        const startDateStr = this.formatDateMMDD(period.start);
        const endDateStr = this.formatDateMMDD(period.end);
        this.tierPeriodEl.textContent = `阶梯周期: ${startDateStr}-${endDateStr}`;

        // 移除所有阶梯的current类
        this.tier1El.classList.remove('current');
        this.tier2El.classList.remove('current');
        this.tier3El.classList.remove('current');

        // 为当前阶梯添加current类
        const currentTierEl = this.shadowRoot.getElementById(`tier-${tierInfo.tier}`);
        if (currentTierEl) {
          currentTierEl.classList.add('current');
        }

        // 移除可能存在的旧红色竖线指示器
        const oldRedLines = this.shadowRoot.querySelectorAll('.red-line-indicator');
        oldRedLines.forEach(line => line.remove());

        // 计算指示器位置
        this._updateIndicatorPositionAndDisplay(actualUsage, tierInfo, period);

        return;
      }
    }

    // 当 utility_type 不为 'ele' 或无法获取计费标准数据时，使用原有逻辑
    const tierInfo = this.calculateCurrentTier(usage);
    const period = this.getCurrentTierPeriod();

    // 存储当前周期用电量和阶梯
    this.currentPeriodUsage = usage;
    this.currentTier = tierInfo.tier;

    // 【集中处理 utility_type 为 'ele' 的逻辑】使用辅助方法获取当前阶梯的第一个单价
    const currentPrice = this.getCurrentTierPriceFromBillingStandard(tierInfo.tier, tierInfo.price);

    // 更新电价显示
    this.electricityPriceEl.textContent = currentPrice.toFixed(4);

    // 更新电价单位显示（元/单位）
    const usageUnit = this.standardData.unit || '';
    this.priceUnitEl.textContent = usageUnit ? `元/${usageUnit}` : '元';

    // 更新周期显示为 MM.DD-MM.DD 格式
    const startDateStr = this.formatDateMMDD(period.start);
    const endDateStr = this.formatDateMMDD(period.end);
    this.tierPeriodEl.textContent = `阶梯周期: ${startDateStr}-${endDateStr}`;

    // 移除所有阶梯的current类
    this.tier1El.classList.remove('current');
    this.tier2El.classList.remove('current');
    this.tier3El.classList.remove('current');

    // 为当前阶梯添加current类
    const currentTierEl = this.shadowRoot.getElementById(`tier-${tierInfo.tier}`);
    if (currentTierEl) {
      currentTierEl.classList.add('current');
    }

    // 移除可能存在的旧红色竖线指示器
    const oldRedLines = this.shadowRoot.querySelectorAll('.red-line-indicator');
    oldRedLines.forEach(line => line.remove());

    // 计算指示器位置
    this._updateIndicatorPositionAndDisplay(usage, tierInfo, period);
  }

  // 更新指示器位置和显示的内部方法
  _updateIndicatorPositionAndDisplay(usage, tierInfo, period) {
    // 确保 tiersContainerEl 已经存在且有有效宽度
    if (!this.tiersContainerEl) {
      return;
    }
    
    // 确保容器已渲染且有宽度
    const containerRect = this.tiersContainerEl.getBoundingClientRect();
    if (containerRect.width <= 0) {
      // 延迟后重试
      setTimeout(() => {
        if (this.tiersContainerEl && this.tiersContainerEl.getBoundingClientRect().width > 0) {
          this._updateIndicatorPositionAndDisplay(usage, tierInfo, period);
        }
      }, 100);
      return;
    }
    
    // 使用用户代码中的精确定位方式
    const totalWidth = 100;
    const tierWidthPercent = totalWidth / 3;

    // 计算当前阶梯指示器的位置
    let indicatorPosition = 0;

    if (tierInfo.tier === 1) {
      // 确保在第一阶梯内有正确的位置
      if (usage > 0 && this.tierConfig.tiers[0].max > 0) {
        indicatorPosition = (usage / this.tierConfig.tiers[0].max) * tierWidthPercent;
        // 确保不超过第一阶梯的范围
        indicatorPosition = Math.min(indicatorPosition, tierWidthPercent);
        // 确保最小位置不为0（除非用电量为0）
        if (indicatorPosition < 0.5 && usage > 0) {
          indicatorPosition = 0.5; // 设置一个最小偏移量，避免在最左侧
        }
      } else {
        indicatorPosition = 0;
      }
    } else if (tierInfo.tier === 2) {
      indicatorPosition = tierWidthPercent + ((usage - this.tierConfig.tiers[0].max) / (this.tierConfig.tiers[1].max - this.tierConfig.tiers[0].max)) * tierWidthPercent;
      // 确保在第二阶梯范围内
      indicatorPosition = Math.max(tierWidthPercent, Math.min(indicatorPosition, 2 * tierWidthPercent));
    } else if (tierInfo.tier === 3) {
      indicatorPosition = 2 * tierWidthPercent + ((usage - this.tierConfig.tiers[1].max) / 1000) * tierWidthPercent;
      // 确保不超过100%
      indicatorPosition = Math.min(indicatorPosition, totalWidth);
    }

    // 计算红色竖线和倒三角的最终位置
    const redLineLeft = Math.max(0, indicatorPosition);
    const triangleLeft = Math.max(0, indicatorPosition);

    // 当前阶梯指示器的背景颜色始终使用白天模式的颜色，不跟随黑夜模式变化
    let currentIndicatorBgColor;
    if (tierInfo.tier === 1) {
      currentIndicatorBgColor = 'rgb(85, 197, 147)'; // 始终使用白天模式的第一阶梯颜色
    } else if (tierInfo.tier === 2) {
      currentIndicatorBgColor = 'rgb(248, 195, 55)'; // 始终使用白天模式的第二阶梯颜色
    } else if (tierInfo.tier === 3) {
      currentIndicatorBgColor = 'rgb(247, 147, 53)'; // 始终使用白天模式的第三阶梯颜色
    }

    // 将数字阶梯转换为带圆圈的数字
    const circleTiers = {1: '❶', 2: '❷', 3: '❸'};

    // 创建完整的文本内容
    const fullText = `${circleTiers[tierInfo.tier]}${usage.toFixed(1)}°`;

    // 计算当前阶梯指示器的位置和变换
    let currentIndicatorLeft = 0;
    let currentIndicatorTransform = '';

    if (tierInfo.tier === 1) {
      // 当用电量为0时，将指示器放在最左侧
      if (usage <= 0) {
        currentIndicatorLeft = 0;
        currentIndicatorTransform = 'none';
      } else {
        currentIndicatorLeft = 0;
        currentIndicatorTransform = 'none';
      }
    } else if (tierInfo.tier === 3) {
      currentIndicatorLeft = 100;
      currentIndicatorTransform = 'translateX(-100%)';
    } else {
      currentIndicatorLeft = indicatorPosition;
      currentIndicatorTransform = 'translateX(-50%)';
    }

    // 创建红色竖线指示器（放在tiers-container中）
    const redLineIndicator = document.createElement('div');
    redLineIndicator.className = 'red-line-indicator';
    redLineIndicator.style.left = `${redLineLeft}%`;
    redLineIndicator.style.position = 'absolute';
    redLineIndicator.style.top = '13px';
    redLineIndicator.style.width = '3px';
    redLineIndicator.style.height = '15px';
    redLineIndicator.style.backgroundColor = '#ff0000';
    redLineIndicator.style.zIndex = '8';
    redLineIndicator.style.boxShadow = '0 0 3px rgba(255, 0, 0, 0.7)';
    redLineIndicator.style.transform = 'translateX(-50%)';
    this.tiersContainerEl.appendChild(redLineIndicator);

    // 更新当前指示器内容
    this.currentTierEl.textContent = circleTiers[tierInfo.tier] || tierInfo.tier;
    this.currentUsageEl.textContent = usage.toFixed(1);

    // 更新当前指示器背景色
    this.currentIndicatorEl.classList.remove('tier-1', 'tier-2', 'tier-3');
    this.currentIndicatorEl.classList.add(`tier-${tierInfo.tier}`);

    // 设置当前指示器的位置和样式（使用用户代码的精确定位方式）
    this.currentIndicatorEl.style.position = 'absolute';
    this.currentIndicatorEl.style.top = '-18px';
    this.currentIndicatorEl.style.left = `${currentIndicatorLeft}%`;
    this.currentIndicatorEl.style.transform = currentIndicatorTransform;
    this.currentIndicatorEl.style.backgroundColor = currentIndicatorBgColor;
    this.currentIndicatorEl.style.color = 'white';
    this.currentIndicatorEl.style.padding = '4px 10px';
    this.currentIndicatorEl.style.borderRadius = '10px';
    this.currentIndicatorEl.style.fontSize = '11px';
    this.currentIndicatorEl.style.fontWeight = '600';
    this.currentIndicatorEl.style.whiteSpace = 'nowrap';
    this.currentIndicatorEl.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.2)';
    this.currentIndicatorEl.style.zIndex = '10';
    this.currentIndicatorEl.style.pointerEvents = 'none';
    this.currentIndicatorEl.style.minWidth = 'auto';
    this.currentIndicatorEl.style.maxWidth = '300px';
    this.currentIndicatorEl.style.overflow = 'hidden';
    this.currentIndicatorEl.style.textOverflow = 'ellipsis';

    // 当用电量为0时，确保在最左侧
    if (usage <= 0) {
      this.currentIndicatorEl.style.left = '0%';
      this.currentIndicatorEl.style.transform = 'none';
    }

    // 移除可能存在的旧倒三角指示器
    const oldTriangle = this.shadowRoot.querySelector('.current-indicator-triangle');
    if (oldTriangle) {
      oldTriangle.remove();
    }

    // 添加倒三角指示器 - 确保与红色竖线完全对齐
    const triangleIndicator = document.createElement('div');
    triangleIndicator.className = 'current-indicator-triangle';
    triangleIndicator.style.position = 'absolute';
    triangleIndicator.style.top = '6px';
    triangleIndicator.style.left = `${triangleLeft}%`;
    triangleIndicator.style.transform = 'translateX(-50%)';
    triangleIndicator.style.width = '0';
    triangleIndicator.style.height = '0';
    triangleIndicator.style.borderLeft = '4px solid transparent';
    triangleIndicator.style.borderRight = '4px solid transparent';
    triangleIndicator.style.borderTop = `4px solid ${currentIndicatorBgColor}`;
    triangleIndicator.style.zIndex = '9';
    triangleIndicator.style.pointerEvents = 'none';
    this.tiersContainerEl.appendChild(triangleIndicator);

    // 同时设置indicator-arrow的位置，跟随red-line-indicator
    if (this.indicatorArrowEl) {
      this.indicatorArrowEl.style.left = `${redLineLeft}%`;
      // 设置indicator-arrow的颜色跟随current-indicator的tier颜色
      this.indicatorArrowEl.style.borderTopColor = currentIndicatorBgColor;
    }
  }

  // 辅助方法：从entity获取属性，支持从data节点下获取
  getEntityAttribute(entity, attributeName) {
    if (!entity || !entity.attributes) return undefined;

    // 优先从顶层节点获取
    let value = entity.attributes[attributeName];

    // 如果顶层节点没有，尝试从data节点获取
    if (value === undefined && entity.attributes.data) {
      value = entity.attributes.data[attributeName];
    }

    return value;
  }

  // 辅助方法：判断是否使用data节点
  isUsingDataNode(entity) {
    return entity && entity.attributes && entity.attributes.data && entity.attributes.data.daylist;
  }

  async updateCard() {
    if (!this._hass || !this.entityId) return;

    // 获取实体
    const entity = this._hass.states[this.entityId];
    let balance = 0;
    
    // 检查实体是否可用（不存在或状态为unknown/unavailable）
    const isEntityUnavailable = !entity || entity.state === 'unknown' || entity.state === 'unavailable';
    
    if (isEntityUnavailable) {
      // 实体不可用，显示"--"
      if (this.balanceEl) {
        this.balanceEl.textContent = '--';
      }
      if (this.electricityPriceEl) {
        this.electricityPriceEl.textContent = '--';
      }
      if (this.remainingDaysEl) {
        this.remainingDaysEl.textContent = '--';
      }
      if (this.remainingDaysDateEl) {
        this.remainingDaysDateEl.textContent = '';
      }
      
      // data-container中三个按钮的用量和金额显示为"--"
      if (this.currentMonthElectricityEl) this.currentMonthElectricityEl.textContent = '--';
      if (this.currentMonthCostEl) this.currentMonthCostEl.textContent = '--';
      if (this.lastMonthElectricityEl) this.lastMonthElectricityEl.textContent = '--';
      if (this.lastMonthCostEl) this.lastMonthCostEl.textContent = '--';
      if (this.yearElectricityEl) this.yearElectricityEl.textContent = '--';
      if (this.yearCostEl) this.yearCostEl.textContent = '--';
      
      // tiers-container中的阶梯值和阶梯单价显示为"--"
      if (this.tier1RangeEl) this.tier1RangeEl.textContent = '--';
      if (this.tier1PriceEl) this.tier1PriceEl.textContent = '--';
      if (this.tier2RangeEl) this.tier2RangeEl.textContent = '--';
      if (this.tier2PriceEl) this.tier2PriceEl.textContent = '--';
      if (this.tier3RangeEl) this.tier3RangeEl.textContent = '--';
      if (this.tier3PriceEl) this.tier3PriceEl.textContent = '--';
      
      // current-indicator中的阶梯值和合计用电值显示为"--"
      if (this.currentTierEl) this.currentTierEl.textContent = '--';
      if (this.currentUsageEl) this.currentUsageEl.textContent = '--';
      
      // 将阶梯指示器移动到最左侧
      if (this.currentIndicatorEl) {
        this.currentIndicatorEl.style.left = '0%';
        this.currentIndicatorEl.style.transform = 'none';
        // 移除阶梯样式类，保持默认样式
        this.currentIndicatorEl.className = 'current-indicator';
      }
      
      // 将indicator-arrow也移动到最左侧
      if (this.indicatorArrowEl) {
        this.indicatorArrowEl.style.left = '0%';
        this.indicatorArrowEl.style.transform = 'none';
      }
      
      // 移除红色竖线和倒三角指示器
      if (this.tiersContainerEl) {
        const redLines = this.tiersContainerEl.querySelectorAll('.red-line-indicator');
        redLines.forEach(line => line.remove());
        const triangles = this.tiersContainerEl.querySelectorAll('.current-indicator-triangle');
        triangles.forEach(triangle => triangle.remove());
      }
      
      return;
    }
    
    if (entity) {
      // 优先从entity.state获取余额，如果state不是数值，则尝试从data节点获取
      balance = parseFloat(entity.state);
      if (isNaN(balance)) {
        // 如果state不是数值，尝试从data.balance获取
        balance = parseFloat(this.getEntityAttribute(entity, 'balance')) || 0;
      }
      this.balanceEl.textContent = balance.toFixed(2);

      // 【重要】当 utility_type 为 'ele' 时，根据"预付费"字段动态显示标签
      if (this.utilityType === 'ele' && this.balanceLabelEl) {
        // 从实体顶层节点获取"预付费"字段
        let isPrepaid = this.getEntityAttribute(entity, '预付费');
        
        // 如果顶层节点没有，尝试从data节点的"预付费"字段获取
        if (!isPrepaid && entity.attributes && entity.attributes.data) {
          isPrepaid = entity.attributes.data['预付费'];
        }
        
        if (isPrepaid === '是') {
          this.balanceLabelEl.textContent = '账户余额';
        } else {
          this.balanceLabelEl.textContent = '当期账单';
        }
      } else if (this.utilityType !== 'ele' && this.balanceLabelEl) {
        // 当不为电力类型时，显示为"账户余额"
        this.balanceLabelEl.textContent = '账户余额';
      }
    }

    // 异步更新缴费次数角标
    this._updatePayCountBadge();

    // 更新剩余天数
    if (entity && entity.attributes) {
      let remainingDays = 0;

      // 当 utility_type 为 'ele' 时，从 entity 的"剩余天数"获取
      if (this.utilityType === 'ele') {
        const daysValue = this.getEntityAttribute(entity, '剩余天数');
        if (daysValue !== undefined) {
          remainingDays = parseInt(daysValue, 10) || 0;
        }
      } else if (this.utilityType !== 'ele') {
        // 当 utility_type 不是 'ele' 时，根据近30天平均使用金额计算剩余天数
        let daylist = this.getEntityAttribute(entity, 'daylist') || [];
        if (typeof daylist === 'string') {
          try {
            daylist = JSON.parse(daylist);
          } catch (e) {
            console.warn('解析 daylist 失败:', e);
            daylist = [];
          }
        }

        // 获取近30天的数据（daylist前面是最新的）
        if (daylist && daylist.length > 0) {
          const recent30Days = daylist.slice(0, 30);
          const mapping = this.fieldMapping || {};

          // 根据utility_type确定金额字段
          let amountField;
          if (this.utilityType === 'gas') {
            amountField = mapping.amount || 'e_gas';
          } else if (this.utilityType === 'water') {
            amountField = mapping.amount || 'money';
          } else {
            amountField = mapping.amount || 'cost';
          }

          // 计算近30天总金额
          let totalAmount = 0;
          let validDays = 0;

          recent30Days.forEach(item => {
            const amount = parseFloat(item[amountField]);
            if (!isNaN(amount) && amount > 0) {
              totalAmount += amount;
              validDays++;
            }
          });

          // 计算平均金额
          if (validDays > 0) {
            const averageAmount = totalAmount / validDays;
            // 计算剩余天数 = 余额 / 平均金额，取整
            if (averageAmount > 0) {
              remainingDays = Math.floor(balance / averageAmount);
              this.debugLog(`近${validDays}天平均金额: ${averageAmount.toFixed(2)}, 余额: ${balance.toFixed(2)}, 计算剩余天数: ${remainingDays}`);
            }
          }
        }
      }

      // 更新剩余天数显示
      if (this.remainingDaysEl) {
        this.remainingDaysEl.textContent = remainingDays;
      }
      
      // 计算并显示剩余天数对应的日期
      if (this.remainingDaysDateEl && remainingDays > 0) {
        const today = new Date();
        const futureDate = new Date(today.getTime() + remainingDays * 24 * 60 * 60 * 1000);
        const month = futureDate.getMonth() + 1; // getMonth() 返回 0-11
        const day = futureDate.getDate();
        this.remainingDaysDateEl.textContent = `(${month}.${day})`;
      } else if (this.remainingDaysDateEl) {
        this.remainingDaysDateEl.textContent = '';
      }
    }
    
    // 获取 daylist 数据用于阶梯计算
    let daylist = [];
    if (entity && entity.attributes) {
      daylist = this.getEntityAttribute(entity, 'daylist') || [];
      if (typeof daylist === 'string') {
        try {
          daylist = JSON.parse(daylist);
        } catch (e) {
          console.warn('解析 daylist 失败:', e);
          daylist = [];
        }
      }
    }
    
    // 如果标准数据还没有加载，先加载数据
    if (!this.historicalDataLoaded) {
      this.loadDataForCurrentUser();
      return;
    }

    // 从标准格式获取本月数据
    const currentMonthStandard = this.getCurrentMonthStandardData();
    this.currentMonthElectricityEl.textContent = currentMonthStandard.total_usage.toFixed(1);
    this.currentMonthCostEl.textContent = currentMonthStandard.total_amount.toFixed(1);
    this.currentMonthEleUnitEl.textContent = currentMonthStandard.unit;
    this.currentMonthCostUnitEl.textContent = '元';
    
    // 更新本月分时用电条（从标准格式提取）
    const currentMonthDistribution = this.extractTimeDistributionFromStandard(currentMonthStandard);
    this.createTimeDistributionBar(currentMonthDistribution, this.currentMonthDistributionEl, this.currentMonthLabelsEl);
    
    // 更新上月数据（从标准格式获取）
    const lastMonthStandard = this.getLastMonthStandardData();
    this.lastMonthElectricityEl.textContent = lastMonthStandard.total_usage.toFixed(1);
    this.lastMonthCostEl.textContent = lastMonthStandard.total_amount.toFixed(1);
    this.lastMonthEleUnitEl.textContent = lastMonthStandard.unit;
    this.lastMonthCostUnitEl.textContent = '元';
    
    // 更新上月分时用电条（从标准格式提取）
    const lastMonthDistribution = this.extractTimeDistributionFromStandard(lastMonthStandard);
    this.createTimeDistributionBar(lastMonthDistribution, this.lastMonthDistributionEl, this.lastMonthLabelsEl);
    
    // 更新年度数据（从标准格式获取）
    const currentYearStandard = this.getCurrentYearStandardData();
    const yearValue = currentYearStandard.time || new Date().getFullYear().toString();
    this.currentYearEl.textContent = yearValue;
    
    this.yearElectricityEl.textContent = currentYearStandard.total_usage.toFixed(1);
    this.yearCostEl.textContent = currentYearStandard.total_amount.toFixed(1);
    this.yearEleUnitEl.textContent = currentYearStandard.unit;
    this.yearCostUnitEl.textContent = '元';
    
    // 更新年度分时用电条（从标准格式提取）
    const yearDistribution = this.extractTimeDistributionFromStandard(currentYearStandard);
    this.createTimeDistributionBar(yearDistribution, this.yearDistributionEl, this.yearLabelsEl);
    
    // 更新趋势箭头（本月同比、本年同比）
    this.updateTrendArrows();
    
    // 计算并更新阶梯电价
    let currentPeriodUsage = 0;

    // 当 utility_type 为 'ele' 时，从 entity 的"计费标准"节点获取数据
    if (this.utilityType === 'ele' && this._hass && entity) {
      const billingStandard = this.getBillingStandardObject(entity);
      if (billingStandard) {
        // === 根据计费标准类型动态选择字段名 ===
        const billingStandardType = billingStandard['计费标准'] || '';
        const isMonthlyTier = billingStandardType.includes('月阶梯');
        const accumulatedUsageField = isMonthlyTier ? '月阶梯累计用电量' : '年阶梯累计用电量';
        
        currentPeriodUsage = billingStandard[accumulatedUsageField] !== undefined ?
          parseFloat(billingStandard[accumulatedUsageField]) : 0;
      }
    }

    // 如果没有计费标准或不是电力类型，使用 daylist 计算
    if (currentPeriodUsage === 0) {
      currentPeriodUsage = this.calculatePeriodUsageFromDaylist(daylist);
      this.debugLog('从 daylist 计算当前周期用电量:', currentPeriodUsage);
    }
    
    // 延迟更新阶梯指示器，确保DOM已经渲染完成
    // 使用 setTimeout 给予更充足的时间确保DOM和样式都准备好
    setTimeout(() => {
      this.updateTierIndicator(currentPeriodUsage);
    }, 150);
    
    // 更新阶梯显示（确保单位从统一数据格式中获取）
    this.updateTierDisplay();
    
    // 更新主题（以便实时响应开关实体的状态变化）
    this.updateTheme(this._config);
    
    // 延迟应用隐藏配置，确保动态元素已创建
    requestAnimationFrame(() => {
      this.applyHiddenConfig();
    });
  }

  // 定义卡片配置架构
  static getStubConfig() {
    return {
      entity: 'sensor.electricity_info',
      name: '用电信息',
      // 主题配置 (不配置时自动根据时间切换: 白天light, 晚上dark)
      theme: undefined
    };
  }
}

// 注册自定义元素 - 使用更安全的注册方式
try {
  if (!customElements.get('electricity-info-card')) {
    customElements.define('electricity-info-card', ElectricityInfoCard);
  }
} catch (error) {
  // 如果注册失败（例如已经注册过），忽略错误
  console.warn('Custom element registration warning:', error.message);
}

// 告诉Home Assistant这个卡片类型
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'electricity-info-card',
  name: '用电信息卡片',
  description: '展示水电气使用量、缴费的卡片，显示各类图表信息，支持自定义阶梯、计费周期、设备运行统计（时长、电费）、主题切换和控制各项显示',
  preview: true
});
