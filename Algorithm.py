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
    solution_type: str = 'DC',  # 直接用solution_type判定AC/DC
    bess_specs_sheet: int | str = 0,
) -> int:
    """
    Compute proposed number of BESS containers.
    新算法：根据 solution_type（AC/DC），用需求总量除以单柜 usable capacity，向上取整。
    - DC: usable = 100% DOD Energy × DOD × discharge_eff × calendar_degradation
    - AC: usable = 100% DOD Energy × DOD × discharge_eff × ac_conversion × calendar_degradation
    """
    try:
        specs = get_bess_specs_for(product, model, sheet=bess_specs_sheet)
        # 获取单柜100% DOD能量
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
        if energy_kwh is None or energy_kwh <= 0:
            return 0

        # ---------- 新增：根据 product 计算 calendar_degradation ----------
        p = (product or '').strip().upper()
        if p == 'EDGE':
            calendar_degradation = 0.9565
        elif p == 'GRID5015':
            calendar_degradation = 0.9808
        else:
            calendar_degradation = 1.0  # 不认识的产品先不衰减
        # ------------------------------------------------------------------

        # 默认参数
        dod = 0.95
        discharge_rate = 0.5  # 可根据实际传参
        ac_conversion = 0.9732

        # 放电效率
        if discharge_rate <= 0.25:
            discharge_eff = 0.965
        elif discharge_rate <= 0.5:
            discharge_eff = 0.95
        else:
            discharge_eff = 0.95

        # 直接用solution_type判定AC/DC
        solution_mode = (solution_type or '').strip().upper()
        if solution_mode == 'AC':
            usable = (
                energy_kwh
                * dod
                * discharge_eff
                * ac_conversion
                * calendar_degradation   # ✅ AC情形也乘日历衰减
            )
        else:
            usable = (
                energy_kwh
                * dod
                * discharge_eff
                * calendar_degradation   # ✅ DC情形乘日历衰减
            )

        if usable <= 0:
            return 0

        from math import ceil
        return max(0, int(ceil((capacity_required_kwh or 0.0) / usable)))
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


def compute_pcs_count(
    product: str,
    option_tag: str,
    proposed_bess: int,
    power_kw: float | None,
    discharge_rate: float | str | None,
    bess_specs_sheet: int | str = 0,
) -> str:
    """Compute Proposed Number of PCS per configuration.
    Handles discharge_rate provided as float or string like '0.5C'.
    """
    from math import ceil
    
    tag = (option_tag or '').strip().lower()
    p = (product or '').strip().upper()
    # Normalize discharge rate to float
    dr_val: float = 0.0
    try:
        if isinstance(discharge_rate, (int, float)):
            dr_val = float(discharge_rate)
        else:
            s = str(discharge_rate or '').strip().upper()
            if s.endswith('C'):
                s = s[:-1]
            dr_val = float(s) if s else 0.0
    except Exception:
        dr_val = 0.0
    # EDGE
    if p == 'EDGE':
        if tag in ('760', '760+dc'):
            return '-'
        if tag == '760+dc+epc':
            try:
                return str(max(0, ceil(((power_kw or 0.0) / 1043.0))))
            except Exception:
                return '0'
        if tag in ('760+dynapower', '760+ac'):
            try:
                return str(int(max(0, proposed_bess) * 2))
            except Exception:
                return '0'
        return '0'
    # GRID5015
    if p == 'GRID5015':
        try:
            if dr_val > 0.25 and dr_val <= 0.5:
                return str(max(0, ceil((proposed_bess or 0) / 2)))
            elif dr_val > 0.125 and dr_val <= 0.25:
                return str(max(0, ceil((proposed_bess or 0) / 4)))
            else:  # dr_val <= 0.125
                return str(max(0, ceil((proposed_bess or 0) / 6)))
        except Exception:
            return '0'
    return '0'


