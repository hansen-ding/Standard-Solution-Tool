"""
算法模块：包含所有业务逻辑和API调用
"""
import requests
from datetime import date


def to_kw(value, unit):
    """转换为 kW"""
    if value == "" or value is None:
        return None
    v = float(value)
    return v * 1000 if unit == "MW" else v


def to_kwh(value, unit):
    """转换为 kWh"""
    if value == "" or value is None:
        return None
    v = float(value)
    return v * 1000 if unit == "MWh" else v


def format_c_rate(c_rate):
    """智能格式化 C-rate，避免不必要的尾随零，最多保留3位小数"""
    if c_rate is None:
        return ""
    
    # 处理接近整数的情况
    if abs(c_rate - round(c_rate)) < 1e-6:
        return f"{int(round(c_rate))}C"
    
    # 处理常见分数，保留必要的小数位，但最多3位
    for decimals in [1, 2, 3]:
        formatted = f"{c_rate:.{decimals}f}"
        formatted = formatted.rstrip('0').rstrip('.')
        
        try:
            formatted_value = float(formatted)
            if abs(formatted_value - c_rate) < 1e-6:
                return f"{formatted}C"
        except ValueError:
            continue
    
    # 如果上述方法都不行，强制保留最多3位小数
    formatted = f"{c_rate:.3f}".rstrip('0').rstrip('.')
    return f"{formatted}C"


def calculate_c_rate(power_kw, capacity_kwh):
    """计算 C-rate: Power (kW) / Capacity (kWh)"""
    if power_kw is None or capacity_kwh is None or capacity_kwh == 0:
        return None
    return power_kw / capacity_kwh


def fetch_temperature(location):
    """
    使用 Open-Meteo Archive API 计算多年期"年极值的年均"：
    Max = mean(每年的 [当年每日最高气温的极大值])
    Min = mean(每年的 [当年每日最低气温的极小值])
    单位：°C
    
    返回: (max_temp, min_temp, tooltip) 或 (None, None, error_message)
    """
    if not location or not location.strip():
        return None, None, "Please enter a location"
    
    try:
        # 1) 地名 -> 经纬度
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1"
        geo = requests.get(geo_url, timeout=12).json()
        
        if "results" not in geo or not geo["results"]:
            return None, None, "Location not found"
        
        lat = geo["results"][0]["latitude"]
        lon = geo["results"][0]["longitude"]

        # 2) 设定统计年限：最近20个完整年份
        current_year = date.today().year
        start_year = current_year - 20
        start_date = f"{start_year}-01-01"
        end_date = f"{current_year-1}-12-31"

        # 3) 拉逐日历史最高/最低
        url = (
            "https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={lat}&longitude={lon}"
            f"&start_date={start_date}&end_date={end_date}"
            "&daily=temperature_2m_max,temperature_2m_min"
            "&timezone=auto"
        )
        data = requests.get(url, timeout=20).json()
        
        if "daily" not in data or "time" not in data["daily"]:
            return None, None, "Temperature data not available"

        times = data["daily"]["time"]
        tmax = data["daily"]["temperature_2m_max"]
        tmin = data["daily"]["temperature_2m_min"]

        # 4) 按年份聚合：每年 max(tmax) / min(tmin)
        yearly_maxes = {}
        yearly_mins = {}
        
        for d, hi, lo in zip(times, tmax, tmin):
            if hi is None or lo is None:
                continue
            y = int(d[:4])
            
            if y not in yearly_maxes or hi > yearly_maxes[y]:
                yearly_maxes[y] = hi
            if y not in yearly_mins or lo < yearly_mins[y]:
                yearly_mins[y] = lo

        if not yearly_maxes or not yearly_mins:
            return None, None, "Insufficient temperature data"

        # 5) 多年期均值
        mean_annual_max = round(sum(yearly_maxes.values()) / len(yearly_maxes), 2)
        mean_annual_min = round(sum(yearly_mins.values()) / len(yearly_mins), 2)

        tooltip = (
            f"Aggregated over {min(yearly_maxes)}–{max(yearly_maxes)} (years): "
            "Max = mean of each year's hottest-day high; "
            "Min = mean of each year's coldest-day low. Unit: °C"
        )
        
        return mean_annual_max, mean_annual_min, tooltip

    except Exception as e:
        return None, None, f"API error: {str(e)}"


