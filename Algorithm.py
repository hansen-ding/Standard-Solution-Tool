"""
算法模块：包含所有业务逻辑和API调用
"""
import requests
from datetime import date
import os
import pandas as pd
from math import ceil

# Data folder paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
BESS_XLSX = os.path.join(DATA_DIR, "BESS.xlsx")
DEGRADATION_XLSX = os.path.join(DATA_DIR, "Degradation.xlsx")


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
    Return PCS configuration options for EDGE and GRID5015 only.
    Each option includes: id, image, components, architecture, origin.
    """
    base_assets = "images"

    def make_option(opt_id, img, components: str = "", architecture: str = "", origin: str = ""):
        return {
            "id": opt_id,
            "image": f"{base_assets}/{img}",
            "components": components,
            "architecture": architecture,
            "origin": origin,
        }

    p = (product or "").strip().lower()
    m = (model or "").strip().lower()
    stype = (solution_type or "").strip().lower()

    # EDGE rules
    if p == "edge":
        if stype == "dc":
            return [
                make_option(
                    "config_a",
                    "760.png",
                    "Gotion EDGE BESS",
                    architecture="-",
                    origin="China",
                ),
                make_option(
                    "config_b",
                    "760+DC.png",
                    "Gotion EDGE BESS + Gotion DC Confluence Cabinet",
                    architecture="Centralized System",
                    origin="China",
                ),
            ]
        if "760" in m and stype == "ac":
            return [
                make_option(
                    "config_a",
                    "760+DC+EPC.png",
                    "Gotion EDGE BESS + Gotion DC Confluence Cabinet + EPC Power CAB1000/AC-3L.2",
                    architecture="Centralized System",
                    origin="BESS: China, PCS: USA",
                ),
                make_option(
                    "config_b",
                    "760+Dynapower.png",
                    "Gotion EDGE BESS + Dynapower MPS-125",
                    architecture="String System",
                    origin="BESS: China, PCS: USA",
                ),
            ]
        # parse capacity range 507–676
        import re
        nums = re.findall(r"(\d{3,4})", m)
        cap = float(nums[0]) if nums else None
        if cap is not None and 507 <= cap <= 676:
            return [
                make_option(
                    "config_a",
                    "760+AC.png",
                    "Gotion EDGE BESS + Gotion AC Confluence Cabinet",
                    architecture="Centralized System",
                    origin="BESS: China, PCS: China",
                ),
                make_option(
                    "config_b",
                    "760+Dynapower.png",
                    "Gotion EDGE BESS + Dynapower MPS-125",
                    architecture="String System",
                    origin="BESS: China, PCS: USA",
                ),
            ]
        return []

    # GRID5015 rules
    if p == "grid5015":
        dr = discharge_rate if discharge_rate is not None else None
        if dr is not None and ((dr > 0.25 and dr <= 0.5) or (dr > 0.125 and dr <= 0.25)):
            return [
                make_option(
                    "config_a",
                    "5015+5160.png",
                    "Gotion GRID5015 + Sineng EH-5160-HA-MR-US-34.5 Skid",
                    architecture="Centralized System",
                    origin="BESS: China, PCS skid: China",
                ),
                make_option(
                    "config_b",
                    "5015+CAB1000.png",
                    "Gotion GRID5015 + EPC Power CAB1000/AC-3L.2 Skid",
                    architecture="Centralized System",
                    origin="BESS: China, PCS skid: USA",
                ),
            ]
        if dr is not None and dr <= 0.125:
            return [
                make_option(
                    "config_a",
                    "5015+4800.png",
                    "Gotion GRID5015 + EH-4800-HA-MR-US-34.5",
                    architecture="Centralized System",
                    origin="BESS: China, PCS skid: USA",
                ),
            ]
        return []

    # Default: no options
    return []


def load_bess_specs(xlsx_path: str = BESS_XLSX, sheet: int | str = 0) -> pd.DataFrame:
    """Load BESS specs workbook. Returns a DataFrame of the requested sheet."""
    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(f"BESS.xlsx not found: {xlsx_path}")
    return pd.read_excel(xlsx_path, sheet_name=sheet)


def load_degradation_table(xlsx_path: str = DEGRADATION_XLSX, sheet: int | str = 0) -> pd.DataFrame:
    """Load Degradation workbook. Returns a DataFrame of the requested sheet."""
    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(f"Degradation.xlsx not found: {xlsx_path}")
    return pd.read_excel(xlsx_path, sheet_name=sheet)


def _norm(s: str) -> str:
    return (str(s or "").replace(" ", "").replace("\u00a0", "").upper())

EDGE_MODEL_TO_HEADER = {
    "760kWh": "ESD1267-05P760-G",
    "676kWh": "ESD1126-05P676-G",
    "591kWh": "ESD985-05P591-G",
    "507kWh": "ESD844-05P507-G",
    "422kWh": "ESD704-05P422-G",
    "338kWh": "ESD563-05P338-G",
}
GRID5015_HEADER = "ESD1331-05P5015"

def get_bess_specs_for(product: str, model: str | None, xlsx_path: str = BESS_XLSX, sheet: int | str = 0) -> dict:
    """Load BESS.xlsx and return a dict of specs for the selected product/model column.
    Uses first column as keys and the matched header column as values.
    """
    df = load_bess_specs(xlsx_path, sheet)
    if df.shape[1] < 2:
        raise ValueError("BESS.xlsx: not enough columns")
    # Determine target header
    prodN = _norm(product)
    target_header = None
    if prodN == "EDGE":
        header = EDGE_MODEL_TO_HEADER.get((model or "").strip())
        target_header = header
    elif prodN == "GRID5015":
        target_header = GRID5015_HEADER
    else:
        raise ValueError(f"Unsupported product: {product}")
    if not target_header:
        raise ValueError(f"Missing or unsupported model for EDGE: {model}")
    # Find column index by normalized header match
    norm_cols = [_norm(str(c)) for c in df.columns]
    try:
        col_idx = norm_cols.index(_norm(target_header))
    except ValueError:
        raise KeyError(f"Column not found in BESS.xlsx: {target_header}")
    # Build dict from first column keys to target column values
    keys = df.iloc[:, 0]
    vals = df.iloc[:, col_idx]
    out: dict = {}
    for k, v in zip(keys, vals):
        key = None if pd.isna(k) else str(k).strip()
        val = None if pd.isna(v) else v
        if key:
            out[key] = val
    return out


def compute_proposed_bess_count(
    capacity_required_kwh: float,
    product: str,
    model: str | None,
    augmentation_mode: str,
    bess_specs_sheet: int | str = 0,
) -> int:
    """
    Compute proposed number of BESS containers.

    Rules:
    - If augmentation_mode in ['N/A', 'Augmentation'] -> direct sizing by single product capacity.
    - If augmentation_mode == 'Overbuild' -> placeholder branch (to be implemented upon your rule).

    Inputs:
    - capacity_required_kwh: target capacity (kWh) to meet.
    - product/model: used to fetch single product capacity from data/BESS.xlsx.
    - augmentation_mode: "", "N/A", "Augmentation", or "Overbuild".

    Returns integer count (ceil), minimum 0.
    """
    try:
        specs = get_bess_specs_for(product, model, sheet=bess_specs_sheet)
        # Attempt to locate single product energy capacity from specs.
        # Prefer keys commonly named like '100% DOD Energy (kWh)'; otherwise try a few variants.
        energy_kwh = None
        for key in (
            '100% DOD Energy (kWh)',
            '100%DOD Energy (kWh)',
            '100% DOD Energy',
            'Energy (kWh)',
        ):
            if key in specs:
                try:
                    energy_kwh = float(str(specs[key]).replace(',', '').strip())
                    break
                except Exception:
                    pass
        if energy_kwh is None:
            # Fallback: try first numeric value in the column
            for v in specs.values():
                try:
                    energy_kwh = float(str(v).replace(',', '').strip())
                    break
                except Exception:
                    continue
        if energy_kwh is None or energy_kwh <= 0:
            return 0

        mode = (augmentation_mode or '').strip()
        if mode in ('', 'N/A', 'Augmentation'):
            from math import ceil
            return max(0, int(ceil((capacity_required_kwh or 0.0) / energy_kwh)))
        elif mode == 'Overbuild':
            # TODO: Overbuild sizing rule to be provided; placeholder returns direct sizing for now.
            from math import ceil
            return max(0, int(ceil((capacity_required_kwh or 0.0) / energy_kwh)))
        else:
            # Unknown mode -> default direct sizing
            from math import ceil
            return max(0, int(ceil((capacity_required_kwh or 0.0) / energy_kwh)))
    except Exception:
        return 0


def compute_confluence_cabinet_count(product: str, model: str | None, option_id: str, proposed_bess: int) -> str:
    """Return Confluence Cabinet count per config.
    EDGE rules:
      - 760+DC, 760+DC+EPC -> ceil(BESS/5)
      - 760+AC -> ceil(BESS/3)
      - 760, 760+Dynapower -> "-"
    GRID5015: not applicable -> return None to indicate hide.
    """
    p = (product or '').strip().upper()
    if p == 'GRID5015':
        return None
    oid = (option_id or '').strip().lower()
    try:
        if oid in ('config_b') and model and 'dc' in (model or '').lower():
            pass  # fallback to image/title not reliable; we use explicit mapping below
    except Exception:
        pass
    # Map by image/component name embedded in option id is not sufficient; use heuristic by option image names
    # We expect option_id values: config_a/config_b. Use components string to infer type in UI if needed.
    # Here, we assume caller passes a derived tag of image name in option_id when available.
    # Implement by checking known keywords in option_id or model+solution pairing in UI.
    # For simplicity, let UI pass a tag; here we support image-like tags too.
    tag = oid  # ui can pass '760', '760+dc', '760+dc+epc', '760+ac', '760+dynapower'
    if tag in ('760+dc', '760+dc+epc'):
        return str(max(0, ceil((proposed_bess or 0) / 5)))
    if tag == '760+ac':
        return str(max(0, ceil((proposed_bess or 0) / 3)))
    if tag in ('760', '760+dynapower'):
        return '-'
    # Fallback: use solution_type hint via model string
    m = (model or '').lower()
    if 'ac' in m:
        return str(max(0, ceil((proposed_bess or 0) / 3)))
    if 'dc' in m:
        return str(max(0, ceil((proposed_bess or 0) / 5)))
    return '-'
