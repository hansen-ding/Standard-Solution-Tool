"""
Streamlit 销售工具 - 项目信息输入页面
"""
import streamlit as st
from algorithm import (
    to_kw, to_kwh, calculate_c_rate, format_c_rate, fetch_temperature, get_pcs_options,
    compute_proposed_bess_count, compute_confluence_cabinet_count, compute_pcs_count,
    get_bess_specs_for, compute_system_dc_usable_capacity, compute_system_ac_usable_capacity,
    compute_system_rated_dc_power, compute_system_rated_ac_power
)
from datetime import datetime
import io
from PIL import Image
import base64
import matplotlib.pyplot as plt

# 主题颜色
THEME_RGB = (234, 85, 32)
THEME_COLOR = f"rgb({THEME_RGB[0]}, {THEME_RGB[1]}, {THEME_RGB[2]})"

# 页面配置
st.set_page_config(
    page_title="BESS Sizing Tool",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS样式
st.markdown(f"""
<style>
    /* 响应式容器 */
    .main .block-container {{
        max-width: 1400px;
        padding-left: 2rem;
        padding-right: 2rem;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }}
    
    /* 主题色按钮 */
    .stButton>button {{
        background-color: {THEME_COLOR};
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 8px 18px;
        white-space: nowrap;
    }}
    .stButton>button:hover {{
        background-color: rgba({THEME_RGB[0]}, {THEME_RGB[1]}, {THEME_RGB[2]}, 0.85);
    }}
    
    /* 底部 Next 按钮自适应宽度 */
    div[data-testid="column"]:has(button[key="next_btn"]) .stButton>button {{
        width: auto;
        min-width: 100px;
        font-size: 14px;
    }}
    
    /* Export Configuration 按钮自适应宽度 */
    div[data-testid="column"]:has(button[key="export_config_btn"]) .stButton>button {{
        width: auto;
        min-width: 150px;
        font-size: 14px;
        padding: 8px 18px;
    }}
    
    /* 使用 Streamlit 容器作为分组框 */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {{
        border: 2px solid rgba({THEME_RGB[0]}, {THEME_RGB[1]}, {THEME_RGB[2]}, 0.7);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }}
    
    /* 标题样式 */
    .main-title {{
        color: {THEME_COLOR};
        text-align: center;
        font-size: clamp(20px, 4vw, 28px);
        font-weight: 700;
        margin-bottom: 5px;
    }}
    .subtitle {{
        color: #5f5f5f;
        text-align: center;
        font-size: clamp(12px, 2vw, 16px);
        margin-bottom: 20px;
    }}
    
    /* 分组标题 */
    .group-title {{
        color: {THEME_COLOR};
        font-weight: 600;
        font-size: 18px;
        margin-bottom: 15px;
        padding-bottom: 8px;
        border-bottom: 2px solid rgba({THEME_RGB[0]}, {THEME_RGB[1]}, {THEME_RGB[2]}, 0.3);
    }}
    
    /* 响应式输入框 */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div {{
        font-size: clamp(12px, 1.5vw, 14px);
    }}
    
    /* 隐藏数字输入框的加减按钮 */
    .stNumberInput button {{
        display: none;
    }}
    
    /* 隐藏 "Press Enter to apply" 提示 */
    .stNumberInput > div > div > input::placeholder {{
        color: transparent;
    }}
    /* 显示 delivery 和 cod 输入框的 placeholder */
    .stTextInput > div > div > input::placeholder {{
        color: #999;
        opacity: 0.7;
    }}
    .stTextInput [data-testid="InputInstructions"],
    .stNumberInput [data-testid="InputInstructions"] {{
        display: none;
    }}
    
    /* Fetch Temp 按钮样式 */
    .stButton>button {{
        font-size: clamp(6px, 0.75vw, 11px);
        padding: 6px 3px;
    }}
    
    /* 底部 Next 按钮保持原样 */
    div[data-testid="column"]:has(button[key="next_btn"]) .stButton>button {{
        width: auto;
        min-width: 100px;
        font-size: 14px;
        padding: 8px 18px;
    }}
    
    /* 小屏幕适配 */
    @media (max-width: 768px) {{
        .main .block-container {{
            padding-left: 1rem;
            padding-right: 1rem;
        }}
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {{
            padding: 10px;
        }}
        .stButton>button {{
            width: 100%;
            font-size: 10px !important;
            padding: 4px 4px !important;
        }}
    }}
    
    /* 超大屏幕适配 */
    @media (min-width: 1920px) {{
        .main .block-container {{
            max-width: 1600px;
        }}
    }}
    
    /* PCS 图片固定高度 */
    .stImage img {{
        height: 300px;
        object-fit: contain;
    }}
    
    /* Results 表格样式 - 更小的字体和紧凑布局 */
    .stDataFrame {{
        font-size: 10px;
    }}
    .stDataFrame table {{
        font-size: 10px;
    }}
    .stDataFrame th {{
        font-size: 10px;
        padding: 2px 4px !important;
        white-space: nowrap;
        text-align: center !important;
    }}
    .stDataFrame td {{
        font-size: 10px;
        padding: 2px 4px !important;
        text-align: center !important;
    }}
    .stDataFrame [data-testid="stDataFrame"] {{
        height: auto !important;
    }}
    /* 强制表格单元格内容居中 - 更强的选择器 */
    [data-testid="stDataFrame"] table tbody tr td {{
        text-align: center !important;
    }}
    [data-testid="stDataFrame"] table thead tr th {{
        text-align: center !important;
    }}
    [data-testid="stDataFrame"] table tbody tr td div {{
        text-align: center !important;
        justify-content: center !important;
    }}
    [data-testid="stDataFrame"] table thead tr th div {{
        text-align: center !important;
        justify-content: center !important;
    }}
    
    /* Augmentation Plan 输入框紧凑样式 */
    [data-testid="column"] .stNumberInput {{
        margin-bottom: 0 !important;
    }}
    [data-testid="column"] .stNumberInput > div {{
        padding: 0 !important;
    }}
    [data-testid="column"] .stNumberInput input {{
        min-height: 32px !important;
        height: 32px !important;
        padding: 4px 8px !important;
        font-size: 13px !important;
        text-align: center !important;
    }}
    
    /* Augmentation Plan text input 样式 (用于允许空值) */
    [data-testid="column"] .stTextInput {{
        margin-bottom: 0 !important;
    }}
    [data-testid="column"] .stTextInput > div {{
        padding: 0 !important;
    }}
    [data-testid="column"] .stTextInput input {{
        min-height: 32px !important;
        height: 32px !important;
        padding: 4px 8px !important;
        font-size: 13px !important;
        text-align: center !important;
    }}
</style>
""", unsafe_allow_html=True)

# 初始化 session state
if 'data' not in st.session_state:
    st.session_state.data = {
        'customer': '',
        'project': '',
        'usecase': '',
        'life_stage': '',
        'location': '',
        'tmax_c': None,
        'tmin_c': None,
        'power': None,
        'power_unit': 'kW',
        'capacity': None,
        'capacity_unit': 'kWh',
        'cycle': '',
        'product': '',
        'edge_model': '',
        'edge_solution': '',
        'delivery': '',
        'cod': '',
        'augmentation': '',
        'selected_pcs': None,
        'pcs_options': None,
    }

if 'show_pcs_section' not in st.session_state:
    st.session_state.show_pcs_section = False

if 'show_results_section' not in st.session_state:
    st.session_state.show_results_section = False

# 标题
st.markdown('<div class="main-title">Project Overview</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Basic Information Input</div>', unsafe_allow_html=True)

# 创建居中的容器，左右留白
spacer_left, center_content, spacer_right = st.columns([0.5, 9, 0.5])

with center_content:
    # 创建两列布局
    col_left, col_right = st.columns(2)

with col_left:
    # ===== Basic Info =====
    with st.container():
        st.markdown('<div class="group-title">Basic Info</div>', unsafe_allow_html=True)
        
        customer = st.text_input("Customer Name:", value=st.session_state.data['customer'], key='customer')
        if customer != st.session_state.data.get('customer'):
            st.session_state.data['customer'] = customer
        
        project = st.text_input("Project Name:", value=st.session_state.data['project'], key='project')
        if project != st.session_state.data.get('project'):
            st.session_state.data['project'] = project
        
        # Use Case dropdown list
        usecase_options = [
            "",
            "Peak Shaving",
            "Load Shifting",
            "Energy Arbitrage",
            "TOU Optimization",
            "Frequency Regulation",
            "Spinning Reserve",
            "Backup Power / UPS",
            "Black Start",
            "Renewable Integration",
            "PV Smoothing",
            "Renewable Firming",
            "EV Charging Support",
            "Microgrid / Island Operation",
            "Demand Response",
            "Power Quality Improvement",
            "Voltage Control / Reactive Power Support",
            "Congestion Management",
            "T&D Upgrade Deferral",
            "Long-duration Energy Storage",
            "Virtual Power Plant (VPP)",
            "Other"
        ]
        
        # 判断当前值是否在选项中，如果不在且不为空，说明是自定义值
        current_usecase = st.session_state.data.get('usecase', '')
        if current_usecase and current_usecase not in usecase_options:
            # 保存自定义值到 session state
            if 'usecase_custom' not in st.session_state.data:
                st.session_state.data['usecase_custom'] = current_usecase
            usecase_select = "Other"
        else:
            usecase_select = current_usecase
        
        usecase = st.selectbox(
            "Use Case:",
            usecase_options,
            index=usecase_options.index(usecase_select) if usecase_select in usecase_options else 0,
            key='usecase_select'
        )
        
        # 如果选择了 "Other"，显示文本输入框
        if usecase == "Other":
            usecase_custom = st.text_input(
                "Please specify:",
                value=st.session_state.data.get('usecase_custom', ''),
                key='usecase_custom_input'
            )
            # 使用自定义值作为最终的 usecase
            final_usecase = usecase_custom if usecase_custom else "Other"
            # Auto-save custom usecase
            if usecase_custom != st.session_state.data.get('usecase_custom'):
                st.session_state.data['usecase_custom'] = usecase_custom
                st.session_state.data['usecase'] = final_usecase
        else:
            final_usecase = usecase
            # 清除自定义值
            if 'usecase_custom' in st.session_state.data:
                st.session_state.data['usecase_custom'] = ''
            # Auto-save standard usecase
            if final_usecase != st.session_state.data.get('usecase'):
                st.session_state.data['usecase'] = final_usecase
        
        # Life Stage dropdown
        life_stage_options = ["", "BOL", "EOL"]
        life_stage = st.selectbox(
            "Life Stage:",
            life_stage_options,
            index=life_stage_options.index(st.session_state.data['life_stage']) if st.session_state.data['life_stage'] in life_stage_options else 0,
            key='life_stage'
        )
        # Auto-save to session state when changed
        if life_stage != st.session_state.data.get('life_stage'):
            st.session_state.data['life_stage'] = life_stage
        
        # Location with fetch button
        location_col1, location_col2 = st.columns([0.82, 0.18])
        with location_col1:
            location = st.text_input("Location (City or Zipcode):", value=st.session_state.data['location'], key='location')
        with location_col2:
            st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
            fetch_clicked = st.button("Fetch Temp", width="stretch")
        
        # 检测回车键：当 location 改变且不为空时也触发 fetch
        location_changed = location != st.session_state.data['location']
        
        if fetch_clicked or (location_changed and location):
            if location:
                with st.spinner("Fetching temperature data..."):
                    max_temp, min_temp, tooltip = fetch_temperature(location)
                    if max_temp is not None:
                        st.session_state.data['tmax_c'] = max_temp
                        st.session_state.data['tmin_c'] = min_temp
                        st.session_state.data['location'] = location
                        st.rerun()
                    else:
                        st.error(tooltip)
            else:
                st.warning("Please enter a location first")
        
        # Temperature fields (read-only display)
        max_temp_display = st.session_state.data['tmax_c'] if st.session_state.data['tmax_c'] is not None else ""
        min_temp_display = st.session_state.data['tmin_c'] if st.session_state.data['tmin_c'] is not None else ""
        
        # 使用 markdown 显示温度 (模拟 disabled text_input 样式)
        st.markdown('<p style="margin-bottom: 0.25rem; font-size: 14px; font-weight: 400;">Max Temp (°C):</p>', unsafe_allow_html=True)
        st.markdown(f'<div style="background-color: #f0f2f6; padding: 0.5rem 0.75rem; border-radius: 0.5rem; margin-bottom: 1rem; font-size: 14px; color: #31333F;">{max_temp_display if max_temp_display else "&nbsp;"}</div>', unsafe_allow_html=True)
        
        st.markdown('<p style="margin-bottom: 0.25rem; font-size: 14px; font-weight: 400;">Min Temp (°C):</p>', unsafe_allow_html=True)
        st.markdown(f'<div style="background-color: #f0f2f6; padding: 0.5rem 0.75rem; border-radius: 0.5rem; margin-bottom: 1rem; font-size: 14px; color: #31333F;">{min_temp_display if min_temp_display else "&nbsp;"}</div>', unsafe_allow_html=True)
    
    # ===== Product ===== (移除第一页的产品选择控件，改为从 session_state 读取)
    # 之前此处包含 Product / EDGE Model / Solution Type 的选择框。
    # 现在不显示，只保留变量以便 Next 时写回。
    product = st.session_state.data.get('product', '')
    edge_model = st.session_state.data.get('edge_model', '')
    edge_solution = st.session_state.data.get('edge_solution', '')

with col_right:
    # ===== System Design =====
    with st.container():
        st.markdown('<div class="group-title">System Design</div>', unsafe_allow_html=True)
        
        # Power with unit
        power_col1, power_col2 = st.columns([3, 1])
        with power_col1:
            power = st.number_input(
                "Power:",
                min_value=0.0,
                value=float(st.session_state.data['power']) if st.session_state.data['power'] else None,
                step=1.0,
                format="%.2f",
                key='power_input'
            )
        with power_col2:
            st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
            power_unit = st.selectbox("Unit", ["kW", "MW"], key='power_unit_select', label_visibility="collapsed")
        
        # Auto-save power and unit
        if power != st.session_state.data.get('power') or power_unit != st.session_state.data.get('power_unit'):
            st.session_state.data['power'] = power if power and power > 0 else None
            st.session_state.data['power_unit'] = power_unit
        
        # Capacity with unit
        capacity_col1, capacity_col2 = st.columns([3, 1])
        with capacity_col1:
            capacity = st.number_input(
                "Capacity:",
                min_value=0.0,
                value=float(st.session_state.data['capacity']) if st.session_state.data['capacity'] else None,
                step=1.0,
                format="%.2f",
                key='capacity_input'
            )
        with capacity_col2:
            st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
            capacity_unit = st.selectbox("Unit", ["kWh", "MWh"], key='capacity_unit_select', label_visibility="collapsed")
        
        # Auto-save capacity and unit
        if capacity != st.session_state.data.get('capacity') or capacity_unit != st.session_state.data.get('capacity_unit'):
            st.session_state.data['capacity'] = capacity if capacity and capacity > 0 else None
            st.session_state.data['capacity_unit'] = capacity_unit
        
        # Calculate and display C-rate
        power_kw = to_kw(power if power and power > 0 else None, power_unit)
        capacity_kwh = to_kwh(capacity if capacity and capacity > 0 else None, capacity_unit)
        c_rate = calculate_c_rate(power_kw, capacity_kwh)
        c_rate_display = format_c_rate(c_rate) if c_rate else ""
        
        # Auto-save calculated values
        st.session_state.data['power_kw'] = power_kw
        st.session_state.data['capacity_kwh'] = capacity_kwh
        st.session_state.data['discharge'] = c_rate_display
        
        # 使用 markdown 显示 C-rate (模拟 text_input 样式)
        st.markdown('<p style="margin-bottom: 0.25rem; font-size: 14px; font-weight: 400;">Discharge Rate:</p>', unsafe_allow_html=True)
        st.markdown(f'<div style="background-color: #f0f2f6; padding: 0.5rem 0.75rem; border-radius: 0.5rem; margin-bottom: 1rem; font-size: 16px; color: #31333F;">{c_rate_display if c_rate_display else "&nbsp;"}</div>', unsafe_allow_html=True)
        
        cycle_num = st.number_input(
            "Cycles per Year:",
            min_value=0,
            max_value=10000,
            value=int(st.session_state.data['cycle']) if st.session_state.data['cycle'] not in (None, '', 0) else None,
            step=1,
            format="%d",
            key='cycle'
        )
        
        # Auto-save cycle
        if cycle_num != st.session_state.data.get('cycle'):
            st.session_state.data['cycle'] = cycle_num
    
    # ===== Lifecycle =====
    with st.container():
        st.markdown('<div class="group-title">Lifecycle</div>', unsafe_allow_html=True)
        
        delivery = st.text_input(
            "Delivery Date:", 
            value=st.session_state.data['delivery'], 
            key='delivery',
            placeholder="e.g. Q1 2049 / Jan 2049"
        )
        if delivery != st.session_state.data.get('delivery'):
            st.session_state.data['delivery'] = delivery
            
        cod = st.text_input(
            "COD:", 
            value=st.session_state.data['cod'], 
            key='cod',
            placeholder="e.g. Q4 2077 / Dec 2077"
        )
        if cod != st.session_state.data.get('cod'):
            st.session_state.data['cod'] = cod
        augmentation = st.selectbox(
            "Augmentation & Overbuild:",
            ["", "N/A", "Augmentation", "Overbuild"],
            index=["", "N/A", "Augmentation", "Overbuild"].index(st.session_state.data['augmentation']) if st.session_state.data['augmentation'] in ["", "N/A", "Augmentation", "Overbuild"] else 0,
            key='augmentation'
        )
        # Auto-save to session state when changed
        if augmentation != st.session_state.data.get('augmentation'):
            st.session_state.data['augmentation'] = augmentation

# ==========================================
# 👇 Next 按钮：移到页面最底部右下角
# ==========================================

# 只在未显示 PCS 部分时显示 Next 按钮
if not st.session_state.show_pcs_section:
    # 添加一点垂直间距，确保不拥挤
    st.markdown("<br>", unsafe_allow_html=True)

    # 创建一个新的底部容器 - 也使用 0.5:9:0.5 布局保持一致
    next_spacer_left, next_center, next_spacer_right = st.columns([0.5, 9, 0.5])
    
    with next_center:
        # [10, 1.2] 的比例会让左边留白，把按钮挤到最右边的角落
        col_footer_left, col_footer_right = st.columns([10, 1.2])

        with col_footer_right:
            # use_container_width=True 让按钮填满这个小列，视觉上更整齐
            if st.button("Next ➔", key='next_btn', use_container_width=True):
                # 所有数据已经实时自动保存，只需触发页面切换
                st.session_state.show_pcs_section = True
                st.rerun()

# ==========================================
# PCS Selection 部分
# ==========================================

if st.session_state.show_pcs_section:
    # 增加与第一页的垂直间距
    st.markdown("<div style='height: 48px;'></div>", unsafe_allow_html=True)
    # 顶部主题与副标题
    st.markdown('<div class="main-title">System Configuration</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Product Selection · PCS Selection · System Configuration</div>', unsafe_allow_html=True)
    st.markdown('<div id="pcs-selection"></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # 在 PCS 页提供简洁的产品信息编辑控件
    edit_col1, edit_col2, edit_col3 = st.columns([3, 3, 3])
    with edit_col1:
        product_inline = st.selectbox(
            "Product",
            ["", "EDGE", "GRID5015"],
            index=["", "EDGE", "GRID5015"].index(st.session_state.data.get('product', '')) if st.session_state.data.get('product', '') in ["", "EDGE", "GRID5015"] else 0,
            key='product_inline'
        )
        # Auto-save when changed
        if product_inline != st.session_state.data.get('product'):
            st.session_state.data['product'] = product_inline
    with edit_col2:
        if product_inline == "EDGE":
            model_inline = st.selectbox(
                "Model",
                ["", "760kWh", "676kWh", "591kWh", "507kWh", "422kWh", "338kWh"],
                index=["", "760kWh", "676kWh", "591kWh", "507kWh", "422kWh", "338kWh"].index(st.session_state.data.get('edge_model','')) if st.session_state.data.get('edge_model','') in ["", "760kWh", "676kWh", "591kWh", "507kWh", "422kWh", "338kWh"] else 0,
                key='model_inline'
            )
            # Auto-save when changed
            if model_inline != st.session_state.data.get('edge_model'):
                st.session_state.data['edge_model'] = model_inline
        else:
            model_inline = ""
    with edit_col3:
        solution_inline = st.selectbox(
            "Solution",
            ["", "DC", "AC"],
            index=["", "DC", "AC"].index(st.session_state.data.get('edge_solution','')) if st.session_state.data.get('edge_solution','') in ["", "DC", "AC"] else 0,
            key='solution_inline'
        )
        # Auto-save when changed
        if solution_inline != st.session_state.data.get('edge_solution'):
            st.session_state.data['edge_solution'] = solution_inline

    # 准备选项数据（按当前输入自动生成，无需手动加载）
    current_product = st.session_state.data.get('product')
    current_model = st.session_state.data.get('edge_model')
    current_solution = st.session_state.data.get('edge_solution')
    # 使用最新保存的功率/容量
    current_power_kw = st.session_state.data.get('power_kw')
    current_capacity_kwh = st.session_state.data.get('capacity_kwh')
    current_c_rate = calculate_c_rate(current_power_kw, current_capacity_kwh)
    
    # Compute proposed BESS count
    current_augmentation = st.session_state.data.get('augmentation', '')
    current_life_stage = st.session_state.data.get('life_stage', 'BOL')
    current_cycles = st.session_state.data.get('cycle', 365)
    proposed_bess = 0
    if current_product and current_capacity_kwh:
        try:
            proposed_bess = compute_proposed_bess_count(
                capacity_required_kwh=current_capacity_kwh,
                product=current_product,
                model=current_model,
                augmentation_mode=current_augmentation,
                solution_type=current_solution,
                life_stage=current_life_stage,
                cycles_per_year=int(current_cycles) if current_cycles else 365,
                discharge_rate=current_c_rate if current_c_rate else 0.5,
            )
        except Exception:
            proposed_bess = 0

    # Compute System Nameplate Capacity (sync unit with first page input)
    system_nameplate_value = None
    system_nameplate_unit = st.session_state.data.get('capacity_unit', 'kWh')
    system_dc_usable_value = None
    system_dc_usable_unit = system_nameplate_unit
    system_ac_usable_value = None
    system_ac_usable_unit = system_nameplate_unit
    system_rated_dc_power_value = None
    system_rated_dc_power_unit = st.session_state.data.get('power_unit', 'kW')
    try:
        specs = get_bess_specs_for(current_product, current_model)
        energy_kwh = specs.get('100% DOD Energy (kWh)')
        energy_kwh = float(str(energy_kwh).replace(',', '').strip()) if energy_kwh not in (None, '') else None
        if energy_kwh is not None:
            total_kwh = (proposed_bess or 0) * energy_kwh
            if system_nameplate_unit == 'MWh':
                system_nameplate_value = round(total_kwh / 1000.0, 3)
            else:
                system_nameplate_value = round(total_kwh, 3)
            # Compute DC Usable Capacity
            system_dc_usable_value, system_dc_usable_unit = compute_system_dc_usable_capacity(
                proposed_bess, energy_kwh, current_product, system_nameplate_unit
            )
            # Compute AC Usable Capacity from DC Usable
            if system_dc_usable_value is not None:
                # Convert DC usable back to kWh for calculation
                dc_kwh = system_dc_usable_value * 1000 if system_dc_usable_unit == 'MWh' else system_dc_usable_value
                system_ac_usable_value, system_ac_usable_unit = compute_system_ac_usable_capacity(
                    dc_kwh, system_nameplate_unit
                )
                # Compute System Rated DC Power
                if current_c_rate is not None:
                    system_rated_dc_power_value, system_rated_dc_power_unit = compute_system_rated_dc_power(
                        dc_kwh, current_c_rate, system_rated_dc_power_unit
                    )
    except Exception:
        system_nameplate_value = None
        system_dc_usable_value = None
        system_ac_usable_value = None
        system_rated_dc_power_value = None

    def infer_tag_from_image(img_path: str) -> str:
        try:
            name = (img_path or '').lower()
            if '760+dc+epc' in name:
                return '760+dc+epc'
            if '760+dc' in name and 'epc' not in name:
                return '760+dc'
            if '760+ac' in name:
                return '760+ac'
            if '760+dynapower' in name:
                return '760+dynapower'
            if '760.png' in name or name.endswith('/760.png'):
                return '760'
            # GRID5015 tags
            if '5015+5160' in name:
                return '5015+5160'
            if '5015+cab1000' in name or 'cab1000' in name:
                return '5015+cab1000'
            if '5015+4800' in name or '4800' in name:
                return '5015+4800'
        except Exception:
            pass
        return ''
    
    def compute_metrics_for_config(option_tag: str) -> dict:
        """Compute all metrics for a specific configuration."""
        metrics = {
            'pcs_count': None,
            'pcs_count_str': None,
            'rated_ac_power_value': None,
            'rated_ac_power_unit': system_rated_dc_power_unit,
        }
        
        # PCS count (skip 760 and 760+DC)
        if option_tag not in ('760', '760+dc'):
            pcs_str = compute_pcs_count(
                product=current_product,
                option_tag=option_tag,
                proposed_bess=proposed_bess,
                power_kw=current_power_kw,
                discharge_rate=(st.session_state.data.get('discharge') or current_c_rate),
            )
            metrics['pcs_count_str'] = pcs_str
            try:
                metrics['pcs_count'] = int(pcs_str) if pcs_str not in ('-', '') else None
            except Exception:
                metrics['pcs_count'] = None
        
        # System Rated AC Power
        if system_ac_usable_value is not None:
            ac_kwh = system_ac_usable_value * 1000 if system_ac_usable_unit == 'MWh' else system_ac_usable_value
            rated_ac_val, rated_ac_unit = compute_system_rated_ac_power(
                ac_kwh, current_c_rate, metrics['pcs_count'], option_tag, system_rated_dc_power_unit
            )
            metrics['rated_ac_power_value'] = rated_ac_val
            metrics['rated_ac_power_unit'] = rated_ac_unit
        
        return metrics

    # 特定组合不推荐：EDGE 422/338kWh 仅在 AC；GRID5015 的 DC；Discharge Rate > 0.5C
    no_recommend = (
        (current_product == 'EDGE' and current_solution == 'AC' and current_model in ['422kWh', '338kWh']) or
        (current_product == 'GRID5015' and current_solution == 'DC') or
        (current_c_rate is not None and current_c_rate > 0.5)
    )
    
    # 确定不推荐的原因
    no_recommend_reason = ""
    if no_recommend:
        if current_c_rate is not None and current_c_rate > 0.5:
            no_recommend_reason = f"(Discharge rate cannot exceed 0.5C)"
        elif current_product == 'GRID5015' and current_solution == 'DC':
            no_recommend_reason = "(DC solution not available for GRID5015)"
        elif current_product == 'EDGE' and current_solution == 'AC' and current_model in ['422kWh', '338kWh']:
            no_recommend_reason = "(AC solution not available for this EDGE model)"

    if not current_product and not current_solution:
        pcs_options = []
    elif no_recommend:
        pcs_options = []
    else:
        pcs_options = get_pcs_options(
            product=current_product,
            model=current_model,
            solution_type=current_solution,
            discharge_rate=current_c_rate,
        ) or []
    st.session_state.data['pcs_options'] = pcs_options

    # 安全渲染图片函数：当文件不存在或路径为空时不渲染
    import os
    def render_image_safe(path: str):
        if not path:
            return
        try:
            if path.startswith('http://') or path.startswith('https://'):
                st.image(path, use_container_width=True)
            else:
                if os.path.isfile(path):
                    st.image(path, use_container_width=True)
        except Exception:
            pass

    # 已选择时仅显示选中配置；空白或无数据时保持空白或提示
    if no_recommend:
        if no_recommend_reason:
            st.warning(f"⚠️ No recommended solution {no_recommend_reason}")
        else:
            st.info("No recommended solution")
    elif st.session_state.data.get('selected_pcs') and pcs_options:
        pcs_spacer_left, pcs_center, pcs_spacer_right = st.columns([2, 6, 2])
        with pcs_center:
            with st.container():
                selected_label = st.session_state.data['selected_pcs']
                idx = 0 if selected_label == 'Configuration A' else 1
                opt = pcs_options[idx] if len(pcs_options) > idx else None
                if opt:
                    render_image_safe(opt.get("image"))
                    st.markdown(f'<div class="group-title">{selected_label} (Selected)</div>', unsafe_allow_html=True)
                    # Show components and new fields from option data
                    st.markdown(f"**System Components:** {opt.get('components','')}")
                    st.markdown(f"**Architecture:** {opt.get('architecture','')}")
                    st.markdown(f"**Origin:** {opt.get('origin','')}")
                    st.markdown(f"**Proposed Number of BESS:** {proposed_bess}")
                    tag_sel = infer_tag_from_image(opt.get('image',''))
                    conf_sel = compute_confluence_cabinet_count(current_product, current_model, tag_sel, proposed_bess)
                    if conf_sel is not None:
                        st.markdown(f"**Proposed Number of Confluence Cabinet:** {conf_sel}")
                    # Compute metrics for this config
                    metrics_sel = compute_metrics_for_config(tag_sel)
                    if metrics_sel['pcs_count_str'] is not None:
                        st.markdown(f"**Proposed Number of PCS:** {metrics_sel['pcs_count_str']}")
                    # System Nameplate Capacity
                    if system_nameplate_value is not None:
                        st.markdown(f"**System Nameplate Capacity:** {system_nameplate_value} {system_nameplate_unit}")
                    else:
                        st.markdown("**System Nameplate Capacity:**")
                    # System DC Usable Capacity
                    if system_dc_usable_value is not None:
                        st.markdown(f"**System DC Usable Capacity:** {system_dc_usable_value} {system_dc_usable_unit}")
                    else:
                        st.markdown("**System DC Usable Capacity:**")
                    # System AC Usable Capacity
                    if system_ac_usable_value is not None:
                        st.markdown(f"**System AC Usable Capacity:** {system_ac_usable_value} {system_ac_usable_unit}")
                    else:
                        st.markdown("**System AC Usable Capacity:**")
                    # System Rated DC Power
                    if system_rated_dc_power_value is not None:
                        st.markdown(f"**System Rated DC Power:** {system_rated_dc_power_value} {system_rated_dc_power_unit}")
                    else:
                        st.markdown("**System Rated DC Power:**")
                    # System Rated AC Power
                    if metrics_sel['rated_ac_power_value'] is not None:
                        st.markdown(f"**System Rated AC Power:** {metrics_sel['rated_ac_power_value']} {metrics_sel['rated_ac_power_unit']}")
                    else:
                        st.markdown("**System Rated AC Power:**")
                    st.markdown("<br>", unsafe_allow_html=True)
    elif pcs_options:
        # 未选择时显示两个选项
        pcs_spacer_left, pcs_center, pcs_spacer_right = st.columns([1, 8, 1])
        with pcs_center:
            pcs_col1, pcs_gap, pcs_col2 = st.columns([3.75, 0.5, 3.75])
            with pcs_col1:
                with st.container():
                    a_opt = pcs_options[0] if len(pcs_options) > 0 else None
                    if a_opt:
                        render_image_safe(a_opt.get("image"))
                        st.markdown('<div class="group-title">Configuration A</div>', unsafe_allow_html=True)
                        st.markdown(f"**System Components:** {a_opt.get('components','')}")
                        st.markdown(f"**Architecture:** {a_opt.get('architecture','')}")
                        st.markdown(f"**Origin:** {a_opt.get('origin','')}")
                        st.markdown(f"**Proposed Number of BESS:** {proposed_bess}")
                        # Confluence Cabinet per option
                        tag_a = infer_tag_from_image(a_opt.get('image',''))
                        conf_a = compute_confluence_cabinet_count(current_product, current_model, tag_a, proposed_bess)
                        if conf_a is not None:
                            st.markdown(f"**Proposed Number of Confluence Cabinet:** {conf_a}")
                        # Compute metrics for config A
                        metrics_a = compute_metrics_for_config(tag_a)
                        if metrics_a['pcs_count_str'] is not None:
                            st.markdown(f"**Proposed Number of PCS:** {metrics_a['pcs_count_str']}")
                        # System Nameplate Capacity
                        if system_nameplate_value is not None:
                            st.markdown(f"**System Nameplate Capacity:** {system_nameplate_value} {system_nameplate_unit}")
                        else:
                            st.markdown("**System Nameplate Capacity:**")
                        # System DC Usable Capacity
                        if system_dc_usable_value is not None:
                            st.markdown(f"**System DC Usable Capacity:** {system_dc_usable_value} {system_dc_usable_unit}")
                        else:
                            st.markdown("**System DC Usable Capacity:**")
                        # System AC Usable Capacity
                        if system_ac_usable_value is not None:
                            st.markdown(f"**System AC Usable Capacity:** {system_ac_usable_value} {system_ac_usable_unit}")
                        else:
                            st.markdown("**System AC Usable Capacity:**")
                        # System Rated DC Power
                        if system_rated_dc_power_value is not None:
                            st.markdown(f"**System Rated DC Power:** {system_rated_dc_power_value} {system_rated_dc_power_unit}")
                        else:
                            st.markdown("**System Rated DC Power:**")
                        # System Rated AC Power
                        if metrics_a['rated_ac_power_value'] is not None:
                            st.markdown(f"**System Rated AC Power:** {metrics_a['rated_ac_power_value']} {metrics_a['rated_ac_power_unit']}")
                        else:
                            st.markdown("**System Rated AC Power:**")
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("Select Configuration A", key='select_pcs_a', use_container_width=True):
                            st.session_state.data['selected_pcs'] = 'Configuration A'
                            st.session_state.show_results_section = True
                            st.rerun()
            with pcs_col2:
                with st.container():
                    b_opt = pcs_options[1] if len(pcs_options) > 1 else None
                    if b_opt:
                        render_image_safe(b_opt.get("image"))
                        st.markdown('<div class="group-title">Configuration B</div>', unsafe_allow_html=True)
                        st.markdown(f"**System Components:** {b_opt.get('components','')}")
                        st.markdown(f"**Architecture:** {b_opt.get('architecture','')}")
                        st.markdown(f"**Origin:** {b_opt.get('origin','')}")
                        st.markdown(f"**Proposed Number of BESS:** {proposed_bess}")
                        # Confluence Cabinet per option
                        tag_b = infer_tag_from_image(b_opt.get('image',''))
                        conf_b = compute_confluence_cabinet_count(current_product, current_model, tag_b, proposed_bess)
                        if conf_b is not None:
                            st.markdown(f"**Proposed Number of Confluence Cabinet:** {conf_b}")
                        # Compute metrics for config B
                        metrics_b = compute_metrics_for_config(tag_b)
                        if metrics_b['pcs_count_str'] is not None:
                            st.markdown(f"**Proposed Number of PCS:** {metrics_b['pcs_count_str']}")
                        # System Nameplate Capacity
                        if system_nameplate_value is not None:
                            st.markdown(f"**System Nameplate Capacity:** {system_nameplate_value} {system_nameplate_unit}")
                        else:
                            st.markdown("**System Nameplate Capacity:**")
                        # System DC Usable Capacity
                        if system_dc_usable_value is not None:
                            st.markdown(f"**System DC Usable Capacity:** {system_dc_usable_value} {system_dc_usable_unit}")
                        else:
                            st.markdown("**System DC Usable Capacity:**")
                        # System AC Usable Capacity
                        if system_ac_usable_value is not None:
                            st.markdown(f"**System AC Usable Capacity:** {system_ac_usable_value} {system_ac_usable_unit}")
                        else:
                            st.markdown("**System AC Usable Capacity:**")
                        # System Rated DC Power
                        if system_rated_dc_power_value is not None:
                            st.markdown(f"**System Rated DC Power:** {system_rated_dc_power_value} {system_rated_dc_power_unit}")
                        else:
                            st.markdown("**System Rated DC Power:**")
                        # System Rated AC Power
                        if metrics_b['rated_ac_power_value'] is not None:
                            st.markdown(f"**System Rated AC Power:** {metrics_b['rated_ac_power_value']} {metrics_b['rated_ac_power_unit']}")
                        else:
                            st.markdown("**System Rated AC Power:**")
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("Select Configuration B", key='select_pcs_b', use_container_width=True):
                            st.session_state.data['selected_pcs'] = 'Configuration B'
                            st.session_state.show_results_section = True
                            st.rerun()
    else:
        # 完全空白状态：不渲染任何图片或错误
        st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# Results & Analysis 部分
# ==========================================

if st.session_state.show_results_section:
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # 添加 Reload Options 按钮
    nav_spacer, nav_reload = st.columns([8.5, 1.5])
    with nav_reload:
        if st.button("Reload Options ↻", key='reload_options_results', use_container_width=True):
            # 重新加载产品选项，清除选择状态
            st.session_state.data['selected_pcs'] = None
            st.session_state.show_results_section = False
            st.rerun()
    
    st.markdown('<div class="main-title">Results & Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Capacity Analysis · Performance Metrics</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 显示 Cycle Degradation 数据框
    try:
        from algorithm import get_degradation_curve, compute_soh_percent, compute_yearly_dc_nameplate, compute_yearly_dc_usable, compute_yearly_ac_usable
        
        # 获取输入参数
        input_product = st.session_state.data.get('product', 'EDGE')
        input_model = st.session_state.data.get('edge_model', '760kWh')
        input_cycles = st.session_state.data.get('cycle', 365)
        input_discharge = current_c_rate if current_c_rate else 0.5
        input_capacity_unit = st.session_state.data.get('capacity_unit', 'kWh')
        
        # 确保 cycles 是整数
        try:
            input_cycles = int(input_cycles) if input_cycles else 365
        except:
            input_cycles = 365
        
        # 读取退化曲线
        deg_curve = get_degradation_curve(
            product=input_product,
            cycles_per_year=input_cycles,
            discharge_rate=input_discharge,
            debug=False  # 关闭调试
        )
        
        # 计算 SOH%
        soh_list = compute_soh_percent(
            degradation_curve=deg_curve,
            product=input_product
        )
        
        # 创建容器数量列表（0-20年）
        # 目前使用固定值，未来可以根据 Augmentation 动态调整
        containers_list = [proposed_bess] * 21
        
        # 计算 DC Nameplate (0-20年)
        dc_nameplate_list = compute_yearly_dc_nameplate(
            product=input_product,
            model=input_model,
            containers_list=containers_list,
            capacity_unit=input_capacity_unit
        )
        
        # 计算 DC Usable (0-20年)
        dc_usable_list = compute_yearly_dc_usable(
            product=input_product,
            model=input_model,
            containers_list=containers_list,
            soh_list=soh_list,
            capacity_unit=input_capacity_unit,
            dod=0.95,  # 固定 95%
            discharge_rate=input_discharge
        )
        
        # 计算 AC Usable (0-20年)
        ac_usable_list = compute_yearly_ac_usable(
            product=input_product,
            model=input_model,
            containers_list=containers_list,
            soh_list=soh_list,
            capacity_unit=input_capacity_unit,
            dod=0.95,  # 固定 95%
            discharge_rate=input_discharge,
            ac_conversion=0.9732  # 97.32%
        )
        
        # 创建显示框 - 类似图片的紧凑横向布局
        filter_info = deg_curve.get('filter_info', {})
        
        # 获取 DOD 值
        try:
            # 尝试从 BESS specs 获取 DOD
            specs = get_bess_specs_for(input_product, st.session_state.data.get('edge_model'))
            dod_value = specs.get('DOD', '95%')
            if not isinstance(dod_value, str):
                dod_value = f"{float(dod_value)*100:.0f}%"
        except:
            dod_value = "95%"
        
        # 构建退化因子的百分比字符串
        deg_percentages = []
        for year in range(21):
            val = deg_curve.get(f'deg_{year}')
            if val is not None:
                deg_percentages.append(f"{val*100:.2f}%")
            else:
                deg_percentages.append("N/A")
        
        # Adjust the table style to make it responsive and adapt to the screen width
        html_output = f"""
        <style>
            .deg-table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 12px;
                margin-bottom: 20px;
                table-layout: auto; /* Allow columns to adjust width automatically */
            }}
            .deg-table th, .deg-table td {{
                border: 1px solid #ddd;
                padding: 4px 1px;
                text-align: center !important;
            }}
            .deg-table th {{
                background-color: #f0f2f6;
                font-weight: 600;
                color: #31333F;
            }}
            .deg-table td {{
                background-color: #ffffff;
            }}
            .deg-table tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            .deg-table tr:hover {{
                background-color: #f5f5f5;
            }}
            .deg-table-container {{
                width: 100%; /* Ensure the container takes full width */
                overflow-x: auto; /* Add horizontal scroll for smaller screens */
                margin-bottom: 20px;
            }}
        </style>
        <div class="group-title">Cycling Degradation Curve</div>
        <div class="deg-table-container">
            <table class="deg-table">
                <thead>
                    <tr>
                        <th>Cell</th>
                        <th>Cycles</th>
                        <th>Temp(°C)</th>
                        <th>C/P rate</th>
                        <th>DOD</th>
                        <th>0 yr</th>
                        <th>1 yr</th>
                        <th>2 yr</th>
                        <th>3 yr</th>
                        <th>4 yr</th>
                        <th>5 yr</th>
                        <th>6 yr</th>
                        <th>7 yr</th>
                        <th>8 yr</th>
                        <th>9 yr</th>
                        <th>10 yr</th>
                        <th>11 yr</th>
                        <th>12 yr</th>
                        <th>13 yr</th>
                        <th>14 yr</th>
                        <th>15 yr</th>
                        <th>16 yr</th>
                        <th>17 yr</th>
                        <th>18 yr</th>
                        <th>19 yr</th>
                        <th>20 yr</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>{filter_info.get('target_cell')}</td>
                        <td>{filter_info.get('matched_cycle')}</td>
                        <td>25</td>
                        <td>{filter_info.get('matched_prate'):.2f}</td>
                        <td>{dod_value}</td>
                        {''.join([f'<td>{pct}</td>' for pct in deg_percentages])}
                    </tr>
                </tbody>
            </table>
        </div>
        """
        
        st.markdown(html_output, unsafe_allow_html=True)
        
    except Exception as e:
        st.warning(f"⚠️ Unable to load degradation curve: {str(e)}")
    
    # 创建表格数据
    import pandas as pd
    
    # 获取选中配置的 PCS 数量
    selected_pcs_count = None
    selected_pcs_tag = None
    if st.session_state.data.get('selected_pcs') and pcs_options:
        selected_label = st.session_state.data['selected_pcs']
        idx = 0 if selected_label == 'Configuration A' else 1
        opt = pcs_options[idx] if len(pcs_options) > idx else None
        if opt:
            tag = infer_tag_from_image(opt.get('image', ''))
            selected_pcs_tag = tag
            metrics = compute_metrics_for_config(tag)
            selected_pcs_count = metrics.get('pcs_count_str', '-')
    
    # 表格列名（9列）- 单位同步第一页选择
    capacity_unit_display = st.session_state.data.get('capacity_unit', 'kWh')
    columns = ["End of Year", "Containers in Service", "PCS in Service", "SOH (% of Original Capacity)", 
               f"DC Nameplate ({capacity_unit_display})", f"DC Usable ({capacity_unit_display})", 
               f"AC Usable @ MVT ({capacity_unit_display})", f"Min. Required ({capacity_unit_display})", 
               f"Δ ({capacity_unit_display})"]
    
    # 获取第一页填写的 Min. Required（容量需求）
    min_required_value = st.session_state.data.get('capacity')
    min_required_unit = st.session_state.data.get('capacity_unit', 'kWh')
    if min_required_value is not None:
        try:
            min_required_value = float(min_required_value)
            if min_required_unit == 'MWh':
                min_required_value = round(min_required_value, 2)
            else:
                min_required_value = round(min_required_value, 2)
        except:
            min_required_value = '-'
    else:
        min_required_value = '-'

    # 初始化 augmentation_plan（如果不存在）
    if 'augmentation_plan' not in st.session_state.data:
        st.session_state.data['augmentation_plan'] = [0] * 21
    
    # 判断是否启用 Augmentation 编辑模式
    is_augmentation_mode = (st.session_state.data.get('augmentation', '').strip().upper() == 'AUGMENTATION')
    
    # 如果是 Augmentation 模式，显示编辑界面
    if is_augmentation_mode:
        st.markdown('<div class="group-title">Augmentation Plan</div>', unsafe_allow_html=True)
        
        # 使用 Streamlit columns 创建紧凑的表格样式布局
        # 第一行：Year 标签（居中显示）
        year_cols = st.columns([0.8] + [1]*21)
        with year_cols[0]:
            st.markdown('<p style="text-align:center; margin:0; padding:4px 0; font-size:13px; font-weight:600;">Year</p>', unsafe_allow_html=True)
        for year in range(21):
            with year_cols[year + 1]:
                st.markdown(f'<p style="text-align:center; margin:0; padding:4px 0; font-size:13px; font-weight:600;">{year}</p>', unsafe_allow_html=True)
        
        # 第二行：Qty 输入框（紧凑排列）
        qty_cols = st.columns([0.8] + [1]*21)
        with qty_cols[0]:
            st.markdown('<p style="text-align:center; margin:0; padding:8px 0 4px 0; font-size:13px; font-weight:600;">Qty</p>', unsafe_allow_html=True)
        
        for year in range(21):
            with qty_cols[year + 1]:
                current_val = st.session_state.data['augmentation_plan'][year]
                # 使用 text_input 允许空值，然后转换为整数
                input_str = st.text_input(
                    f"y{year}",
                    value=str(int(current_val)) if current_val else "",
                    key=f'aug_year_{year}',
                    label_visibility="collapsed",
                    placeholder=None
                )
                # 转换并验证输入
                try:
                    new_val = int(input_str) if input_str.strip() else 0
                    new_val = max(0, new_val)  # 确保非负
                except (ValueError, AttributeError):
                    new_val = 0
                # 自动保存
                if new_val != st.session_state.data['augmentation_plan'][year]:
                    st.session_state.data['augmentation_plan'][year] = new_val
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 重新计算 containers_list（BOL + 累计 Aug）
        containers_list = []
        cumulative_aug = 0
        for year in range(21):
            cumulative_aug += st.session_state.data['augmentation_plan'][year]
            containers_list.append(proposed_bess + cumulative_aug)
        
        # 重新计算所有依赖的数据
        dc_nameplate_list = compute_yearly_dc_nameplate(
            product=input_product,
            model=input_model,
            containers_list=containers_list,
            capacity_unit=input_capacity_unit
        )
        
        dc_usable_list = compute_yearly_dc_usable(
            product=input_product,
            model=input_model,
            containers_list=containers_list,
            soh_list=soh_list,
            capacity_unit=input_capacity_unit,
            dod=0.95,
            discharge_rate=input_discharge,
            augmentation_plan=st.session_state.data['augmentation_plan']  # 传递 augmentation_plan
        )
        
        ac_usable_list = compute_yearly_ac_usable(
            product=input_product,
            model=input_model,
            containers_list=containers_list,
            soh_list=soh_list,
            capacity_unit=input_capacity_unit,
            dod=0.95,
            discharge_rate=input_discharge,
            ac_conversion=0.9732,
            augmentation_plan=st.session_state.data['augmentation_plan']  # 传递 augmentation_plan
        )
    else:
        # 非 Augmentation 模式：使用固定的 proposed_bess
        containers_list = [proposed_bess] * 21
    
    # 创建表格数据（21行：0-20）
    data = []
    for year in range(0, 21):
        # 获取当前年份的容器数
        current_containers = containers_list[year] if year < len(containers_list) else proposed_bess
        
        # 动态计算当前年份的 PCS 数量（基于当前容器数）
        year_pcs_count = "-"
        if selected_pcs_tag and selected_pcs_tag not in ('760', '760+dc'):
            try:
                # 使用当前年份的容器数重新计算 PCS
                pcs_str = compute_pcs_count(
                    product=current_product,
                    option_tag=selected_pcs_tag,
                    proposed_bess=current_containers,  # 使用当前年份的容器数
                    power_kw=current_power_kw,
                    discharge_rate=(st.session_state.data.get('discharge') or current_c_rate),
                )
                year_pcs_count = pcs_str if pcs_str not in ('-', '') else "-"
            except Exception:
                year_pcs_count = "-"
        
        # 获取 SOH% 值（如果存在）
        soh_value = ""
        soh_is_valid = False
        try:
            if 'soh_list' in locals() and soh_list and year < len(soh_list):
                soh_val = soh_list[year]
                if soh_val is not None:
                    soh_value = f"{soh_val * 100:.2f}%"
                    soh_is_valid = True
        except:
            pass
        
        # 如果 SOH 无效，所有计算值都显示 "-"
        if not soh_is_valid:
            dc_nameplate_value = "-"
            dc_usable_value = "-"
            ac_usable_value = "-"
            delta_value = "-"
        else:
            # 获取 DC Nameplate 值
            dc_nameplate_value = ""
            try:
                if 'dc_nameplate_list' in locals() and dc_nameplate_list and year < len(dc_nameplate_list):
                    dc_val = dc_nameplate_list[year]
                    if dc_val is not None:
                        dc_nameplate_value = f"{dc_val:,.2f}"
            except:
                pass
            
            # 获取 DC Usable 值
            dc_usable_value = ""
            try:
                if 'dc_usable_list' in locals() and dc_usable_list and year < len(dc_usable_list):
                    dc_val = dc_usable_list[year]
                    if dc_val is not None:
                        dc_usable_value = f"{dc_val:,.2f}"
            except:
                pass
            
            # 获取 AC Usable 值
            ac_usable_value = ""
            try:
                if 'ac_usable_list' in locals() and ac_usable_list and year < len(ac_usable_list):
                    ac_val = ac_usable_list[year]
                    if ac_val is not None:
                        ac_usable_value = f"{ac_val:,.2f}"
            except:
                pass
            
            # 获取 solution 类型（AC 或 DC）
            solution_type = st.session_state.data.get('edge_solution', '').strip().upper()
            
            # 计算 Δ (Delta)
            delta_value = ""
            try:
                if min_required_value != '-' and min_required_value is not None:
                    min_val = float(min_required_value)
                    if solution_type == 'AC':
                        # 用 AC Usable - Min. Required
                        if 'ac_usable_list' in locals() and ac_usable_list and year < len(ac_usable_list):
                            ac_val = ac_usable_list[year]
                            if ac_val is not None:
                                delta_value = f"{ac_val - min_val:,.2f}"
                    else:
                        # 用 DC Usable - Min. Required
                        if 'dc_usable_list' in locals() and dc_usable_list and year < len(dc_usable_list):
                            dc_val = dc_usable_list[year]
                            if dc_val is not None:
                                delta_value = f"{dc_val - min_val:,.2f}"
            except:
                delta_value = ""
        data.append({
            columns[0]: str(year),  # End of Year
            columns[1]: str(int(current_containers)),  # Containers in Service (使用动态值)
            columns[2]: year_pcs_count,  # PCS in Service (使用动态计算的值)
            columns[3]: soh_value,  # SOH (% of Original Capacity)
            columns[4]: dc_nameplate_value,  # DC Nameplate (unit)
            columns[5]: dc_usable_value,  # DC Usable (unit)
            columns[6]: ac_usable_value,  # AC Usable @ MVT (unit)
            columns[7]: min_required_value,  # Min. Required (unit)
            columns[8]: delta_value  # Δ (unit)
        })
    
    df = pd.DataFrame(data)
    
    # 使用 HTML 表格替代 st.dataframe，完全控制样式
    st.markdown('<div class="group-title">Capacity Analysis Table</div>', unsafe_allow_html=True)
    
    # 生成 HTML 表格
    html_table = """
    <style>
        .custom-table {
            width: 100%;  /* 表格宽度设置为 100% */
            border-collapse: collapse;
            font-size: 14px;  /* 恢复字体大小 */
            margin-top: 10px;
        }
        .custom-table th, .custom-table td {
            border: 1px solid #ddd;
            padding: 6px 8px;  /* 恢复单元格间距 */
            text-align: center !important;
        }
        .custom-table th {
            background-color: #f0f2f6;
            font-weight: 600;
            color: #31333F;
        }
        .custom-table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .custom-table tr:hover {
            background-color: #f5f5f5;
        }
        .table-container {
            width: 100%;  /* 容器宽度设置为 100% */
            overflow-x: auto;  /* 添加水平滚动条以适应屏幕 */
        }
    </style>
    <div class="table-container">
        <table class="custom-table">
            <thead>
                <tr>
    """
    
    # 添加表头
    for col in df.columns:
        html_table += f"<th>{col}</th>"
    html_table += "</tr></thead><tbody>"
    
    # 添加数据行
    for _, row in df.iterrows():
        html_table += "<tr>"
        for val in row:
            html_table += f"<td>{val if val else '-'}</td>"
        html_table += "</tr>"
    
    html_table += "</tbody></table></div>"
    
    st.markdown(html_table, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 绘图区域
    # 使用 st.container() 确保图表占据整个可用宽度
    with st.container(): 
        st.markdown('<div class="group-title">Performance Chart</div>', unsafe_allow_html=True)

        # 生成两条线：Min. Required（常量线）和 Usable（DC 或 AC）
        chart_years = list(range(21))
        solution_type = st.session_state.data.get('edge_solution', '').strip().upper()
        if solution_type == 'AC':
            usable_curve = ac_usable_list if 'ac_usable_list' in locals() else []
            usable_label = 'AC Usable'
        else:
            usable_curve = dc_usable_list if 'dc_usable_list' in locals() else []
            usable_label = 'DC Usable'
        min_required_curve = [min_required_value] * 21 if min_required_value not in ('-', None) else [0] * 21

        # 使用 matplotlib 绘制图表
        fig, ax = plt.subplots(figsize=(20, 6))  
        ax.plot(chart_years, usable_curve, label=usable_label)
        ax.fill_between(chart_years, usable_curve, alpha=0.2)
        ax.plot(chart_years, min_required_curve, label='Min. Required', linestyle='-', color='red')
        ax.set_xlabel('Year', fontsize=16)
        ax.set_ylabel('Capacity', fontsize=16)
        ax.tick_params(axis='both', which='major', labelsize=14)
        max_capacity = max(max(usable_curve, default=0), max(min_required_curve, default=0))
        ax.set_ylim(bottom=0, top=max_capacity * 1.5)
        ax.set_xlim(left=0, right=20)
        ax.set_xticks(chart_years)
        ax.legend(fontsize=14)
        ax.grid(True, linestyle='--', alpha=0.6)
        fig.tight_layout()

    # 在 Streamlit 中显示图表
    st.pyplot(fig, use_container_width=True)
    
    # 添加 Export Configuration 按钮到右下角
    st.markdown("<br>", unsafe_allow_html=True)
    export_col_left, export_col_right = st.columns([8.5, 1.5])
    
    with export_col_right:
        if st.button("Export Configuration", key='export_config_btn', use_container_width=True):
            st.success("✓ Press **Ctrl+P** (Windows) or **Cmd+P** (Mac) to print!")