def compute_system_dc_usable_capacity(
    proposed_bess: int,
    energy_kwh_per_bess: float | None,
    product: str,
    capacity_unit: str = 'kWh',
    dod: float = 0.95,
    discharge_efficiency: float = 0.9732
) -> tuple[float | None, str]:
    """Compute System DC Usable Capacity.
    Formula: Proposed BESS × 100% DOD Energy × DOD × Discharge Efficiency × Calendar Degradation
    
    Parameters:
    - proposed_bess: Number of BESS containers
    - energy_kwh_per_bess: 100% DOD Energy per BESS (kWh)
    - product: Product type ('EDGE' or 'GRID5015')
    - capacity_unit: Output unit ('kWh' or 'MWh')
    - dod: Depth of Discharge, default 95%
    - discharge_efficiency: Discharge efficiency, default 97.32%
    
    Calendar Degradation:
    - EDGE: 95.65%
    - GRID5015: 98.08%
    
    Returns: (value, unit) or (None, unit) if cannot compute.
    """
    if energy_kwh_per_bess is None or energy_kwh_per_bess <= 0 or proposed_bess <= 0:
        return None, capacity_unit
    try:
        # Determine calendar degradation based on product
        p = (product or '').strip().upper()
        if p == 'EDGE':
            calendar_degradation = 0.9565
        elif p == 'GRID5015':
            calendar_degradation = 0.9808
        else:
            calendar_degradation = 1.0  # fallback
        
        total_kwh = (
            energy_kwh_per_bess 
            * proposed_bess 
            * dod 
            * discharge_efficiency 
            * calendar_degradation
        )
        
        if capacity_unit == 'MWh':
            return round(total_kwh / 1000.0, 3), 'MWh'
        else:
            return round(total_kwh, 3), 'kWh'
    except Exception:
        return None, capacity_unit


def compute_system_ac_usable_capacity(
    dc_usable_kwh: float | None,
    capacity_unit: str = 'kWh',
    discharge_efficiency: float = 0.9732
) -> tuple[float | None, str]:
    """Compute System AC Usable Capacity.
    Formula: DC Usable × Discharge Efficiency (97.32%)
    
    Parameters:
    - dc_usable_kwh: DC Usable Capacity in kWh
    - capacity_unit: Output unit ('kWh' or 'MWh')
    - discharge_efficiency: Discharge efficiency, default 97.32%
    
    Returns: (value, unit) or (None, unit) if cannot compute.
    """
    if dc_usable_kwh is None or dc_usable_kwh <= 0:
        return None, capacity_unit
    try:
        ac_usable_kwh = dc_usable_kwh * discharge_efficiency
        
        if capacity_unit == 'MWh':
            return round(ac_usable_kwh / 1000.0, 3), 'MWh'
        else:
            return round(ac_usable_kwh, 3), 'kWh'
    except Exception:
        return None, capacity_unit


def compute_system_rated_dc_power(
    dc_usable_kwh: float | None,
    discharge_rate: float | None,
    power_unit: str = 'kW'
) -> tuple[float | None, str]:
    """Compute System Rated DC Power.
    Formula: System DC Usable × Discharge Rate
    
    Parameters:
    - dc_usable_kwh: DC Usable Capacity in kWh
    - discharge_rate: Discharge rate (C-rate) as a float (e.g., 0.5 for 0.5C)
    - power_unit: Output unit ('kW' or 'MW')
    
    Returns: (value, unit) or (None, unit) if cannot compute.
    """
    if dc_usable_kwh is None or dc_usable_kwh <= 0 or discharge_rate is None or discharge_rate <= 0:
        return None, power_unit
    try:
        rated_dc_kw = dc_usable_kwh * discharge_rate
        
        if power_unit == 'MW':
            return round(rated_dc_kw / 1000.0, 3), 'MW'
        else:
            return round(rated_dc_kw, 3), 'kW'
    except Exception:
        return None, power_unit


