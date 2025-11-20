import json
import os
from typing import Dict, Optional, Tuple

import pandas as pd


# Files live alongside this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_JSON = os.path.join(BASE_DIR, "sizing_state.json")
SYSTEM_SPECS_XLSX = os.path.join(BASE_DIR, "System Specs.xlsx")


def load_state(path: str = STATE_JSON) -> Dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"State file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_product_and_model(state: Dict) -> Tuple[str, Optional[str]]:
    """Resolve product and model from state.

    Priority:
    - Interface section (product, edge_model)
    - Fallback to Degradation section (product)
    """
    product = None
    model = None

    if isinstance(state, dict):
        iface = state.get("interface", {}) or {}
        product = (iface.get("product") or "").strip()
        model = (iface.get("edge_model") or "").strip()
        if not product:
            degr = state.get("degradation", {}) or {}
            product = (degr.get("product") or "").strip()

    return product, (model or None)


def _normalize(s: str) -> str:
    return (s or "").replace(" ", "").replace("\u00a0", "").upper()


EDGE_MODELS_ORDER = [
    "760kWh",
    "676kWh",
    "591kWh",
    "507kWh",
    "422kWh",
    "338kWh",
]


def _find_target_column(df: pd.DataFrame, product: str, model: Optional[str]) -> int:
    """Return the zero-based column index to use for system specs.

    Rules:
    - EDGE: prefer a column whose header matches the model string exactly (case-insensitive);
      else map models to sequential columns starting at column B (index 1) for 760kWh, then C, D, ...
    - GRID3421: select column with header 'ESD1267-05P-3421' (flexible spacing/case);
    - GRID5015: select column with header 'ESD1331-05P5015' or 'ESD1331-05P-5015'.
    """
    cols = list(df.columns)
    norm_cols = [_normalize(str(c)) for c in cols]

    prodN = _normalize(product)

    if prodN == "EDGE":
        # 1) Try match by header name
        if model:
            modelN = _normalize(model)
            for i, cN in enumerate(norm_cols):
                if cN == modelN:
                    return i
        # 2) Fallback by fixed column positions (A=0, B=1, ...)
        if model in EDGE_MODELS_ORDER:
            idx_in_order = EDGE_MODELS_ORDER.index(model)
            col_idx = 1 + idx_in_order  # B starts at 1
            if col_idx < len(cols):
                return col_idx
        # If no model or out of range, default to B if available
        return 1 if len(cols) > 1 else 0

    if prodN == "GRID3421":
        targets = ["ESD1267-05P-3421", "ESD1267-05P3421", "1267-05P-3421", "1267-05P3421"]
        target_set = {_normalize(t) for t in targets}
        for i, cN in enumerate(norm_cols):
            if cN in target_set:
                return i
        raise KeyError("Column for GRID3421 not found (expected header like 'ESD1267-05P-3421').")

    if prodN == "GRID5015":
        targets = ["ESD1331-05P5015", "ESD1331-05P-5015", "1331-05P5015", "1331-05P-5015"]
        target_set = {_normalize(t) for t in targets}
        for i, cN in enumerate(norm_cols):
            if cN in target_set:
                return i
        raise KeyError("Column for GRID5015 not found (expected header like 'ESD1331-05P5015').")

    raise ValueError(f"Unsupported product: {product}")


def load_system_specs(product: str, model: Optional[str], xlsx_path: str = SYSTEM_SPECS_XLSX) -> Dict[str, object]:
    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(f"System spec not found: {xlsx_path}")

    # Read first sheet, keep all columns
    df = pd.read_excel(xlsx_path, sheet_name=0)

    if df.shape[1] < 2:
        raise ValueError("System spec: not enough columns to select from.")

    # Identify index/parameter name column (first column by convention)
    index_series = df.iloc[:, 0]
    # Determine target column
    col_idx = _find_target_column(df, product, model)
    value_series = df.iloc[:, col_idx]

    # Build result dict, skipping rows where both key and value are NaN/empty
    result: Dict[str, object] = {}
    for key, val in zip(index_series, value_series):
        k = None if pd.isna(key) else str(key).strip()
        v = None if pd.isna(val) else val
        if k is None and v is None:
            continue
        if k in (None, ""):
            # anonymous row -> skip
            continue
        result[k] = v

    return result