def get_pcs_options(product: str, model: str = None, solution_type: str = None, discharge_rate: float = None):
    """
    根据产品/型号/方案类型/放电倍率返回 PCS 配置选项数据。

    参数:
        product: 产品类型（例如 EDGE / grid5015 / Utility / C&I / Residential）
        model: 型号（示例："760kWh"，或区间 676–507kWh）
        solution_type: 方案类型（AC / DC）
        discharge_rate: 放电倍率（C-rate，float）

    返回:
        List[Dict]: 每项包含以下键：
            - id
            - image
            - title
            - description
            - tooltip
    """
    base_assets = "images"

    def make_option(opt_id, img, title="配置", desc="推荐搭配", tip="点击查看详情", components: str = ""):
        return {
            "id": opt_id,
            "image": f"{base_assets}/{img}",
            "title": title,
            "description": desc,
            "tooltip": tip,
            "components": components,
        }

    p = (product or "").strip().lower()
    m = (model or "").strip().lower()
    st = (solution_type or "").strip().lower()

    # 业务规则：EDGE
    if p == "edge":
        # product=EDGE，solution type=DC -> A:760.png, B:760+DC.png
        if st == "dc":
            return [
                make_option("config_a", "760.png", "Config A", "EDGE DC 方案：基础 760", components="Gotion EDGE BESS"),
                make_option("config_b", "760+DC.png", "Config B", "EDGE DC 方案：760 + DC", components="Gotion EDGE BESS + Gotion DC Confluence Cabinet"),
            ]
        # product=EDGE, model=760kWh, solution type=AC -> A:760+DC+EPC.png, B:760+Dynapower.png
        if "760" in m and st == "ac":
            return [
                make_option("config_a", "760+DC+EPC.png", "Config A", "EDGE AC 方案：760 + DC + EPC", components="Gotion EDGE BESS + Gotion DC Confluence Cabinet + EPC Power CAB1000/AC-3L.2"),
                make_option("config_b", "760+Dynapower.png", "Config B", "EDGE AC 方案：760 + Dynapower", components="Gotion EDGE BESS + Dynapower MPS-125"),
            ]
        # product=EDGE, model=676到507kWh -> A:760+AC.png, B:760+Dynapower.png
        # 粗略判断型号字符串是否包含数值并位于 507–676 范围
        def parse_capacity_kwh(s):
            import re
            m = re.findall(r"(\d{3,4})", s)
            return float(m[0]) if m else None
        cap = parse_capacity_kwh(m)
        if cap is not None and 507 <= cap <= 676:
            return [
                make_option("config_a", "760+AC.png", "Config A", "EDGE：760 + AC", components="Gotion EDGE BESS + Gotion AC Confluence Cabinet"),
                make_option("config_b", "760+Dynapower.png", "Config B", "EDGE：760 + Dynapower", components="Gotion EDGE BESS + Dynapower MPS-125"),
            ]

    # 业务规则：grid5015
    if p == "grid5015":
        dr = discharge_rate if discharge_rate is not None else None
        # >0.25C <=0.5C 或 >0.125C <=0.25C -> A:5015+5160.png, B:5015+CAB1000.png
        if dr is not None and ((dr > 0.25 and dr <= 0.5) or (dr > 0.125 and dr <= 0.25)):
            return [
                make_option("config_a", "5015+5160.png", "Config A", "GRID5015：5015 + 5160", components="Gotion GRID5015 + Sineng EH-5160-HA-MR-US-34.5 Skid"),
                make_option("config_b", "5015+CAB1000.png", "Config B", "GRID5015：5015 + CAB1000", components="Gotion GRID5015 + EPC Power CAB1000/AC-3L.2 Skid"),
            ]
        # <=0.125C -> 仅一个配置 5015+4800.png
        if dr is not None and dr <= 0.125:
            return [
                make_option("config_a", "5015+4800.png", "Config", "GRID5015：5015 + 4800", components="Gotion GRID5015 + EH-4800-HA-MR-US-34.5"),
            ]

    # 其他产品沿用原默认 catalog
    base_assets = "images"

    # 不同产品的推荐文案与图片映射（示例）
    catalog = {
        "Utility": [
            {
                "id": "pcs_hv",
                "image": f"{base_assets}/pcs_hv.png",
                "title": "高压并网 PCS",
                "description": "适用于大型并网场景，支持高功率密度与并网合规特性。",
                "tooltip": "推荐用于集中式电站与长时间并网运行。",
            },
            {
                "id": "pcs_mv",
                "image": f"{base_assets}/pcs_mv.png",
                "title": "中压并网 PCS",
                "description": "兼顾成本与性能，适合中大型项目与园区级应用。",
                "tooltip": "当并网电压等级在中压侧时的优选方案。",
            },
        ],
        "C&I": [
            {
                "id": "pcs_ci_ac",
                "image": f"{base_assets}/pcs_ci_ac.png",
                "title": "工商业 AC 耦合 PCS",
                "description": "便于既有工厂/园区改造，部署灵活，维护简便。",
                "tooltip": "改造存量配电系统的常见选择。",
            },
            {
                "id": "pcs_ci_dc",
                "image": f"{base_assets}/pcs_ci_dc.png",
                "title": "工商业 DC 耦合 PCS",
                "description": "适合与光伏直流侧耦合，提高系统效率与能量利用率。",
                "tooltip": "新建工商业光储系统的高效配置。",
            },
        ],
        "Residential": [
            {
                "id": "pcs_res_hybrid",
                "image": f"{base_assets}/pcs_res_hybrid.png",
                "title": "户用混合逆变器",
                "description": "集成 PV 与储能，提升自发自用与备电能力。",
                "tooltip": "适用于家庭与小型商铺的一体化方案。",
            },
            {
                "id": "pcs_res_ac",
                "image": f"{base_assets}/pcs_res_ac.png",
                "title": "户用 AC 并网逆变器",
                "description": "配合外置电池或不配储能的并网应用。",
                "tooltip": "入门级并网配置，安装简便。",
            },
        ],
    }

    # 归一化产品键（允许大小写/中英文别名扩展）
    key_map = {
        "utility": "Utility",
        "uti": "Utility",
        "ci": "C&I",
        "c&i": "C&I",
        "commercial": "C&I",
        "industrial": "C&I",
        "res": "Residential",
        "residential": "Residential",
    }

    normalized = (product or "").strip().lower()
    catalog_key = key_map.get(normalized, None)
    if catalog_key is None:
        # 未识别产品类型时的通用占位方案
        return [
            {
                "id": "pcs_generic_1",
                "image": f"{base_assets}/pcs_generic_1.png",
                "title": "并网型 PCS",
                "description": "通用并网应用场景，适配多种电压等级。",
                "tooltip": "默认占位内容，可根据产品类型细化。",
            },
            {
                "id": "pcs_generic_2",
                "image": f"{base_assets}/pcs_generic_2.png",
                "title": "独立微网 PCS",
                "description": "支持孤岛/微网运行，提高系统韧性。",
                "tooltip": "默认占位内容，可根据产品类型细化。",
            },
        ]

    return catalog[catalog_key]