def compute_system_rated_ac_power(
    ac_usable_kwh: float | None,
    discharge_rate: float | None,
    pcs_count: int | None,
    option_tag: str,
    power_unit: str = 'kW'
) -> tuple[float | None, str]:
    """Compute System Rated AC Power.
    
    Formula:
    - Default: AC Usable × Discharge Rate
    - Special cases (760+Dynapower, 760+AC): Number of PCS × 125 kW
      BUT if (Number of PCS × 125 kW) > (AC Usable × 0.5C), use default formula instead
    
    Parameters:
    - ac_usable_kwh: AC Usable Capacity in kWh
    - discharge_rate: Discharge rate (C-rate) as a float (e.g., 0.5 for 0.5C)
    - pcs_count: Number of PCS (for special cases)
    - option_tag: Configuration tag to identify special cases
    - power_unit: Output unit ('kW' or 'MW')
    
    Returns: (value, unit) or (None, unit) if cannot compute.
    """
    tag = (option_tag or '').strip().lower()
    
    # Special cases: 760+Dynapower and 760+AC
    if tag in ('760+dynapower', '760+ac'):
        if pcs_count is not None and pcs_count > 0 and ac_usable_kwh is not None and ac_usable_kwh > 0:
            try:
                special_formula_kw = pcs_count * 125.0
                # Threshold is 0.5C of AC Usable (equivalent to AC Usable / 2 hours = AC Usable * 0.5)
                threshold_kw = ac_usable_kwh * 0.5
                
                # If special formula exceeds threshold, use default formula
                if special_formula_kw > threshold_kw:
                    # Fall through to default case
                    pass
                else:
                    # Use special formula
                    if power_unit == 'MW':
                        return round(special_formula_kw / 1000.0, 3), 'MW'
                    else:
                        return round(special_formula_kw, 3), 'kW'
            except Exception:
                pass
    
    # Default case: AC Usable × Discharge Rate
    if ac_usable_kwh is None or ac_usable_kwh <= 0 or discharge_rate is None or discharge_rate <= 0:
        return None, power_unit
    try:
        rated_ac_kw = ac_usable_kwh * discharge_rate
        
        if power_unit == 'MW':
            return round(rated_ac_kw / 1000.0, 3), 'MW'
        else:
            return round(rated_ac_kw, 3), 'kW'
    except Exception:
        return None, power_unit


