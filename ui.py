"""
Streamlit 销售工具 - 项目信息输入页面
"""
import streamlit as st
from algorithm import (
    to_kw, to_kwh, calculate_c_rate, format_c_rate, fetch_temperature, get_pcs_options
)
from datetime import datetime
import io
from PIL import Image
import base64

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
    .stTextInput > div > div > input::placeholder,
    .stNumberInput > div > div > input::placeholder {{
        color: transparent;
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
    }}
    .stDataFrame td {{
        font-size: 10px;
        padding: 2px 4px !important;
    }}
    .stDataFrame [data-testid="stDataFrame"] {{
        height: auto !important;
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
        project = st.text_input("Project Name:", value=st.session_state.data['project'], key='project')
        usecase = st.text_input("Use Case:", value=st.session_state.data['usecase'], key='usecase')
        life_stage = st.text_input("Life Stage (BOL/EOL):", value=st.session_state.data['life_stage'], key='life_stage')
        
        # Location with fetch button
        location_col1, location_col2 = st.columns([0.82, 0.18])
        with location_col1:
            location = st.text_input("Location (City or Zipcode):", value=st.session_state.data['location'], key='location')
        with location_col2:
            st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
            fetch_clicked = st.button("Fetch Temp", use_container_width=True)
        
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
        
        # Calculate and display C-rate
        power_kw = to_kw(power if power and power > 0 else None, power_unit)
        capacity_kwh = to_kwh(capacity if capacity and capacity > 0 else None, capacity_unit)
        c_rate = calculate_c_rate(power_kw, capacity_kwh)
        c_rate_display = format_c_rate(c_rate) if c_rate else ""
        
        # 使用 markdown 显示 C-rate (模拟 text_input 样式)
        st.markdown('<p style="margin-bottom: 0.25rem; font-size: 14px; font-weight: 400;">Discharge Rate:</p>', unsafe_allow_html=True)
        st.markdown(f'<div style="background-color: #f0f2f6; padding: 0.5rem 0.75rem; border-radius: 0.5rem; margin-bottom: 1rem; font-size: 16px; color: #31333F;">{c_rate_display if c_rate_display else "&nbsp;"}</div>', unsafe_allow_html=True)
        
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
                # 保存数据
                st.session_state.data.update({
                    'customer': customer,
                    'project': project,
                    'usecase': usecase,
                    'life_stage': life_stage,
                    'location': location,
                    'power': power if power and power > 0 else None,
                    'power_unit': power_unit,
                    'capacity': capacity if capacity and capacity > 0 else None,
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
    with edit_col2:
        if product_inline == "EDGE":
            model_inline = st.selectbox(
                "Model",
                ["", "760kWh", "676kWh", "591kWh", "507kWh", "422kWh", "338kWh"],
                index=["", "760kWh", "676kWh", "591kWh", "507kWh", "422kWh", "338kWh"].index(st.session_state.data.get('edge_model','')) if st.session_state.data.get('edge_model','') in ["", "760kWh", "676kWh", "591kWh", "507kWh", "422kWh", "338kWh"] else 0,
                key='model_inline'
            )
        else:
            model_inline = ""
    with edit_col3:
        solution_inline = st.selectbox(
            "Solution",
            ["", "DC", "AC"],
            index=["", "DC", "AC"].index(st.session_state.data.get('edge_solution','')) if st.session_state.data.get('edge_solution','') in ["", "DC", "AC"] else 0,
            key='solution_inline'
        )

    # 导航与重载（仅保留 Reload Options 按钮）
    nav_spacer, nav_reload = st.columns([8.5, 1.5])
    with nav_reload:
        if st.button("↻ Load Options", key='reload_options', use_container_width=True):
            # 更新产品相关选择
            st.session_state.data['product'] = product_inline
            st.session_state.data['edge_model'] = model_inline
            st.session_state.data['edge_solution'] = solution_inline
            # 从当前输入控件重算 C-rate（无需回到第一页点击 Next）
            try:
                cur_power = st.session_state.get('power_input', None)
                cur_power_unit = st.session_state.get('power_unit_select', 'kW')
                cur_capacity = st.session_state.get('capacity_input', None)
                cur_capacity_unit = st.session_state.get('capacity_unit_select', 'kWh')
                cur_power_kw = to_kw(cur_power if cur_power and cur_power > 0 else None, cur_power_unit)
                # Use correct variable names
                cur_capacity_kwh = to_kwh(cur_capacity if cur_capacity and cur_capacity > 0 else None, cur_capacity_unit)
                cur_c_rate = calculate_c_rate(cur_power_kw, cur_capacity_kwh)
                st.session_state.data['power_kw'] = cur_power_kw
                st.session_state.data['capacity_kwh'] = cur_capacity_kwh
                st.session_state.data['discharge'] = format_c_rate(cur_c_rate) if cur_c_rate else ""
            except Exception:
                pass
            # 清空选中并刷新
            st.session_state.data['selected_pcs'] = None
            st.session_state.show_results_section = False
            st.rerun()

    # 准备选项数据（按当前输入生成)，空白状态处理
    current_product = st.session_state.data.get('product')
    current_model = st.session_state.data.get('edge_model')
    current_solution = st.session_state.data.get('edge_solution')
    # 使用最新保存的功率/容量
    current_power_kw = st.session_state.data.get('power_kw')
    current_capacity_kwh = st.session_state.data.get('capacity_kwh')
    current_c_rate = calculate_c_rate(current_power_kw, current_capacity_kwh)

    # 特定组合不推荐：EDGE 422/338kWh；GRID5015 的 DC
    no_recommend = (
        (current_product == 'EDGE' and current_model in ['422kWh', '338kWh']) or
        (current_product == 'GRID5015' and current_solution == 'DC')
    )

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
                    st.markdown(f"**Title:** {opt.get('title','')}")
                    st.markdown(f"**Description:** {opt.get('description','')}")
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
                        st.markdown(f"**Title:** {a_opt.get('title','')}")
                        st.markdown(f"**Description:** {a_opt.get('description','')}")
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
                        st.markdown(f"**Title:** {b_opt.get('title','')}")
                        st.markdown(f"**Description:** {b_opt.get('description','')}")
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
    st.markdown('<div id="results-section"></div>', unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # 添加导航按钮
    nav_col1, nav_col2, nav_col3 = st.columns([7.6, 1.2, 1.2])
    with nav_col2:
        if st.button("← Edit Info", key='edit_info_results', use_container_width=True):
            st.session_state.show_pcs_section = False
            st.session_state.show_results_section = False
            st.rerun()
    with nav_col3:
        if st.button("↻ Change PCS", key='change_pcs', use_container_width=True):
            st.session_state.data['selected_pcs'] = None
            st.session_state.show_results_section = False
            st.rerun()
    
    st.markdown('<div class="main-title">Results & Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Capacity Analysis · Performance Metrics</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 创建表格数据
    import pandas as pd
    
    # 表格列名（9列）
    columns = ["End of Year", "Containers in Service", "PCS in Service", "SOH (% of Original Capacity)", 
               "DC Nameplate", "DC Usable", "AC Usable @ MVT", "Min. Required", "Δ"]
    
    # 创建示例数据（20行：1-20）
    data = []
    for year in range(1, 21):
        data.append({
            "End of Year": year,
            "Containers in Service": "",
            "PCS in Service": "",
            "SOH (% of Original Capacity)": "",
            "DC Nameplate": "",
            "DC Usable": "",
            "AC Usable @ MVT": "",
            "Min. Required": "",
            "Δ": ""
        })
    
    df = pd.DataFrame(data)
    
    # 显示表格 - 精确调整高度，刚好显示20行数据
    st.markdown('<div class="group-title">Capacity Analysis Table</div>', unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True, hide_index=True, height=738)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 绘图区域
    st.markdown('<div class="group-title">Performance Chart</div>', unsafe_allow_html=True)
    
    # 示例：使用 Streamlit 的 line_chart
    import numpy as np
    chart_data = pd.DataFrame(
        np.random.randn(20, 3),
        columns=['DC Usable', 'AC Usable', 'Min. Required']
    )
    st.line_chart(chart_data)
    
    # 添加 Export Configuration 按钮到右下角
    st.markdown("<br>", unsafe_allow_html=True)
    export_col_left, export_col_right = st.columns([8.5, 1.5])
    
    with export_col_right:
        if st.button("Export Configuration", key='export_config_btn', use_container_width=True):
            # TODO: 添加导出配置的逻辑
            st.success("✓ Ready to export!")
            st.info("Export functionality will be implemented here.")