def load_selected_specs_from_state(state_path: str = STATE_JSON, xlsx_path: str = SYSTEM_SPECS_XLSX) -> Dict[str, object]:
    state = load_state(state_path)
    product, model = resolve_product_and_model(state)
    if not product:
        raise ValueError("No product found in state (expected interface.product or degradation.product)")
    return load_system_specs(product, model, xlsx_path)


def _to_float(val) -> Optional[float]:
    try:
        if val is None:
            return None
        s = str(val).strip()
        if s == "":
            return None
        return float(s)
    except Exception:
        return None


def compute_and_persist_system_outputs(state_path: str = STATE_JSON, xlsx_path: str = SYSTEM_SPECS_XLSX) -> Dict[str, Dict[str, object]]:
    """Compute & persist system output values (robust fallback so UI always shows numbers)."""
    state = load_state(state_path)
    # 1. Product & specs (fallback if missing excel or product)
    try:
        product, model = resolve_product_and_model(state)
    except Exception:
        product, model = None, None
    try:
        specs = load_system_specs(product or 'EDGE', model, xlsx_path)
    except Exception:
        specs = {"100% DOD Energy (kWh)": 760.0}
    energy_kwh = _to_float(specs.get("100% DOD Energy (kWh)")) or 0.0
    prodN = (product or '').strip().upper()
    # Unit rule: original logic converted GRID* to MWh – re‑implement safely
    if prodN in ("GRID3421", "GRID5015"):
        prod_value = energy_kwh / 1000.0
        prod_unit = "MWh"
    else:
        prod_value = energy_kwh
        prod_unit = "kWh"
    # 2. Inputs
    calc_inputs = (state.get('calculator', {}).get('inputs', {}) if isinstance(state.get('calculator'), dict) else {})
    bol_cabinets = _to_float(calc_inputs.get('bol_cabinets')) or 0.0
    system_nameplate = bol_cabinets * (prod_value or 0.0)
    # 3. DOD
    iface = state.get('interface') if isinstance(state.get('interface'), dict) else {}
    degr = state.get('degradation') if isinstance(state.get('degradation'), dict) else {}
    def pct_to_frac(s: Optional[str]):
        if not s: return None
        try: return float(str(s).replace('%','').strip())/100.0
        except Exception: return None
    dod = pct_to_frac(iface.get('dod')) or pct_to_frac(degr.get('dod')) or 1.0
    # 4. C-rate & discharge efficiency
    discharge_text = (iface.get('discharge') or '').strip(); c_rate=None
    if discharge_text.endswith('C'):
        try: c_rate=float(discharge_text[:-1])
        except Exception: c_rate=None
    if c_rate is None:
        c_rate = _to_float(degr.get('cp'))
    if c_rate is None: c_rate = 0.0
    discharge_eff = 0.95 if abs(c_rate-0.5) < 1e-6 else 0.965
    # 5. Calendar degradation factor (optional)
    cal_deg = 1.0
    try:
        cal_start = int((degr.get('calendar_start_month') or '').strip())
        if 0 <= cal_start <= 24:
            key = f"CD_{cal_start}"
            cdv = _to_float(degr.get(key))
            if cdv is not None and 0 < cdv <= 1.0:
                cal_deg = cdv
    except Exception:
        pass
    # 6. Usable capacities
    sys_dc_usable = prod_value * bol_cabinets * dod * discharge_eff * cal_deg if prod_value is not None else None
    sys_ac_usable = (sys_dc_usable * 0.9732) if sys_dc_usable is not None else None
    rated_dc_power = (sys_dc_usable * c_rate) if sys_dc_usable is not None else None
    rated_ac_power = (sys_ac_usable * c_rate) if sys_ac_usable is not None else None
    def rnd(v):
        try:
            return None if v is None else round(float(v), 3)
        except Exception:
            return None
    outputs = {
        'product_nameplate_capacity': {'value': rnd(prod_value), 'unit': prod_unit},
        'system_nameplate_capacity': {'value': rnd(system_nameplate), 'unit': prod_unit},
        'system_dc_usable_capacity': {'value': rnd(sys_dc_usable), 'unit': prod_unit},
        'system_ac_usable_capacity': {'value': rnd(sys_ac_usable), 'unit': prod_unit},
        'system_rated_dc_power': {'value': rnd(rated_dc_power), 'unit': prod_unit},
        'system_rated_ac_power': {'value': rnd(rated_ac_power), 'unit': prod_unit},
    }
    state.setdefault('system_output', {}).update(outputs)
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return outputs