def get_degradation_curve(
    product: str,
    cycles_per_year: int,
    discharge_rate: float,
    xlsx_path: str = DEGRADATION_XLSX,
    sheet: int | str = 0,
    debug: bool = True
) -> dict:
    """
    Filter and load degradation curve data from Degradation.xlsx.
    
    Filtering rules:
    1. Cell: 300 for EDGE, 314 for GRID5015
    2. Cycle: find nearest match to cycles_per_year (e.g., 350 -> 365)
    3. P-rate: find nearest match to discharge_rate (e.g., 0.125 -> 0.125)
    
    Parameters:
    - product: 'EDGE' or 'GRID5015'
    - cycles_per_year: annual cycle count (e.g., 365)
    - discharge_rate: C-rate value (e.g., 0.5)
    - xlsx_path: path to Degradation.xlsx
    - sheet: sheet name or index
    - debug: if True, print debug info
    
    Returns:
    - dict with keys:
        - 'deg_0' to 'deg_20': cycle degradation factors
        - 'CD_0' to 'CD_24': calendar degradation factors
        - 'filter_info': dict with matched filter values
    """
    import numpy as np
    
    # Load degradation table
    df = load_degradation_table(xlsx_path, sheet)
    
    # Normalize column names (strip whitespace and convert to lowercase for matching)
    df.columns = [str(col).strip() for col in df.columns]
    col_map = {col.lower(): col for col in df.columns}
    
    # 1. Filter by Cell (300 for EDGE, 314 for GRID5015)
    p = (product or '').strip().upper()
    target_cell = 300 if p == 'EDGE' else 314
    
    # Find 'cell' column (case-insensitive)
    cell_col = col_map.get('cell')
    if not cell_col:
        raise KeyError(f"Column 'cell' not found in Degradation.xlsx. Available columns: {list(df.columns)}")
    # Find 'cell' column (case-insensitive)
    cell_col = col_map.get('cell')
    if not cell_col:
        raise KeyError(f"Column 'cell' not found in Degradation.xlsx. Available columns: {list(df.columns)}")
    
    df_filtered = df[df[cell_col] == target_cell].copy()
    
    if len(df_filtered) == 0:
        raise ValueError(f"No rows found with {cell_col}={target_cell} for product={product}")
    
    # 2. Filter by Cycle (find nearest match)
    cycle_col = col_map.get('cycle') or col_map.get('cycles/year')
    if not cycle_col:
        raise KeyError(f"Column 'cycle' not found in Degradation.xlsx. Available columns: {list(df_filtered.columns)}")
    # 2. Filter by Cycle (find nearest match)
    cycle_col = col_map.get('cycle') or col_map.get('cycles/year')
    if not cycle_col:
        raise KeyError(f"Column 'cycle' not found in Degradation.xlsx. Available columns: {list(df_filtered.columns)}")
    
    available_cycles = df_filtered[cycle_col].dropna().unique()
    nearest_cycle = min(available_cycles, key=lambda x: abs(x - cycles_per_year))
    
    df_filtered = df_filtered[df_filtered[cycle_col] == nearest_cycle].copy()
    
    if len(df_filtered) == 0:
        raise ValueError(f"No rows found with cycle={nearest_cycle}")
    
    # 3. Filter by P-rate (find nearest match)
    # Column name might be 'P-rate' or 'P rate' or similar
    prate_col = None
    for col in df_filtered.columns:
        if 'p' in col.lower() and 'rate' in col.lower():
            prate_col = col
            break
    
    if prate_col is None:
        raise KeyError("Column 'P-rate' (or similar) not found in Degradation.xlsx")
    
    available_prates = df_filtered[prate_col].dropna().unique()
    nearest_prate = min(available_prates, key=lambda x: abs(x - discharge_rate))
    
    df_filtered = df_filtered[df_filtered[prate_col] == nearest_prate].copy()
    
    if len(df_filtered) == 0:
        raise ValueError(f"No rows found with {prate_col}={nearest_prate}")
    
    # 4. Select first matching row
    if len(df_filtered) > 1 and debug:
        print(f"[DEBUG] Multiple rows matched filters, using first row")
    
    row = df_filtered.iloc[0]
    
    # 5. Extract deg_0 to deg_20 (look for '0 year', '1 year', etc.)
    deg_data = {}
    
    # Debug: print all column names to see what we have
    if debug:
        print(f"\n[DEBUG] All columns in filtered row: {list(row.index)}")
    
    for i in range(21):
        # Try multiple column name formats
        possible_names = [
            f'{i} year',
            f'{i}year',
            f'{i} yr',
            f'{i}yr',
            f'deg_{i}',
            f'{i}yr',  # without space
            f'{i} y',   # just 'y'
        ]
        
        value = None
        matched_col = None
        for col_name in possible_names:
            if col_name in row.index:
                value = float(row[col_name]) if pd.notna(row[col_name]) else None
                matched_col = col_name
                break
        
        if debug and i < 3:  # Only print first 3 for brevity
            print(f"[DEBUG] Year {i}: tried {possible_names}, matched '{matched_col}', value={value}")
        
        deg_data[f'deg_{i}'] = value
    
    # 6. Extract CD_0 to CD_24
    cd_data = {}
    for i in range(25):
        col_name = f'CD_{i}'
        if col_name in row.index:
            cd_data[col_name] = float(row[col_name]) if pd.notna(row[col_name]) else None
        else:
            cd_data[col_name] = None
    
    # 7. Prepare result
    result = {
        **deg_data,
        **cd_data,
        'filter_info': {
            'product': product,
            'target_cell': target_cell,
            'input_cycles_per_year': cycles_per_year,
            'matched_cycle': int(nearest_cycle),
            'input_discharge_rate': discharge_rate,
            'matched_prate': float(nearest_prate),
        }
    }
    
    # 8. Debug output
    if debug:
        print("\n" + "="*60)
        print("DEGRADATION CURVE DEBUG INFO")
        print("="*60)
        print(f"Product: {product}")
        print(f"Target Cell: {target_cell}")
        print(f"Input Cycles/Year: {cycles_per_year} → Matched: {int(nearest_cycle)}")
        print(f"Input P-rate: {discharge_rate} → Matched: {nearest_prate}")
        print("\n--- Cycle Degradation Factors (deg_0 to deg_20) ---")
        for i in range(21):
            val = deg_data.get(f'deg_{i}')
            print(f"Year {i:2d}: {val if val is not None else 'N/A'}")
        print("\n--- Calendar Degradation Factors (CD_0 to CD_24) ---")
        for i in range(25):
            val = cd_data.get(f'CD_{i}')
            print(f"Month {i:2d}: {val if val is not None else 'N/A'}")
        print("="*60 + "\n")
    
    return result


