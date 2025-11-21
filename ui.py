"""
Streamlit 销售工具 - 项目信息输入页面
"""
import streamlit as st
from algorithm import (
    to_kw, to_kwh, calculate_c_rate, format_c_rate, fetch_temperature
)

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
        width: 150px;
    }}
    .stButton>button:hover {{
        background-color: rgba({THEME_RGB[0]}, {THEME_RGB[1]}, {THEME_RGB[2]}, 0.85);
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
    
    /* Fetch Temp 按钮自适应 */
    div[data-testid="column"] .stButton>button {{
        width: 100%;
        padding: 6px 12px;
        font-size: 12px;
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
        }}
    }}
    
    /* 超大屏幕适配 */
    @media (min-width: 1920px) {{
        .main .block-container {{
            max-width: 1600px;
        }}
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
        'augmentation': ''
    }

# 标题
st.markdown('<div class="main-title">Project Overview</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Basic Information · Product Selection · System Configuration</div>', unsafe_allow_html=True)

# 创建两列布局
col_left, col_right = st.columns(2)

with col_left:
    # ===== Basic Info =====
    with st.container():
        st.markdown('<div class="group-title">Basic Info</div>', unsafe_allow_html=True)
        
        customer = st.text_input("Customer Name:", value=st.session_state.data['customer'], key='customer')
        project = st.text_input("Project Name:", value=st.session_state.data['project'], key='project')
        usecase = st.text_input("Use Case:", value=st.session_state.data['usecase'], key='usecase')
        life_stage = st.text_input("Life Stage (BOL/EOL):", value=st.session_state.data['life_stage'], key='life_stage')
        
        # Location with fetch button
        location_col1, location_col2 = st.columns([2.5, 1])
        with location_col1:
            location = st.text_input("Location (City or Zipcode):", value=st.session_state.data['location'], key='location')
        with location_col2:
            st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
            if st.button("Fetch Temp", use_container_width=True):
                if location:
                    with st.spinner("Fetching temperature data..."):
                        max_temp, min_temp, tooltip = fetch_temperature(location)
                        if max_temp is not None:
                            st.session_state.data['tmax_c'] = max_temp
                            st.session_state.data['tmin_c'] = min_temp
                            st.success(f"✓ Temperature fetched!")
                            st.info(tooltip)
                        else:
                            st.error(tooltip)
                else:
                    st.warning("Please enter a location first")
        
        # Temperature fields (read-only display)
        max_temp_display = st.session_state.data['tmax_c'] if st.session_state.data['tmax_c'] is not None else ""
        min_temp_display = st.session_state.data['tmin_c'] if st.session_state.data['tmin_c'] is not None else ""
        
        st.text_input("Max Temp (°C):", value=str(max_temp_display), key='max_temp', disabled=True)
        st.text_input("Min Temp (°C):", value=str(min_temp_display), key='min_temp', disabled=True)
    
    # ===== Product =====
    with st.container():
        st.markdown('<div class="group-title">Product</div>', unsafe_allow_html=True)
        
        product = st.selectbox(
            "Product:",
            ["", "EDGE", "GRID5015", "GRID3421"],
            index=["", "EDGE", "GRID5015", "GRID3421"].index(st.session_state.data['product']) if st.session_state.data['product'] in ["", "EDGE", "GRID5015", "GRID3421"] else 0,
            key='product'
        )
        
        # EDGE Model (only show if EDGE is selected)
        if product == "EDGE":
            edge_model = st.selectbox(
                "EDGE Model:",
                ["", "760kWh", "676kWh", "591kWh", "507kWh", "422kWh", "338kWh"],
                index=["", "760kWh", "676kWh", "591kWh", "507kWh", "422kWh", "338kWh"].index(st.session_state.data['edge_model']) if st.session_state.data['edge_model'] in ["", "760kWh", "676kWh", "591kWh", "507kWh", "422kWh", "338kWh"] else 0,
                key='edge_model'
            )
        else:
            edge_model = ""
            st.session_state.data['edge_model'] = ""
        
        # Solution Type (always show)
        edge_solution = st.selectbox(
            "Solution Type:",
            ["", "DC", "AC"],
            index=["", "DC", "AC"].index(st.session_state.data['edge_solution']) if st.session_state.data['edge_solution'] in ["", "DC", "AC"] else 0,
            key='edge_solution'
        )

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
                value=float(st.session_state.data['power']) if st.session_state.data['power'] else 0.0,
                step=1.0,
                format="%.2f",
                key='power_input'
            )
        with power_col2:
            st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
            power_unit = st.selectbox("Unit", ["kW", "MW"], key='power_unit_select', label_visibility="collapsed")
        
        # Capacity with unit
        capacity_col1, capacity_col2 = st.columns([3, 1])
        with capacity_col1:
            capacity = st.number_input(
                "Capacity:",
                min_value=0.0,
                value=float(st.session_state.data['capacity']) if st.session_state.data['capacity'] else 0.0,
                step=1.0,
                format="%.2f",
                key='capacity_input'
            )
        with capacity_col2:
            st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
            capacity_unit = st.selectbox("Unit", ["kWh", "MWh"], key='capacity_unit_select', label_visibility="collapsed")
        
        # Calculate and display C-rate
        power_kw = to_kw(power if power > 0 else None, power_unit)
        capacity_kwh = to_kwh(capacity if capacity > 0 else None, capacity_unit)
        c_rate = calculate_c_rate(power_kw, capacity_kwh)
        c_rate_display = format_c_rate(c_rate) if c_rate else ""
        
        st.text_input("Discharge Rate:", value=c_rate_display, key='discharge', disabled=True)
        
        cycle_num = st.text_input("Cycle Number:", value=st.session_state.data['cycle'], key='cycle')
    
    # ===== Lifecycle =====
    with st.container():
        st.markdown('<div class="group-title">Lifecycle</div>', unsafe_allow_html=True)
        
        delivery = st.text_input("Delivery Date:", value=st.session_state.data['delivery'], key='delivery')
        cod = st.text_input("COD:", value=st.session_state.data['cod'], key='cod')
        augmentation = st.selectbox(
            "Augmentation & Overbuild:",
            ["", "N/A", "Augmentation", "Overbuild"],
            index=["", "N/A", "Augmentation", "Overbuild"].index(st.session_state.data['augmentation']) if st.session_state.data['augmentation'] in ["", "N/A", "Augmentation", "Overbuild"] else 0,
            key='augmentation'
        )
        # 占位符，使两列底部对齐
        st.markdown('<div style="height: 1px;"></div>', unsafe_allow_html=True)

# Bottom navigation
st.write("")
col1, col2, col3 = st.columns([3, 1, 3])
with col2:
    if st.button("Next ➔", key='next_btn'):
        # 保存所有数据到 session_state
        st.session_state.data.update({
            'customer': customer,
            'project': project,
            'usecase': usecase,
            'life_stage': life_stage,
            'location': location,
            'power': power if power > 0 else None,
            'power_unit': power_unit,
            'capacity': capacity if capacity > 0 else None,
            'capacity_unit': capacity_unit,
            'power_kw': power_kw,
            'capacity_kwh': capacity_kwh,
            'discharge': c_rate_display,
            'cycle': cycle_num,
            'product': product,
            'edge_model': edge_model,
            'edge_solution': edge_solution,
            'delivery': delivery,
            'cod': cod,
            'augmentation': augmentation
        })
        
        # TODO: 跳转到下一页（PCS选择）
        st.success("✓ Data saved! (Next page coming soon...)")
        st.balloons()
