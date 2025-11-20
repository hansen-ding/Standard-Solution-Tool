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