def _get_aug_list_from_state(state: Dict) -> list:
    """Return a list of yearly augmentation quantities (years 0..20) from state.

    Accepts either:
    - state['calculator']['augmentation_plan'] as list[float] length 21,
    - or list[dict] with 'qty' or 'value'.
    Missing or malformed entries are treated as 0.0.
    """
    out = [0.0] * 21
    try:
        calc = state.get("calculator", {}) if isinstance(state.get("calculator"), dict) else {}
        plan = calc.get("augmentation_plan")
        if isinstance(plan, list):
            for i in range(min(21, len(plan))):
                v = plan[i]
                if isinstance(v, dict):
                    vv = v.get("qty", v.get("value"))
                else:
                    vv = v
                try:
                    out[i] = float(vv) if vv is not None and str(vv).strip() != "" else 0.0
                except Exception:
                    out[i] = 0.0
    except Exception:
        pass
    return out


def compute_and_persist_containers_in_service(state_path: str = STATE_JSON) -> list:
    """Compute cumulative Containers in Service for years 0..20 and persist to state.

    Formula: containers[r] = base_bol_cabinets + sum(aug[0..r]).
    """
    state = load_state(state_path)
    calc_inputs = (state.get("calculator", {}).get("inputs", {}) if isinstance(state.get("calculator"), dict) else {})
    try:
        base = float(calc_inputs.get("bol_cabinets") or 0.0)
    except Exception:
        base = 0.0

    aug = _get_aug_list_from_state(state)
    # cumulative sum
    containers: list = []
    s = 0.0
    for i in range(21):
        q = aug[i] if i < len(aug) else 0.0
        try:
            s += float(q)
        except Exception:
            s += 0.0
        containers.append(base + s)

    # Persist
    state.setdefault("calculator", {})
    yr = state["calculator"].get("yearly_result") if isinstance(state["calculator"], dict) else None
    if not isinstance(yr, dict):
        yr = {}
        state["calculator"]["yearly_result"] = yr
    yr["containers_in_service"] = containers

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    return containers


def compute_and_persist_soh_percent(state_path: str = STATE_JSON) -> list:
    """Compute SOH% per year 0..20 and persist to state.

    Formula: SOH_r = deg_r - (1 - CD_{calendar_start_month}).
    Values are stored as fractions (e.g., 0.85) and can be displayed as percentages in UI.
    """
    state = load_state(state_path)
    degr = state.get("degradation", {}) if isinstance(state.get("degradation"), dict) else {}

    # Calendar start month and CD_m
    cal_start_m = None
    try:
        cal_start_m = int((degr.get("calendar_start_month") or "").strip())
    except Exception:
        cal_start_m = None
    cd_val = None
    if cal_start_m is not None and 0 <= cal_start_m <= 24:
        cd_val = _to_float(degr.get(f"CD_{cal_start_m}"))

    offset = 0.0 if cd_val is None else (1.0 - float(cd_val))

    soh_list: list = []
    for r in range(21):
        dr = _to_float(degr.get(f"deg_{r}")) or 0.0
        soh = dr - offset
        soh_list.append(round(soh, 4))

    # Persist
    state.setdefault("calculator", {})
    yr = state["calculator"].get("yearly_result") if isinstance(state["calculator"], dict) else None
    if not isinstance(yr, dict):
        yr = {}
        state["calculator"]["yearly_result"] = yr
    yr["soh_percent"] = soh_list

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    return soh_list