def compute_soh_percent(
    degradation_curve: dict,
    product: str,
) -> list:
    """
    Compute SOH% (State of Health) for years 0-20.
    
    Formula: SOH_r = deg_r × calendar_degradation
    
    Calendar Degradation:
    - EDGE (Cell 300): 95.65%
    - GRID5015 (Cell 314): 98.08%
    
    Parameters:
    - degradation_curve: dict returned by get_degradation_curve()
    - product: 'EDGE' or 'GRID5015'
    
    Returns:
    - list of 21 SOH values (as fractions, e.g., 0.85 = 85%)
    """
    # Determine calendar degradation based on product
    p = (product or '').strip().upper()
    if p == 'EDGE':
        calendar_degradation = 0.9565  # 95.65%
    elif p == 'GRID5015':
        calendar_degradation = 0.9808  # 98.08%
    else:
        calendar_degradation = 1.0  # fallback
    
    # Calculate SOH for each year
    soh_list = []
    for year in range(21):
        deg_key = f'deg_{year}'
        deg_val = degradation_curve.get(deg_key)
        
        if deg_val is None:
            soh_list.append(None)
        else:
            soh = float(deg_val) * calendar_degradation
            # Clamp to [0, 1] range
            soh = max(0.0, min(1.0, soh))
            soh_list.append(round(soh, 4))
    
    return soh_list


def compute_yearly_dc_nameplate(
    product: str,
    model: str | None,
    containers_list: list,
    capacity_unit: str = 'kWh',
) -> list:
    """
    Compute yearly DC Nameplate for years 0-20.
    
    Formula: DC_Nameplate[year] = 100% DOD Energy (kWh) × Containers_in_Service[year]
    
    Parameters:
    - product: 'EDGE' or 'GRID5015'
    - model: Model variant (e.g., '760kWh')
    - containers_list: List of 21 container counts (one per year, allows for augmentation)
    - capacity_unit: Output unit ('kWh' or 'MWh')
    
    Returns:
    - list of 21 DC Nameplate values (one per year)
    """
    try:
        # Get 100% DOD Energy from BESS.xlsx
        specs = get_bess_specs_for(product, model)
        energy_kwh = None
        
        # Try to find 100% DOD Energy
        for key in ('100% DOD Energy (kWh)', '100%DOD Energy (kWh)', '100% DOD Energy', 'Energy (kWh)'):
            if key in specs:
                try:
                    energy_kwh = float(str(specs[key]).replace(',', '').strip())
                    break
                except Exception:
                    pass
        
        if energy_kwh is None or energy_kwh <= 0:
            return [None] * 21
        
        # Calculate DC Nameplate for each year
        dc_nameplate_list = []
        for year in range(21):
            # Get container count for this year (supports augmentation)
            containers = containers_list[year] if year < len(containers_list) else containers_list[-1] if containers_list else 0
            try:
                containers = int(containers)
            except:
                containers = 0
            
            dc_nameplate = energy_kwh * containers
            
            # Convert to desired unit
            if capacity_unit == 'MWh':
                dc_nameplate = round(dc_nameplate / 1000.0, 2)
            else:
                dc_nameplate = round(dc_nameplate, 2)
            
            dc_nameplate_list.append(dc_nameplate)
        
        return dc_nameplate_list
    
    except Exception:
        return [None] * 21


def compute_yearly_dc_usable(
    product: str,
    model: str | None,
    containers_list: list,
    soh_list: list,
    capacity_unit: str = 'kWh',
    dod: float = 0.95,
    discharge_rate: float = 0.5,
) -> list:
    """
    Compute yearly DC Usable for years 0-20.
    
    Formula: DC_Usable[year] = 100% DOD Energy × Containers[year] × DOD × discharge_eff × SOH[year]
    
    Parameters:
    - product: 'EDGE' or 'GRID5015'
    - model: Model variant (e.g., '760kWh')
    - containers_list: List of 21 container counts (one per year, allows for augmentation)
    - soh_list: List of 21 SOH values (as fractions, e.g., 0.9565)
    - capacity_unit: Output unit ('kWh' or 'MWh')
    - dod: Depth of Discharge, default 95% (0.95)
    - discharge_rate: C-rate value (e.g., 0.5), used to determine discharge efficiency
    
    Discharge Efficiency:
    - 0.5C → 0.95 (95%)
    - Other → 0.965 (96.5%)
    
    Returns:
    - list of 21 DC Usable values (one per year)
    """
    try:
        # Get 100% DOD Energy from BESS.xlsx
        specs = get_bess_specs_for(product, model)
        energy_kwh = None
        
        # Try to find 100% DOD Energy
        for key in ('100% DOD Energy (kWh)', '100%DOD Energy (kWh)', '100% DOD Energy', 'Energy (kWh)'):
            if key in specs:
                try:
                    energy_kwh = float(str(specs[key]).replace(',', '').strip())
                    break
                except Exception:
                    pass
        
        if energy_kwh is None or energy_kwh <= 0:
            return [None] * 21
        
        # Determine discharge efficiency based on C-rate
        if discharge_rate is not None and discharge_rate <= 0.25:
            discharge_eff = 0.965
        elif discharge_rate is not None and discharge_rate <= 0.5:
            discharge_eff = 0.95
        else:
            discharge_eff = 0.95
        
        # Calculate DC Usable for each year
        dc_usable_list = []
        for year in range(21):
            # Get container count for this year (supports augmentation)
            containers = containers_list[year] if year < len(containers_list) else containers_list[-1] if containers_list else 0
            try:
                containers = int(containers)
            except:
                containers = 0
            
            # Get SOH for this year
            soh = soh_list[year] if year < len(soh_list) and soh_list[year] is not None else 1.0
            
            # Formula: energy × containers × DOD × discharge_eff × SOH
            dc_usable = energy_kwh * containers * dod * discharge_eff * soh
            
            # Convert to desired unit
            if capacity_unit == 'MWh':
                dc_usable = round(dc_usable / 1000.0, 2)
            else:
                dc_usable = round(dc_usable, 2)
            
            dc_usable_list.append(dc_usable)
        
        return dc_usable_list
    
    except Exception:
        return [None] * 21


