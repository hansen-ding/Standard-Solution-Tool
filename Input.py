import sys
import requests
import os, json
from datetime import date
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QComboBox, QVBoxLayout, QHBoxLayout,
    QGroupBox, QSpacerItem, QSizePolicy, QScrollArea, QPushButton
)
from PyQt5.QtGui import QFont, QDoubleValidator
from PyQt5.QtWidgets import QMessageBox, QGridLayout
from PyQt5.QtCore import Qt

THEME_RGB = (234, 85, 32)

def make_group(title):
    box = QGroupBox(title)
    box.setStyleSheet(
        f"""
        QGroupBox {{
            font-weight:500;
            border: 2px solid rgba({THEME_RGB[0]}, {THEME_RGB[1]}, {THEME_RGB[2]}, 0.7);
            border-radius:10px;
            margin-top:12px;
            padding:10px 12px 12px 12px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left:10px;
            padding:0 6px;
        }}
        """
    )
    return box

class BESSApp(QWidget):
    def __init__(self, state=None, save_path=None):
        super().__init__()
        self.setWindowTitle("Sizing Tool")
        self.resize(1000, 640)
        self.setStyleSheet("""
            QWidget {{ background:#F7F7F7; }}
            QLabel{{ font-size:12px; }}
            QLineEdit, QComboBox{{ font-size:12px; height:32px; }}
            QPushButton#nextBtn {{
                background-color: rgb({THEME_RGB[0]}, {THEME_RGB[1]}, {THEME_RGB[2]});
                color: white; font-weight:600; border:none; border-radius:8px;
                padding:8px 18px;
            }}
            QPushButton#nextBtn:hover {{ filter: brightness(1.05); }}
        """)
        # 默认保存路径
        self.save_path = save_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "sizing_state.json")
        # 初始空 state；只在外部传入时使用，不自动加载文件
        self.state = {"interface": {}, "degradation": {}}
        # 先构建 UI 控件
        self.initUI()
        self.deg_win = None
        # 只有当外部传入 state 时才使用（不自动从文件加载）
        if isinstance(state, dict) and state:
            self.state = state
            try:
                self.apply_state_to_ui()
            except Exception:
                pass

    # ---- state restore ----
    def apply_state_to_ui(self):
        data = self.state.get("interface", {}) if isinstance(self.state, dict) else {}
        if not data:
            return
        # 简单工具：安全设值 combo (若目标不在选项中则追加)
        def set_combo(cb, text):
            if text is None:
                return
            t = str(text).strip()
            if t == "":
                return
            idx = cb.findText(t)
            if idx < 0:
                cb.addItem(t)
                idx = cb.findText(t)
            if idx >= 0:
                # 避免触发联动的临时信号
                cb.blockSignals(True)
                cb.setCurrentIndex(idx)
                cb.blockSignals(False)

        # 文本类
        self.customer.setText(data.get("customer", ""))
        self.project.setText(data.get("project", ""))
        self.usecase.setText(data.get("usecase", ""))
        self.life.setText(data.get("life_stage", ""))
        self.location.setText(data.get("location", ""))
        self.max_temp.setText(str(data.get("tmax_c", "")))
        self.min_temp.setText(str(data.get("tmin_c", "")))
        self.cycle_num.setText(str(data.get("cycle", "")))
        self.delivery.setText(data.get("delivery", ""))
        self.cod.setText(data.get("cod", ""))

        # 数字+单位：反向换算
        power_kw = data.get("power_kw")
        power_unit_disp = data.get("power_unit_display", "kW") or "kW"
        if power_kw is not None:
            if power_unit_disp == "MW":
                show = power_kw / 1000.0
            else:
                show = power_kw
            self.power.setText(("%g" % show))
        set_combo(self.power_unit, power_unit_disp)

        capacity_kwh = data.get("capacity_kwh")
        capacity_unit_disp = data.get("capacity_unit_display", "kWh") or "kWh"
        if capacity_kwh is not None:
            if capacity_unit_disp == "MWh":
                show_c = capacity_kwh / 1000.0
            else:
                show_c = capacity_kwh
            self.capacity.setText(("%g" % show_c))
        set_combo(self.capacity_unit, capacity_unit_disp)

        # 组合框
        set_combo(self.product, data.get("product"))
        # 手动调用 EDGE 显示/隐藏
        self.toggle_edge_options(self.product.currentText())
        set_combo(self.edge_model, data.get("edge_model"))
        set_combo(self.edge_solution, data.get("edge_solution"))
        # discharge 现在是自动计算的，不需要手动设置
        set_combo(self.augmetation, data.get("augmentation"))
        
        # 恢复数据后重新计算 discharge rate
        self.calculate_discharge_rate()

        # Tooltip 保留（若之前已有 API 结果）无需修改
        # 完成



    # ---- row builders ----
    def row_text(self, label, placeholder="", readonly=False):
        container = QWidget()
        row = QHBoxLayout(container); row.setContentsMargins(0,0,0,0)
        lab = QLabel(label); lab.setMinimumWidth(150)
        w = QLineEdit()
        if placeholder: w.setPlaceholderText(placeholder)
        w.setReadOnly(readonly)
        row.addWidget(lab); row.addWidget(w, 1)
        return container, w

    def row_combo(self, label, items):
        container = QWidget()
        row = QHBoxLayout(container); row.setContentsMargins(0,0,0,0)
        lab = QLabel(label); lab.setMinimumWidth(150)
        cb = QComboBox(); cb.addItems(items)
        row.addWidget(lab); row.addWidget(cb, 1)
        return container, cb

    def row_num_with_unit(self, label, units):
        container = QWidget()
        row = QHBoxLayout(container); row.setContentsMargins(0,0,0,0)
        lab = QLabel(label); lab.setMinimumWidth(150)
        num = QLineEdit()
        v = QDoubleValidator(0.0, 1e9, 3)
        v.setNotation(QDoubleValidator.StandardNotation)
        num.setValidator(v)
        unit = QComboBox(); unit.addItems(units)
        row.addWidget(lab)
        row.addWidget(num, 2)
        row.addWidget(unit, 1)
        return container, num, unit

    def initUI(self):
        # ===== 顶层布局：滚动内容 + 底部按钮条 =====
        root = QVBoxLayout(self); root.setContentsMargins(12,12,12,12); root.setSpacing(10)

        # ======= 标题部分 =======
        title = QLabel("Project Info")
        title.setAlignment(Qt.AlignHCenter)
        title.setStyleSheet(f"color: rgb({THEME_RGB[0]}, {THEME_RGB[1]}, {THEME_RGB[2]}); font-size:20px; font-weight:700;")
        
        subtitle = QLabel("Basic Information · Product Selection · System Configuration")
        subtitle.setAlignment(Qt.AlignHCenter)
        subtitle.setStyleSheet("color:#5f5f5f; font-size:14px;")
        
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(10)

        scroll = QScrollArea(self); scroll.setWidgetResizable(True)
        root.addWidget(scroll, 1)

        content = QWidget(); scroll.setWidget(content)
        cols = QHBoxLayout(content); cols.setSpacing(12)

        left_col = QVBoxLayout(); right_col = QVBoxLayout()
        cols.addLayout(left_col, 1); cols.addLayout(right_col, 1)

        # --- Left: Basic Info ---
        g1 = make_group("Basic Info"); g1_layout = QVBoxLayout(g1)
        self.customer_row, self.customer = self.row_text("Customer Name:")
        self.project_row,  self.project  = self.row_text("Project Name:")
        self.usecase_row,  self.usecase  = self.row_text("Use Case:")
        self.life_stage,   self.life     = self.row_text("Life Stage (BOL/EOL):")
        
        loc_container = QWidget()
        loc_grid = QGridLayout(loc_container); loc_grid.setContentsMargins(0,0,0,0)
        loc_label = QLabel("Location (City or Zipcode):"); loc_label.setMinimumWidth(150)
        self.location = QLineEdit()
        self.location.setPlaceholderText("")
        loc_btn = QPushButton("Fetch Temp")
        loc_btn.clicked.connect(self.fill_temperature)

        loc_grid.addWidget(loc_label, 0, 0)
        loc_grid.addWidget(self.location, 0, 1)
        loc_grid.addWidget(loc_btn,    0, 2)

        self.location_row = loc_container
        self.max_row, self.max_temp = self.row_text("Max Temp (°C):", readonly=True)
        self.min_row, self.min_temp = self.row_text("Min Temp (°C):", readonly=True)
        self.location.returnPressed.connect(self.fill_temperature)
        for w in (self.customer_row, self.project_row, self.usecase_row,
                  self.life_stage, self.location_row, self.max_row, self.min_row):
            g1_layout.addWidget(w)
        left_col.addWidget(g1)

        # --- Left: Product ---
        g3 = make_group("Product"); g3_layout = QVBoxLayout(g3)
        self.product_row, self.product = self.row_combo("Product:", ["", "EDGE", "GRID5015", "GRID3421"])
        self.edge_model_row, self.edge_model = self.row_combo("EDGE Model:", ["", "760kWh", "676kWh", "591kWh", "507kWh", "422kWh", "338kWh"])
        self.edge_solution_row, self.edge_solution = self.row_combo("Solution Type:", ["", "DC", "AC"])
        g3_layout.addWidget(self.product_row)
        g3_layout.addWidget(self.edge_model_row)
        g3_layout.addWidget(self.edge_solution_row)
        # 默认始终显示解决方案 (DC/AC)；型号仅 EDGE 显示
        self.edge_model_row.setVisible(False)
        self.edge_solution_row.setVisible(True)
        self.product.currentTextChanged.connect(self.toggle_edge_options)
        left_col.addWidget(g3)

        # --- Right: System Design ---
        g2 = make_group("System Design"); g2_layout = QVBoxLayout(g2)
        self.power_row, self.power, self.power_unit = self.row_num_with_unit("Power:", ["kW", "MW"])
        self.capacity_row, self.capacity, self.capacity_unit = self.row_num_with_unit("Capacity:", ["kWh", "MWh"])
        
        # 连接信号以自动计算 C-rate
        self.power.textChanged.connect(self.calculate_discharge_rate)
        self.power_unit.currentTextChanged.connect(self.calculate_discharge_rate)
        self.capacity.textChanged.connect(self.calculate_discharge_rate)
        self.capacity_unit.currentTextChanged.connect(self.calculate_discharge_rate)
        
        self.discharge_row, self.discharge = self.row_text("Discharge Rate:", readonly=True)
        self.discharge.setPlaceholderText("")
        self.cycle_row, self.cycle_num = self.row_text("Cycle Number:")
        for w in (self.power_row, self.capacity_row, self.discharge_row, self.cycle_row):
            g2_layout.addWidget(w)
        right_col.addWidget(g2)

        # --- Right: Lifecycle ---
        g4 = make_group("Lifecycle"); g4_layout = QVBoxLayout(g4)
        self.delivery_row, self.delivery = self.row_text("Delivery Date:")
        self.cod_row,      self.cod      = self.row_text("COD:")
        self.augmentation, self.augmetation = self.row_combo("Augmentation Plan:", ["", "Yes", "No"])
        for w in (self.delivery_row, self.cod_row, self.augmentation):
            g4_layout.addWidget(w)
        right_col.addWidget(g4)

        # ===== 底部按钮条（消除底部空白）=====
        footer = QHBoxLayout(); footer.setContentsMargins(0,0,0,0)
        footer.addStretch(1)
        self.next_btn = QPushButton("Next"); self.next_btn.setObjectName("nextBtn")
        self.next_btn.setFixedHeight(38)
        self.next_btn.clicked.connect(self.on_next_clicked)
        footer.addWidget(self.next_btn, 0)
        root.addLayout(footer)

    # ---- interactions ----
    def toggle_edge_options(self, text):
        is_edge = (text == "EDGE")
        # 型号仅 EDGE 显示，解决方案 (DC/AC) 始终显示
        self.edge_model_row.setVisible(is_edge)
        self.edge_solution_row.setVisible(True)

    def fill_temperature(self):
        """使用 Open-Meteo Archive API 计算多年期“年极值的年均”：
            Max = mean(每年的 [当年每日最高气温的极大值])
            Min = mean(每年的 [当年每日最低气温的极小值])
            单位：°C"""
        place = self.location.text().strip()
        if not place:
            return
        try:
            # 1) 地名 -> 经纬度
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={place}&count=1"
            geo = requests.get(geo_url, timeout=12).json()
            if "results" not in geo or not geo["results"]:
                self.max_temp.setText("N/A"); self.min_temp.setText("N/A"); return
            lat = geo["results"][0]["latitude"]
            lon = geo["results"][0]["longitude"]

            # 2) 设定统计年限：最近20个完整年份（避免当年未完造成偏差）
            current_year = date.today().year
            start_year = current_year - 20
            start_date = f"{start_year}-01-01"
            end_date   = f"{current_year-1}-12-31"

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
                self.max_temp.setText("N/A"); self.min_temp.setText("N/A"); return

            times = data["daily"]["time"]
            tmax  = data["daily"]["temperature_2m_max"]
            tmin  = data["daily"]["temperature_2m_min"]

            # 4) 按年份聚合：每年 max(tmax) / min(tmin)
            yearly_maxes = {}
            yearly_mins  = {}
            for d, hi, lo in zip(times, tmax, tmin):
                if hi is None or lo is None:  # 跳过缺测
                    continue
                y = int(d[:4])
                # 年度极大（那年最热那天的最高温）
                if y not in yearly_maxes or hi > yearly_maxes[y]:
                    yearly_maxes[y] = hi
                # 年度极小（那年最冷那天的最低温）
                if y not in yearly_mins or lo < yearly_mins[y]:
                    yearly_mins[y] = lo

            if not yearly_maxes or not yearly_mins:
                self.max_temp.setText("N/A"); self.min_temp.setText("N/A"); return

            # 5) 多年期均值
            mean_annual_max = round(sum(yearly_maxes.values()) / len(yearly_maxes), 2)
            mean_annual_min = round(sum(yearly_mins.values()) / len(yearly_mins), 2)

            self.max_temp.setText(str(mean_annual_max))
            self.min_temp.setText(str(mean_annual_min))

            tip = (f"Aggregated over {min(yearly_maxes)}–{max(yearly_maxes)} (years): "
                "Max = mean of each year's hottest-day high; "
                "Min = mean of each year's coldest-day low. Unit: °C")
            self.max_temp.setToolTip(tip)
            self.min_temp.setToolTip(tip)

        except Exception as e:
            self.max_temp.setText("Err"); self.min_temp.setText("Err")
            print("API error:", e)

    def _to_kw(self, value, unit):
        if value == "": return None
        v = float(value)
        return v * 1000 if unit == "MW" else v  # 统一到 kW

    def _to_kwh(self, value, unit):
        if value == "": return None
        v = float(value)
        return v * 1000 if unit == "MWh" else v  # 统一到 kWh
    
    def _format_c_rate(self, c_rate):
        """智能格式化 C-rate，避免不必要的尾随零，最多保留3位小数"""
        # 处理接近整数的情况
        if abs(c_rate - round(c_rate)) < 1e-6:
            return f"{int(round(c_rate))}C"
        
        # 处理常见分数，保留必要的小数位，但最多3位
        # 先尝试用不同精度格式化，然后去除尾随零
        for decimals in [1, 2, 3]:
            formatted = f"{c_rate:.{decimals}f}"
            # 去除尾随零和小数点
            formatted = formatted.rstrip('0').rstrip('.')
            
            # 检查格式化后的值是否足够接近原值
            try:
                formatted_value = float(formatted)
                if abs(formatted_value - c_rate) < 1e-6:
                    return f"{formatted}C"
            except ValueError:
                continue
        
        # 如果上述方法都不行，强制保留最多3位小数
        formatted = f"{c_rate:.3f}".rstrip('0').rstrip('.')
        return f"{formatted}C"
    
    def calculate_discharge_rate(self):
        """根据 Power 和 Capacity 自动计算 C-rate"""
        try:
            power_text = self.power.text().strip()
            capacity_text = self.capacity.text().strip()
            
            if not power_text or not capacity_text:
                self.discharge.setText("")
                return
            
            # 获取统一单位的值（kW 和 kWh）
            power_kw = self._to_kw(power_text, self.power_unit.currentText())
            capacity_kwh = self._to_kwh(capacity_text, self.capacity_unit.currentText())
            
            if power_kw is None or capacity_kwh is None or capacity_kwh == 0:
                self.discharge.setText("")
                return
            
            # 计算 C-rate: Power (kW) / Capacity (kWh) = C-rate
            c_rate = power_kw / capacity_kwh
            
            # 智能格式化显示，避免不必要的尾随零
            c_rate_str = self._format_c_rate(c_rate)
            
            self.discharge.setText(c_rate_str)
            
        except (ValueError, ZeroDivisionError):
            self.discharge.setText("")
    
    def _validate_and_collect(self):
        # All fields are optional now — skip required-field enforcement.
        # 数字可选填；若填了就转成统一单位（kW / kWh）
        try:
            power_kw = self._to_kw(self.power.text().strip(), self.power_unit.currentText())
            capacity_kwh = self._to_kwh(self.capacity.text().strip(), self.capacity_unit.currentText())
        except ValueError:
            QMessageBox.warning(self, "Invalid number",
                                "Please enter valid numbers for Power/Capacity.")
            return None

        data = {
            "customer": self.customer.text().strip(),
            "project": self.project.text().strip(),
            "usecase": self.usecase.text().strip(),
            "life_stage": self.life.text().strip(),
            "power_kw": power_kw,                 # 统一到 kW
            "capacity_kwh": capacity_kwh,         # 统一到 kWh
            "location": self.location.text().strip(),
            "tmax_c": self.max_temp.text().strip(),
            "tmin_c": self.min_temp.text().strip(),
            "cycle": self.cycle_num.text().strip(),
            "discharge": self.discharge.text().strip(),  # 现在是文本框，不是 combo box
            "product": self.product.currentText(),
            "edge_model": self.edge_model.currentText(),
            "edge_solution": self.edge_solution.currentText(),
            "delivery": self.delivery.text().strip(),
            "cod": self.cod.text().strip(),
            "augmentation": self.augmetation.currentText(),
            # 原始展示单位（保留给展示/导出）
            "power_unit_display": self.power_unit.currentText(),
            "capacity_unit_display": self.capacity_unit.currentText(),
        }
        return data

    def on_next_clicked(self):
        data = self._validate_and_collect()
        if data is None:
            return

        # 1) 更新 Interface 页数据到内存状态（不立即保存到文件）
        self.state["interface"] = data

        # 2) 打开 Degradation 窗口并把 state / save_path 传过去
        try:
            from Degradation import DegradationSelector
            if getattr(self, "deg_win", None) is None:
                self.deg_win = DegradationSelector(state=self.state, save_path=self.save_path)

            # 设置 Product（现在是只读文本框）
            prod = data.get("product", "").strip()
            if prod:
                self.deg_win.txt_product.setText(prod)
                # 手动触发产品变更以加载对应的曲线数据
                self.deg_win.on_product_change()

            self.deg_win.show(); self.deg_win.raise_(); self.deg_win.activateWindow()
            self.hide()
        except Exception as e:
            QMessageBox.critical(self, "Open Degradation", f"Failed to open Degradation window:\n{e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))  # 更大的全局字体
    win = BESSApp()
    win.show()
    sys.exit(app.exec_())