def compute_and_persist_kwh_dc_nameplate(state_path: str = STATE_JSON, xlsx_path: str = SYSTEM_SPECS_XLSX) -> list:
    """Compute yearly kWh DC Nameplate for years 0..20 and persist to state.

    Rule: kWh DC Nameplate[r] = specs["100% DOD Energy (kWh)"] * containers_in_service[r].
    Always use kWh from specs (do not convert to MWh). Round to 2 decimals.
    """
    state = load_state(state_path)

    # Load 100% DOD Energy (kWh) from specs using resolved product/model
    product, model = resolve_product_and_model(state)
    specs = load_system_specs(product, model, xlsx_path)
    energy_kwh = _to_float(specs.get("100% DOD Energy (kWh)")) or 0.0

    # Ensure containers_in_service exists; if missing, compute it
    containers: list = []
    try:
        calc = state.get("calculator", {}) if isinstance(state.get("calculator"), dict) else {}
        yr = calc.get("yearly_result", {}) if isinstance(calc, dict) else {}
        lst = yr.get("containers_in_service") if isinstance(yr, dict) else None
        if isinstance(lst, list) and len(lst) >= 21:
            containers = lst[:21]
        else:
            # fall back to computing containers
            containers = compute_and_persist_containers_in_service(state_path)
    except Exception:
        containers = compute_and_persist_containers_in_service(state_path)

    # Compute per-year values and round
    values: list = []
    for i in range(21):
        c = 0.0
        try:
            c = float(containers[i] if i < len(containers) else containers[-1])
        except Exception:
            c = 0.0
        values.append(round(energy_kwh * c, 2))

    # Persist
    state = load_state(state_path)  # reload in case containers were updated
    state.setdefault("calculator", {})
    yr = state["calculator"].get("yearly_result") if isinstance(state["calculator"], dict) else None
    if not isinstance(yr, dict):
        yr = {}
        state["calculator"]["yearly_result"] = yr
    yr["kwh_dc_nameplate"] = values

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    return values


def compute_and_persist_kwh_dc_usable(state_path: str = STATE_JSON, xlsx_path: str = SYSTEM_SPECS_XLSX) -> list:
    """Compute yearly kWh DC Usable (years 0..20) based on product capacity and containers.

    Correct Rule:
        Let product_energy = specs["100% DOD Energy (kWh)"] (single product capacity)
        Let C_r = yearly_result.containers_in_service[r]
        kWh DC Usable[r] = product_energy * C_r * DOD * discharge_eff * SOH_r

    Notes:
    - Use single product capacity, not system nameplate (which already includes containers)
    - DOD from interface / degradation percent string.
    - discharge_eff rule unchanged (0.95 @0.5C else 0.965).
    - SOH_r fraction list reused.
    - Round to 2 decimals.
    """
    state = load_state(state_path)

    # Load single product capacity from specs
    product, model = resolve_product_and_model(state)
    specs = load_system_specs(product, model, xlsx_path)
    energy_kwh = _to_float(specs.get("100% DOD Energy (kWh)")) or 0.0

    # Ensure supporting lists exist
    calc = state.get("calculator", {}) if isinstance(state.get("calculator"), dict) else {}
    yr = calc.get("yearly_result", {}) if isinstance(calc, dict) else {}

    # Containers list
    containers = yr.get("containers_in_service") if isinstance(yr, dict) else None
    if not (isinstance(containers, list) and len(containers) >= 21):
        containers = compute_and_persist_containers_in_service(state_path)
        state = load_state(state_path)
        calc = state.get("calculator", {}) if isinstance(state.get("calculator"), dict) else {}
        yr = calc.get("yearly_result", {}) if isinstance(calc, dict) else {}
        containers = yr.get("containers_in_service") or [0.0] * 21

    # SOH list
    soh_list = yr.get("soh_percent") if isinstance(yr, dict) else None
    if not (isinstance(soh_list, list) and len(soh_list) >= 21):
        soh_list = compute_and_persist_soh_percent(state_path)
        state = load_state(state_path)
        calc = state.get("calculator", {}) if isinstance(state.get("calculator"), dict) else {}
        yr = calc.get("yearly_result", {}) if isinstance(calc, dict) else {}
        soh_list = yr.get("soh_percent") or [0.0] * 21

    # DOD fraction helper
    def _parse_percent_to_frac(s: Optional[str]) -> Optional[float]:
        if not s:
            return None
        ss = str(s).strip().replace('%', '')
        try:
            return float(ss) / 100.0
        except Exception:
            return None

    iface = state.get("interface", {}) if isinstance(state.get("interface"), dict) else {}
    degr = state.get("degradation", {}) if isinstance(state.get("degradation"), dict) else {}
    dod_frac = _parse_percent_to_frac(iface.get("dod")) or _parse_percent_to_frac(degr.get("dod")) or 1.0

    # C-rate -> discharge_eff
    discharge_text = (iface.get("discharge") or '').strip()
    c_rate: Optional[float] = None
    if discharge_text:
        try:
            c_rate = float(discharge_text.upper().replace('C', ''))
        except Exception:
            c_rate = None
    if c_rate is None:
        c_rate = _to_float(degr.get("cp"))
    discharge_eff = 0.95 if (c_rate is not None and abs(c_rate - 0.5) < 1e-6) else 0.965

    values: list = []
    for i in range(21):
        try:
            cval = float(containers[i] if i < len(containers) else containers[-1])
        except Exception:
            cval = 0.0
        try:
            soh = float(soh_list[i] if i < len(soh_list) else soh_list[-1])
        except Exception:
            soh = 0.0
        val = energy_kwh * cval * dod_frac * discharge_eff * soh
        values.append(round(val, 2))

    # Persist
    state = load_state(state_path)
    state.setdefault("calculator", {})
    yr2 = state["calculator"].get("yearly_result") if isinstance(state["calculator"], dict) else None
    if not isinstance(yr2, dict):
        yr2 = {}
        state["calculator"]["yearly_result"] = yr2
    yr2["kwh_dc_usable"] = values

    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return values