def compute_yearly_ac_usable(
    product: str,
    model: str | None,
    containers_list: list,
    soh_list: list,
    capacity_unit: str = 'kWh',
    dod: float = 0.95,
    discharge_rate: float = 0.5,
    ac_conversion: float = 0.9732,
) -> list:
    """
    Compute yearly AC Usable for years 0-20.
    
    Formula: AC_Usable[year] = 100% DOD Energy × Containers[year] × DOD × discharge_eff × 0.9732 × SOH[year]
    
    Parameters:
    - product: 'EDGE' or 'GRID5015'
    - model: Model variant (e.g., '760kWh')
    - containers_list: List of 21 container counts (one per year, allows for augmentation)
    - soh_list: List of 21 SOH values (as fractions, e.g., 0.9565)
    - capacity_unit: Output unit ('kWh' or 'MWh')
    - dod: Depth of Discharge, default 95% (0.95)
    - discharge_rate: C-rate value (e.g., 0.5), used to determine discharge efficiency
    - ac_conversion: AC conversion efficiency, default 97.32% (0.9732)
    
    Discharge Efficiency:
    - 0.5C → 0.95 (95%)
    - Other → 0.965 (96.5%)
    
    Returns:
    - list of 21 AC Usable values (one per year)
    """
    try:
        # Get 100% DOD Energy from BESS.xlsx
        specs = get_bess_specs_for(product, model)
        energy_kwh = None
        
        # Try to find 100% DOD Energy
        for key in ('100% DOD Energy (kWh)', '100%DOD Energy (kWh)', '100% DOD Energy', 'Energy (kWh)'):
            if key in specs:
                try:
                    energy_kwh = float(str(specs[key]).replace(',', '').strip())
                    break
                except Exception:
                    pass
        
        if energy_kwh is None or energy_kwh <= 0:
            return [None] * 21
        
        # Determine discharge efficiency based on C-rate
        if discharge_rate is not None and discharge_rate <= 0.25:
            discharge_eff = 0.965
        elif discharge_rate is not None and discharge_rate <= 0.5:
            discharge_eff = 0.95
        else:
            discharge_eff = 0.95
        
        # Calculate AC Usable for each year
        ac_usable_list = []
        for year in range(21):
            # Get container count for this year (supports augmentation)
            containers = containers_list[year] if year < len(containers_list) else containers_list[-1] if containers_list else 0
            try:
                containers = int(containers)
            except:
                containers = 0
            
            # Get SOH for this year
            soh = soh_list[year] if year < len(soh_list) and soh_list[year] is not None else 1.0
            
            # Formula: energy × containers × DOD × discharge_eff × ac_conversion × SOH
            ac_usable = energy_kwh * containers * dod * discharge_eff * ac_conversion * soh
            
            # Convert to desired unit
            if capacity_unit == 'MWh':
                ac_usable = round(ac_usable / 1000.0, 2)
            else:
                ac_usable = round(ac_usable, 2)
            
            ac_usable_list.append(ac_usable)
        
        return ac_usable_list
    
    except Exception:
        return [None] * 21
