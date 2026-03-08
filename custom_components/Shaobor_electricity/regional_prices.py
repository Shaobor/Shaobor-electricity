"""Regional electricity price configuration based on area code."""

# 地区电价配置表
# 键：地区代码前2位（省级）或前4位（市级）
# 值：(省份名称, 第1档上限, 第2档上限, 第1档电价, 第2档电价, 第3档电价)

REGIONAL_PRICES = {
    # 北京市 (1101)
    "11": {
        "name": "北京市",
        "ladder_level_1": 2880,
        "ladder_level_2": 4800,
        "ladder_price_1": 0.4883,
        "ladder_price_2": 0.5383,
        "ladder_price_3": 0.7883,
    },
    # 上海市 (3101)
    "31": {
        "name": "上海市",
        "ladder_level_1": 3120,
        "ladder_level_2": 4800,
        "ladder_price_1": 0.617,
        "ladder_price_2": 0.667,
        "ladder_price_3": 0.917,
    },
    # 天津市 (1201)
    "12": {
        "name": "天津市",
        "ladder_level_1": 2760,
        "ladder_level_2": 4800,
        "ladder_price_1": 0.49,
        "ladder_price_2": 0.54,
        "ladder_price_3": 0.79,
    },
    # 重庆市 (5001)
    "50": {
        "name": "重庆市",
        "ladder_level_1": 2400,
        "ladder_level_2": 4800,
        "ladder_price_1": 0.52,
        "ladder_price_2": 0.57,
        "ladder_price_3": 0.82,
    },
    # 河北省 (13xx)
    "13": {
        "name": "河北省",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.52,
        "ladder_price_2": 0.57,
        "ladder_price_3": 0.82,
    },
    # 山西省 (14xx)
    "14": {
        "name": "山西省",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.477,
        "ladder_price_2": 0.527,
        "ladder_price_3": 0.777,
    },
    # 内蒙古 (15xx)
    "15": {
        "name": "内蒙古",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.45,
        "ladder_price_2": 0.50,
        "ladder_price_3": 0.75,
    },
    # 辽宁省 (21xx)
    "21": {
        "name": "辽宁省",
        "ladder_level_1": 2040,
        "ladder_level_2": 3240,
        "ladder_price_1": 0.50,
        "ladder_price_2": 0.55,
        "ladder_price_3": 0.80,
    },
    # 吉林省 (22xx)
    "22": {
        "name": "吉林省",
        "ladder_level_1": 2040,
        "ladder_level_2": 3240,
        "ladder_price_1": 0.525,
        "ladder_price_2": 0.575,
        "ladder_price_3": 0.825,
    },
    # 黑龙江省 (23xx)
    "23": {
        "name": "黑龙江省",
        "ladder_level_1": 2040,
        "ladder_level_2": 3240,
        "ladder_price_1": 0.51,
        "ladder_price_2": 0.56,
        "ladder_price_3": 0.81,
    },
    # 江苏省 (32xx)
    "32": {
        "name": "江苏省",
        "ladder_level_1": 2760,
        "ladder_level_2": 4800,
        "ladder_price_1": 0.5283,
        "ladder_price_2": 0.5783,
        "ladder_price_3": 0.8283,
    },
    # 浙江省 (33xx)
    "33": {
        "name": "浙江省",
        "ladder_level_1": 2760,
        "ladder_level_2": 4800,
        "ladder_price_1": 0.538,
        "ladder_price_2": 0.588,
        "ladder_price_3": 0.838,
    },
    # 安徽省 (34xx)
    "34": {
        "name": "安徽省",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.5653,
        "ladder_price_2": 0.6153,
        "ladder_price_3": 0.8653,
    },
    # 福建省 (35xx)
    "35": {
        "name": "福建省",
        "ladder_level_1": 2400,
        "ladder_level_2": 4800,
        "ladder_price_1": 0.4983,
        "ladder_price_2": 0.5483,
        "ladder_price_3": 0.7983,
    },
    # 江西省 (36xx)
    "36": {
        "name": "江西省",
        "ladder_level_1": 2400,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.60,
        "ladder_price_2": 0.65,
        "ladder_price_3": 0.90,
    },
    # 山东省 (37xx)
    "37": {
        "name": "山东省",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.5469,
        "ladder_price_2": 0.5969,
        "ladder_price_3": 0.8469,
    },
    # 河南省 (41xx)
    "41": {
        "name": "河南省",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.56,
        "ladder_price_2": 0.61,
        "ladder_price_3": 0.86,
    },
    # 湖北省 (42xx)
    "42": {
        "name": "湖北省",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.558,
        "ladder_price_2": 0.608,
        "ladder_price_3": 0.858,
    },
    # 湖南省 (43xx)
    "43": {
        "name": "湖南省",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.588,
        "ladder_price_2": 0.638,
        "ladder_price_3": 0.888,
    },
    # 广东省 (44xx)
    "44": {
        "name": "广东省",
        "ladder_level_1": 2400,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.68,
        "ladder_price_2": 0.73,
        "ladder_price_3": 0.98,
    },
    # 广西 (45xx)
    "45": {
        "name": "广西",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.5283,
        "ladder_price_2": 0.5783,
        "ladder_price_3": 0.8283,
    },
    # 海南省 (46xx)
    "46": {
        "name": "海南省",
        "ladder_level_1": 2400,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.5983,
        "ladder_price_2": 0.6483,
        "ladder_price_3": 0.8983,
    },
    # 四川省 (51xx)
    "51": {
        "name": "四川省",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.5224,
        "ladder_price_2": 0.6224,
        "ladder_price_3": 0.8224,
    },
    # 贵州省 (52xx)
    "52": {
        "name": "贵州省",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.4573,
        "ladder_price_2": 0.5073,
        "ladder_price_3": 0.7573,
    },
    # 云南省 (53xx)
    "53": {
        "name": "云南省",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.45,
        "ladder_price_2": 0.50,
        "ladder_price_3": 0.80,
    },
    # 西藏 (54xx)
    "54": {
        "name": "西藏",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.35,
        "ladder_price_2": 0.40,
        "ladder_price_3": 0.65,
    },
    # 陕西省 (61xx)
    "61": {
        "name": "陕西省",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.4983,
        "ladder_price_2": 0.5483,
        "ladder_price_3": 0.7983,
    },
    # 甘肃省 (62xx)
    "62": {
        "name": "甘肃省",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.51,
        "ladder_price_2": 0.56,
        "ladder_price_3": 0.81,
    },
    # 青海省 (63xx)
    "63": {
        "name": "青海省",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.3771,
        "ladder_price_2": 0.4271,
        "ladder_price_3": 0.6771,
    },
    # 宁夏 (64xx)
    "64": {
        "name": "宁夏",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.4486,
        "ladder_price_2": 0.4986,
        "ladder_price_3": 0.7486,
    },
    # 新疆 (65xx)
    "65": {
        "name": "新疆",
        "ladder_level_1": 2160,
        "ladder_level_2": 3600,
        "ladder_price_1": 0.39,
        "ladder_price_2": 0.44,
        "ladder_price_3": 0.69,
    },
}


def get_region_price_config(cons_no: str) -> dict | None:
    """
    根据户号获取地区电价配置
    
    Args:
        cons_no: 电力户号
        
    Returns:
        地区电价配置字典，如果找不到则返回 None
    """
    if not cons_no or len(cons_no) < 2:
        return None
    
    # 提取前2位地区代码
    area_code = cons_no[:2]
    
    return REGIONAL_PRICES.get(area_code)


def get_region_name(cons_no: str) -> str:
    """
    根据户号获取地区名称
    
    Args:
        cons_no: 电力户号
        
    Returns:
        地区名称，如果找不到则返回"未知地区"
    """
    config = get_region_price_config(cons_no)
    return config["name"] if config else "未知地区"