def compute_and_persist_kwh_ac_usable(state_path: str = STATE_JSON, xlsx_path: str = SYSTEM_SPECS_XLSX) -> list:
    """Compute yearly kWh AC Usable (years 0..20) based on product capacity and containers.

    Correct Rule:
        Let product_energy = specs["100% DOD Energy (kWh)"] (single product capacity)
        Let C_r = yearly_result.containers_in_service[r]
        kWh AC Usable[r] = product_energy * C_r * DOD * discharge_eff * 0.9732 * SOH_r

    Notes:
    - Use single product capacity, not system values (which already include containers)
    - AC conversion factor 0.9732 applied after DC calculation
    """
    state = load_state(state_path)

    # Load single product capacity from specs
    product, model = resolve_product_and_model(state)
    specs = load_system_specs(product, model, xlsx_path)
    energy_kwh = _to_float(specs.get("100% DOD Energy (kWh)")) or 0.0

    # Ensure dependent lists exist
    calc = state.get("calculator", {}) if isinstance(state.get("calculator"), dict) else {}
    yr = calc.get("yearly_result", {}) if isinstance(calc, dict) else {}

    containers = yr.get("containers_in_service") if isinstance(yr, dict) else None
    if not (isinstance(containers, list) and len(containers) >= 21):
        containers = compute_and_persist_containers_in_service(state_path)
        state = load_state(state_path)
        calc = state.get("calculator", {}) if isinstance(state.get("calculator"), dict) else {}
        yr = calc.get("yearly_result", {}) if isinstance(calc, dict) else {}
        containers = yr.get("containers_in_service") or [0.0] * 21

    soh_list = yr.get("soh_percent") if isinstance(yr, dict) else None
    if not (isinstance(soh_list, list) and len(soh_list) >= 21):
        soh_list = compute_and_persist_soh_percent(state_path)
        state = load_state(state_path)
        calc = state.get("calculator", {}) if isinstance(state.get("calculator"), dict) else {}
        yr = calc.get("yearly_result", {}) if isinstance(calc, dict) else {}
        soh_list = yr.get("soh_percent") or [0.0] * 21

    def _parse_percent_to_frac(s: Optional[str]) -> Optional[float]:
        if not s:
            return None
        ss = str(s).strip().replace('%', '')
        try:
            return float(ss) / 100.0
        except Exception:
            return None

    iface = state.get("interface", {}) if isinstance(state.get("interface"), dict) else {}
    degr = state.get("degradation", {}) if isinstance(state.get("degradation"), dict) else {}
    dod_frac = _parse_percent_to_frac(iface.get("dod")) or _parse_percent_to_frac(degr.get("dod")) or 1.0

    discharge_text = (iface.get("discharge") or '').strip()
    c_rate: Optional[float] = None
    if discharge_text:
        try:
            c_rate = float(discharge_text.upper().replace('C', ''))
        except Exception:
            c_rate = None
    if c_rate is None:
        c_rate = _to_float(degr.get("cp"))
    discharge_eff = 0.95 if (c_rate is not None and abs(c_rate - 0.5) < 1e-6) else 0.965

    values: list = []
    for i in range(21):
        try:
            cval = float(containers[i] if i < len(containers) else containers[-1])
        except Exception:
            cval = 0.0
        try:
            soh = float(soh_list[i] if i < len(soh_list) else soh_list[-1])
        except Exception:
            soh = 0.0
        val = energy_kwh * cval * dod_frac * discharge_eff * 0.9732 * soh
        values.append(round(val, 2))

    state = load_state(state_path)
    state.setdefault("calculator", {})
    yr2 = state["calculator"].get("yearly_result") if isinstance(state["calculator"], dict) else None
    if not isinstance(yr2, dict):
        yr2 = {}
        state["calculator"]["yearly_result"] = yr2
    yr2["kwh_ac_usable"] = values
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return values

def compute_and_persist_delta(state_path: str = STATE_JSON) -> list:
    """Compute yearly delta (kWh) based on edge_solution.

    If edge_solution == 'DC' (case-insensitive):
        delta[r] = kwh_dc_usable[r] - min_required
    Else if edge_solution == 'AC':
        delta[r] = kwh_ac_usable[r] - min_required
    min_required pulled from capacity_kwh (top-level or interface/site/calculator sections).
    Round each to 2 decimals. Persist to calculator.yearly_result.delta_kwh.
    """
    state = load_state(state_path)

    # Resolve edge_solution (fallback 'DC')
    edge_solution = None
    for key in ("edge_solution",):
        if key in state:
            edge_solution = state.get(key)
            break
    if edge_solution is None and isinstance(state.get("interface"), dict):
        edge_solution = state["interface"].get("edge_solution")
    mode = (str(edge_solution).strip().upper() if edge_solution not in (None, "") else "DC")
    if mode not in ("DC", "AC"):
        mode = "DC"

    # Pull min required capacity_kwh
    min_required = None
    if "capacity_kwh" in state:
        min_required = state.get("capacity_kwh")
    else:
        for sec in ("interface", "site", "calculator"):
            sect = state.get(sec)
            if isinstance(sect, dict) and "capacity_kwh" in sect:
                min_required = sect.get("capacity_kwh")
                break
    try:
        min_required_val = float(str(min_required).replace(",", "").strip()) if min_required not in (None, "") else None
    except Exception:
        min_required_val = None

    # Ensure usable lists exist
    calc = state.get("calculator", {}) if isinstance(state.get("calculator"), dict) else {}
    yr = calc.get("yearly_result", {}) if isinstance(calc, dict) else {}
    dc_list = yr.get("kwh_dc_usable") if isinstance(yr, dict) else None
    ac_list = yr.get("kwh_ac_usable") if isinstance(yr, dict) else None

    # Compute if missing
    if not (isinstance(dc_list, list) and len(dc_list) >= 21):
        try:
            dc_list = compute_and_persist_kwh_dc_usable(state_path)
        except Exception:
            dc_list = [0.0] * 21
    if not (isinstance(ac_list, list) and len(ac_list) >= 21):
        try:
            ac_list = compute_and_persist_kwh_ac_usable(state_path)
        except Exception:
            ac_list = [0.0] * 21

    # Choose source list
    src = dc_list if mode == "DC" else ac_list
    delta: list = []
    for i in range(21):
        base = 0.0
        try:
            base = float(src[i] if i < len(src) else src[-1])
        except Exception:
            base = 0.0
        if min_required_val is None:
            delta.append(None)
        else:
            delta.append(round(base - min_required_val, 2))

    # Persist
    state = load_state(state_path)
    state.setdefault("calculator", {})
    yr2 = state["calculator"].get("yearly_result") if isinstance(state["calculator"], dict) else None
    if not isinstance(yr2, dict):
        yr2 = {}
        state["calculator"]["yearly_result"] = yr2
    yr2["delta_kwh"] = delta
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return delta

if __name__ == "__main__":
    try:
        outputs = compute_and_persist_system_outputs()
        print("[System Output] Product nameplate:", outputs["product_nameplate_capacity"]) 
        print("[System Output] System nameplate:", outputs["system_nameplate_capacity"]) 
    except Exception as e:
        print("[Algorithm] Error:", e)
