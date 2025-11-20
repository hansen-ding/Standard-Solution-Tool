# Calculator.py
# Cleaned & structured version of the Calculator page for the Sizing Tool.

import json
import os
import sys
from typing import Dict, Any, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDoubleValidator, QFont, QColor
from PyQt5.QtWidgets import (
    QApplication,
    QDesktopWidget,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
try:
    if os.path.dirname(__file__) not in sys.path:
        sys.path.append(os.path.dirname(__file__))
    from Algorithm import compute_and_persist_system_outputs
except Exception:
    compute_and_persist_system_outputs = None

# Import Output page for navigation
try:
    from Output import OutputPage
except Exception:
    OutputPage = None

# ------------------------------
# Theme & Global Styles (restored)
# ------------------------------
THEME_RGB = (234, 85, 32)

APP_STYLESHEET = f"""
    QWidget {{ background:#F7F7F7; }}
    QLabel  {{ font-size:12px; color:#333; }}
    QPushButton {{
        font-size:14px;
        height:38px;
        min-width:40px;
        padding: 0 18px;
        background:#FFFFFF;
        border:1px solid #C9CCCF;
        border-radius:8px;
    }}
    QPushButton:hover {{ border-color:#AEB2B6; }}
    QPushButton:pressed {{ background:#F3F4F6; }}
    QLineEdit {{
        font-size:14px; height:24px; background:#fff;
        border:1px solid #C9CCCF; border-radius:6px; padding:0 14px;
    }}
    QGroupBox {{
        font-weight:600;
        border: 2px solid rgba({THEME_RGB[0]}, {THEME_RGB[1]}, {THEME_RGB[2]}, 0.7);
        border-radius:10px; margin-top:12px; padding:10px 12px 12px 12px;
        background:#fff;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin; left:10px; padding:0 6px;
    }}
    QScrollBar:horizontal, QScrollBar:vertical {{
        background:transparent; height:10px; width:10px; margin:0;
    }}
    QScrollBar::handle {{ background:rgba(0,0,0,0.18); border-radius:5px; }}
    QScrollBar::handle:hover {{ background:rgba(0,0,0,0.28); }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height:0; width:0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""

def themed_group(title: str) -> QGroupBox:
    box = QGroupBox(title)
    box.setStyleSheet(
        f"""
        QGroupBox {{
            font-weight:600;
            border: 2px solid rgba({THEME_RGB[0]}, {THEME_RGB[1]}, {THEME_RGB[2]}, 0.7);
            border-radius:10px; margin-top:12px; padding:10px 12px 12px 12px;
            background:#fff;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin; left:10px; padding:0 6px;
        }}
        """
    )
    return box

def make_small_kv_table(labels: list[str]) -> QTableWidget:
    """
    Make a compact 6x2 'key-value' table:
    - Left column = label text (left aligned)
    - Right column = value placeholder '-' (center)
    - Smaller font and row height
    """
    rows = len(labels)
    cols = 2
    tbl = QTableWidget(rows, cols)
    tbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    # Smaller font
    f = tbl.font()
    f.setPointSize(8)  # 比默认更小
    tbl.setFont(f)

    # Compact rows
    row_height = 20
    for r in range(rows):
        tbl.setRowHeight(r, row_height)

    # Header tweaks
    tbl.verticalHeader().setVisible(False)
    tbl.horizontalHeader().setVisible(False)  # 简洁的KV样式不显示表头

    # Column sizing（左宽右窄）
    tbl.setColumnWidth(0, 230)

    # Fill cells
    for r, text in enumerate(labels):
        key_item = QTableWidgetItem(text)
        key_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        tbl.setItem(r, 0, key_item)

        val_item = QTableWidgetItem("-")
        val_item.setTextAlignment(Qt.AlignCenter)
        tbl.setItem(r, 1, val_item)

    tbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    tbl.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    tbl.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    return tbl

def fit_table_height(tbl, rows:int, top_extra:int=0, bottom_extra:int=8):
    """根据字体 & 行数，计算并固定 QTableWidget 的高度，去掉多余空白。"""
    fm = QFontMetrics(tbl.font())
    # 行高：留一点上下内边距
    row_h = max(22, fm.height() + 10)
    tbl.verticalHeader().setDefaultSectionSize(row_h)

    # 表头高度（如果隐藏则为 0）
    hh = tbl.horizontalHeader().height() if tbl.horizontalHeader().isVisible() else 0
    # 横向滚动条高度（如果有）
    sb_h = tbl.horizontalScrollBar().sizeHint().height() if tbl.horizontalScrollBarPolicy() != Qt.ScrollBarAlwaysOff else 0

    total = top_extra + hh + row_h * rows + 2 * tbl.frameWidth() + sb_h + bottom_extra
    tbl.setFixedHeight(total)

def make_graph(title: str = "Degradation Curve") -> FigureCanvas:
    """Create a simple line plot canvas."""
    fig = Figure(figsize=(5.4, 3.9), tight_layout=True)
    canvas = FigureCanvas(fig)
    canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    ax = fig.add_subplot(111)
    ax.plot([0, 1, 2, 3, 4], [100, 97, 94, 91, 89], marker="o")
    ax.set_xlabel("Year")
    ax.set_ylabel("SOH (%)")
    ax.set_title(title)
    return canvas


def divider() -> QFrame:
    """A thin horizontal divider line."""
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Plain)
    line.setStyleSheet("color: rgba(0,0,0,0.08);")
    line.setFixedHeight(1)
    return line


def labeled_row(text: str, widget: QWidget, *, label_min_width: int = 330) -> QWidget:
    """Return a row with a label and a single widget."""
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    lab = QLabel(text)
    lab.setStyleSheet("font-size:16px;")
    lab.setMinimumWidth(label_min_width)
    h.addWidget(lab)
    h.addWidget(widget, 1)
    return w


# ------------------------------
# Main UI
# ------------------------------
class CalculatorPage(QWidget):
    """Calculator page of the Sizing Tool."""

    # Emit when the user clicks Next; parent can switch to the next page
    nextRequested = pyqtSignal(dict)

    def __init__(self, state: Optional[Dict[str, Any]] = None, save_path: Optional[str] = None) -> None:
        super().__init__()
        self.state: Dict[str, Any] = state or {}
        self.save_path = save_path or os.path.join(os.path.dirname(__file__), "sizing_state.json")

        self.setWindowTitle("Sizing Tool · Calculator")
        self.setMinimumSize(1000, 800)
        self.resize(1000, 800)
        self.setStyleSheet(APP_STYLESHEET)
        self.center()

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Header
        title = QLabel("Calculator")
        title.setAlignment(Qt.AlignHCenter)
        title.setStyleSheet(
            f"color: rgb({THEME_RGB[0]}, {THEME_RGB[1]}, {THEME_RGB[2]}); font-size:20px; font-weight:700;"
        )
        subtitle = QLabel("Proposals · Yearly Results · Degradation Graphs")
        subtitle.setAlignment(Qt.AlignHCenter)
        subtitle.setStyleSheet("color:#5f5f5f; font-size:14px;")
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addWidget(divider())

        # Scrollable content
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        root.addWidget(scroll, 1)

        content = QWidget()
        scroll.setWidget(content)
        grid = QGridLayout(content)
        grid.setSpacing(12)

        # Inputs go inside the content area (not in header)
        # Use a grid layout for vertical alignment
        input_grid = QGridLayout()
        input_grid.setSpacing(12)

        # Keep attribute names so save/load logic continues to work
        self.input_bol_cabinets = QLineEdit()
        self.input_bol_cabinets.setValidator(QDoubleValidator())
        label_bol_container = QLabel("Proposed BOL Container/Cabinet #:")
        label_bol_container.setBuddy(self.input_bol_cabinets)
        self.input_bol_cabinets.setFixedWidth(80)
        input_grid.addWidget(label_bol_container, 0, 0)
        input_grid.addWidget(self.input_bol_cabinets, 0, 1)
        # Full pipeline recompute when base cabinets change
        try:
            self.input_bol_cabinets.editingFinished.connect(self._on_bol_changed)
        except Exception:
            pass

        # Calculate button next to container input (flatter)
        self.calc_btn = QPushButton("Calculate")
        self.calc_btn.setObjectName("calcBtn")
        self.calc_btn.setFixedHeight(28)
        self.calc_btn.clicked.connect(self.on_calculate_clicked)
        input_grid.addWidget(self.calc_btn, 0, 2)

        # Confluence input (visible by default per user request)
        self.input_bol_confluence = QLineEdit()
        self.input_bol_confluence.setValidator(QDoubleValidator())
        self.label_bol_confluence = QLabel("Proposed BOL Confluence Cabinet #:")
        self.label_bol_confluence.setBuddy(self.input_bol_confluence)
        self.input_bol_confluence.setFixedWidth(80)
        input_grid.addWidget(self.label_bol_confluence, 1, 0)
        input_grid.addWidget(self.input_bol_confluence, 1, 1)

        # Right side stretch to absorb remaining space
        input_grid.setColumnStretch(3, 1)

        # Place the input_grid into the main grid layout (span a couple columns)
        grid.addLayout(input_grid, 0, 0, 1, 4)

        # -------- System Output (COMPLETE) --------
        g3 = themed_group("System Output")
        l3 = QVBoxLayout(g3)
        l3.setContentsMargins(8, 8, 8, 8)  # 外框往里缩一点

        # 6×2 KV 表：左列标签，右列数值
        sys_labels = [
            "Product Nameplate Capacity",
            "System Nameplate Capacity",
            "System DC Usable Capacity",
            "System AC Usable Capacity",
            "System Rated DC Power",
            "System Rated AC Power",
        ]
        self.tbl_sys_output = make_small_kv_table(sys_labels)

        # 列宽：左列稍微变窄，右列保持不变（消除右侧空白）
        self.tbl_sys_output.setColumnWidth(0, 200)
        self.tbl_sys_output.setColumnWidth(1, 120)

        # 固定高度：按行数吃掉多余空白（减少底部额外间距）
        fit_table_height(self.tbl_sys_output, rows=len(sys_labels), bottom_extra=0)

        # 让表格宽度正好等于两列之和，避免右侧出现填充空白
        total_cols_w = self.tbl_sys_output.columnWidth(0) + self.tbl_sys_output.columnWidth(1)
        table_w = total_cols_w + 2 * self.tbl_sys_output.frameWidth()
        self.tbl_sys_output.setFixedWidth(table_w)

        # 把表放进一个固定尺寸的滚动区（看起来像不滚动，但能限制宽度/高度）
        sys_scroll = QScrollArea()
        sys_scroll.setWidgetResizable(True)
        sys_scroll.setFrameShape(QFrame.NoFrame)
        sys_scroll.setWidget(self.tbl_sys_output)
        sys_scroll.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 滚动区宽度与表格一致，彻底消除右侧多余空白
        sys_scroll.setFixedWidth(table_w)
        sys_scroll.setFixedHeight(self.tbl_sys_output.height())

        # 左对齐摆放；整个 group 垂直方向固定高度
        row_sys = QHBoxLayout()
        row_sys.setContentsMargins(0, 0, 0, 0)
        row_sys.addWidget(sys_scroll, 0, Qt.AlignLeft)
        l3.addLayout(row_sys)

        # 固定宽度/高度，避免被父布局拉伸出空白区域
        g3.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        grid.addWidget(g3, 1, 0, 1, 2)

        # Augmentation Plan
        g4 = themed_group("Augmentation Plan")
        l4 = QVBoxLayout(g4)

        rows, cols = 22, 3
        self.tbl_aug = QTableWidget(rows, cols)
        # 隐藏行号（前面的序号列）
        self.tbl_aug.verticalHeader().setVisible(False)

        # 字体和 System Output 一致
        f = self.tbl_aug.font()
        f.setPointSize(8)
        self.tbl_aug.setFont(f)

        headers = ["Year", "Qty of Aug", "Aug Cap"]
        self.tbl_aug.setHorizontalHeaderLabels(headers)

        # 表头字体
        hf = self.tbl_aug.horizontalHeader().font()
        hf.setPointSize(8)
        self.tbl_aug.horizontalHeader().setFont(hf)

        # 初始化 Aug 表：Year 列（不可编辑），Qty（可编辑，Total 行除外），Aug Cap（不可编辑）
        self.tbl_aug.blockSignals(True)
        for r in range(rows):
            # Year 列：0–20 + Total（最后一行）
            if r < 21:
                year_item = QTableWidgetItem(str(r))
            else:
                year_item = QTableWidgetItem("Total")
            year_item.setTextAlignment(Qt.AlignCenter)
            year_item.setFlags(year_item.flags() & ~Qt.ItemIsEditable)
            self.tbl_aug.setItem(r, 0, year_item)

            # Qty 列
            if r == rows - 1:  # Total 行：不可编辑
                qty_item = QTableWidgetItem("")
                qty_item.setFlags(qty_item.flags() & ~Qt.ItemIsEditable)
            else:
                qty_item = QTableWidgetItem("")  # 留空便于输入
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.tbl_aug.setItem(r, 1, qty_item)

            # Aug Cap 列：不可编辑，稍后按 Qty*ProductCap 计算
            cap_item = QTableWidgetItem("-")
            cap_item.setTextAlignment(Qt.AlignCenter)
            cap_item.setFlags(cap_item.flags() & ~Qt.ItemIsEditable)
            self.tbl_aug.setItem(r, 2, cap_item)
        self.tbl_aug.blockSignals(False)

        # 当 Qty 变化时自动重算 Aug Cap 与合计
        self.tbl_aug.itemChanged.connect(self.on_aug_cell_changed)

        # 行高紧凑
        row_height = 20
        for r in range(rows):
            self.tbl_aug.setRowHeight(r, row_height)

        # 把表格放进 ScrollArea
        aug_scroll = QScrollArea()
        aug_scroll.setWidgetResizable(True)
        aug_scroll.setWidget(self.tbl_aug)
        aug_scroll.setFixedHeight(260)  # 👉 控制显示高度，剩下部分用滚动条
        aug_scroll.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        aug_scroll.setMinimumWidth(self.tbl_aug.sizeHint().width() + 60)

        l4.addWidget(aug_scroll)
        grid.addWidget(g4, 2, 0, 1, 2)
        # Yearly Result (main) table
        g5 = themed_group("Yearly Result")
        l5 = QVBoxLayout(g5)

        rows, cols = 21, 8
        self.tbl_main = QTableWidget(rows, cols)
        self.tbl_main.verticalHeader().setVisible(False)
        self.tbl_main.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        f = self.tbl_main.font(); f.setPointSize(8); self.tbl_main.setFont(f)
        headers = [
            "End of Year",
            "Containers in Service",
            "SOH % (% of Original Capacity)",
            "kWh DC Nameplate",
            "kWh DC Usable",
            "kWh AC Usable @ MVT",
            "Min. Required (kWh)",
            "∆ (kWh)"
        ]
        self.tbl_main.setHorizontalHeaderLabels(headers)
        hf = self.tbl_main.horizontalHeader().font(); hf.setPointSize(8); self.tbl_main.horizontalHeader().setFont(hf)
        for r in range(1, rows):
            for c in range(cols):
                it = QTableWidgetItem("-"); it.setTextAlignment(Qt.AlignCenter); self.tbl_main.setItem(r, c, it)
        for r in range(rows):
            it = QTableWidgetItem(str(r)); it.setTextAlignment(Qt.AlignCenter); it.setFlags(it.flags() & ~Qt.ItemIsEditable); self.tbl_main.setItem(r, 0, it)
        for r in range(rows):
            self.tbl_main.setRowHeight(r, 20)
        self.tbl_main.setColumnWidth(0, 70)
        self.tbl_main.setColumnWidth(1, 120)
        self.tbl_main.setColumnWidth(2, 180)
        self.tbl_main.setColumnWidth(3, 110)
        self.tbl_main.setColumnWidth(4, 100)
        self.tbl_main.setColumnWidth(5, 140)
        self.tbl_main.setColumnWidth(6, 120)
        self.tbl_main.setColumnWidth(7, 100)
        l5.addWidget(self.tbl_main)
        grid.addWidget(g5, 1, 2, 2, 10)

        # Prepare hidden graph section
        self.usable_graph_group = themed_group("Usable Capacity")
        # Override padding just for this group to shrink border-to-canvas gap even more
        self.usable_graph_group.setStyleSheet(
            f"QGroupBox {{ border: 2px solid rgba({THEME_RGB[0]}, {THEME_RGB[1]}, {THEME_RGB[2]}, 0.7); border-radius:10px; margin-top:12px; padding:2px 3px 3px 3px; background:#fff; }}"
            "QGroupBox::title { subcontrol-origin: margin; left:6px; padding:0 2px; }"
        )
        g6_layout = QVBoxLayout(self.usable_graph_group)
        # Even tighter inner layout margins
        g6_layout.setContentsMargins(1, 1, 1, 1)
        g6_layout.setSpacing(0)
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as _FigureCanvas  # local import
        from matplotlib.figure import Figure as _Figure
        self.usable_fig = _Figure(figsize=(4.0, 3.2), tight_layout=True)
        self.usable_canvas = _FigureCanvas(self.usable_fig)
        self.usable_ax = self.usable_fig.add_subplot(111)
        # Smaller fonts for axis labels & title (user request)
        self.usable_ax.set_xlabel("End of Year", fontsize=9)
        self.usable_ax.set_ylabel("Usable Capacity (kWh)", fontsize=9)
        self.usable_ax.set_title("Usable Capacity", fontsize=10)
        self.usable_ax.tick_params(axis='both', labelsize=8)
        # Maximize subplot area with minimal padding
        try:
            self.usable_fig.subplots_adjust(left=0.10, right=0.99, top=0.92, bottom=0.12)
        except Exception:
            pass
        g6_layout.addWidget(self.usable_canvas)
        self.usable_graph_group.hide()
        self.graph_shown = False
        for col, stretch in enumerate([1,1,1,1,3,3,3,3,3,3]):
            grid.setColumnStretch(col, stretch)
        self._grid = grid; self._g5 = g5
        grid.setRowStretch(1,1); grid.setRowStretch(2,2)

        # Footer
        root.addWidget(divider())
        footer = QHBoxLayout()
        footer.addStretch()
        # Back button: return to Degradation page
        self.back_btn = QPushButton("Back")
        self.back_btn.setObjectName("backBtn")
        self.back_btn.clicked.connect(self.on_back_clicked)
        footer.addWidget(self.back_btn)
        # Next button (existing)
        self.next_btn = QPushButton("Next")
        self.next_btn.setObjectName("nextBtn")
        self.next_btn.clicked.connect(self.on_next_clicked)
        footer.addWidget(self.next_btn)
        root.addLayout(footer)

        # Try to load state and populate inputs if present
        self._load_state_if_exists()
        # Populate System Output table if state already has results
        try:
            self._refresh_system_output_table()
        except Exception:
            pass

        # Initial fill for Yearly Result containers
        try:
            self._recompute_containers_via_algo()
        except Exception:
            pass
        # Initial fill for SOH %
        try:
            self._recompute_soh_via_algo()
        except Exception:
            pass
        # Initial fill for kWh DC Nameplate
        try:
            self._recompute_kwh_dc_nameplate_via_algo()
        except Exception:
            pass
        # Initial fill for kWh DC Usable
        try:
            self._recompute_kwh_dc_usable_via_algo()
        except Exception:
            pass
        # Initial fill for kWh AC Usable @ MVT
        try:
            self._recompute_kwh_ac_usable_via_algo()
        except Exception:
            pass
        # Initial fill for Min. Required (kWh)
        try:
            self._refresh_min_required()
        except Exception:
            pass
        # Initial fill for Δ (kWh)
        try:
            self._recompute_delta_via_algo()
        except Exception:
            pass
        # Initial usable capacity graph (if data already present)
        try:
            self._update_usable_capacity_graph()
        except Exception:
            pass

    def _show_usable_graph_section(self):
        """Add graph section to the grid layout and resize window (only first time)."""
        try:
            if getattr(self, 'graph_shown', False):
                return
            grid = getattr(self, '_grid', None)
            g5 = getattr(self, '_g5', None)
            if grid is None or g5 is None:
                return
            # Remove current g5 placement (full width)
            try:
                # brute-force removal
                for i in reversed(range(grid.count())):
                    item = grid.itemAt(i)
                    w = item.widget()
                    if w is g5:
                        grid.removeWidget(w)
                        break
            except Exception:
                pass
            # Re-add g5 with reduced span
            grid.addWidget(g5, 1, 2, 2, 6)
            # Add graph group to the right
            grid.addWidget(self.usable_graph_group, 1, 8, 2, 4)
            # Update column stretch for 12 columns configuration
            for col, stretch in enumerate([1,1,1,1,3,3,3,3,3,3,3,3]):
                grid.setColumnStretch(col, stretch)
            self.usable_graph_group.show()
            self.graph_shown = True
            # Resize window to requested 1700x800
            self.resize(1700, 800)
        except Exception:
            pass

    # --------- Internal Utilities ---------
    def _apply_double_validator(self, line_edit: QLineEdit, bottom: float = 0.0, top: float = 1e9, decimals: int = 2) -> None:
        """Attach a numeric validator to a QLineEdit."""
        validator = QDoubleValidator(bottom, top, decimals)
        validator.setNotation(QDoubleValidator.StandardNotation)
        line_edit.setValidator(validator)

    def _load_state_if_exists(self) -> None:
        """Load state from disk if save file exists; populate inputs."""
        if not os.path.isfile(self.save_path):
            return
        try:
            with open(self.save_path, "r", encoding="utf-8") as f:
                disk_state = json.load(f)
                # Merge into current state (disk wins on conflicts)
                self.state.update(disk_state or {})
        except Exception as e:
            # Keep UI usable even if read fails
            QMessageBox.warning(self, "Load Warning", f"Failed to load state file:\n{e}")
            return

        calc_inputs = (
            self.state.get("calculator", {}).get("inputs", {})
            if isinstance(self.state.get("calculator"), dict)
            else {}
        )
        self.input_bol_cabinets.setText(str(calc_inputs.get("bol_cabinets", "")))
        self.input_bol_confluence.setText(str(calc_inputs.get("bol_confluence", "")))

        # Load augmentation plan data if available
        try:
            calc_data = self.state.get("calculator", {})
            aug_plan = calc_data.get("augmentation_plan", [])
            if isinstance(aug_plan, list) and hasattr(self, 'tbl_aug'):
                # Populate augmentation table with saved data
                self.tbl_aug.blockSignals(True)
                try:
                    rows = self.tbl_aug.rowCount()
                    for r in range(min(len(aug_plan), rows - 1)):  # Exclude Total row
                        qty = aug_plan[r] if r < len(aug_plan) else 0.0
                        item = QTableWidgetItem(str(qty) if qty != 0 else "")
                        item.setTextAlignment(Qt.AlignCenter)
                        self.tbl_aug.setItem(r, 1, item)  # Column 1 is "Qty of Aug"
                finally:
                    self.tbl_aug.blockSignals(False)
                
                # Recompute Aug Cap column after loading data
                self._recompute_aug_cap()
        except Exception as e:
            print(f"[Calculator] Error loading augmentation data: {e}")

        # Determine product selection from state (may be stored at top-level 'product' or similar).
        product = self.state.get("product") or (self.state.get("site", {}).get("product") if isinstance(self.state.get("site"), dict) else None)
        # Delegate to public setter so other modules can call it at runtime
        try:
            self.set_product(product)
        except Exception:
            pass

    def _refresh_system_output_table(self, outputs: Optional[Dict[str, Any]] = None) -> None:
        """Fill the System Output KV table from provided outputs or from sizing_state.json.

        Expects a dict like state['system_output'] with keys:
        - product_nameplate_capacity
        - system_nameplate_capacity
        - system_dc_usable_capacity
        - system_ac_usable_capacity
        - system_rated_dc_power
        - system_rated_ac_power
        Each key maps to { value, unit }.
        """
        if outputs is None:
            # Load from disk if not provided
            try:
                if os.path.isfile(self.save_path):
                    with open(self.save_path, "r", encoding="utf-8") as f:
                        disk = json.load(f) or {}
                        outputs = (disk.get("system_output") or {}) if isinstance(disk, dict) else {}
            except Exception:
                outputs = {}

        def fmt(obj: Any) -> str:
            try:
                if not isinstance(obj, dict):
                    return "-"
                v = obj.get("value")
                u = obj.get("unit") or ""
                if v is None or v == "":
                    return "-"
                return f"{float(v):.2f} {u}".strip()
            except Exception:
                return "-"

        keys_in_order = [
            "product_nameplate_capacity",
            "system_nameplate_capacity",
            "system_dc_usable_capacity",
            "system_ac_usable_capacity",
            "system_rated_dc_power",
            "system_rated_ac_power",
        ]

        for row, k in enumerate(keys_in_order):
            try:
                val = fmt(outputs.get(k) if isinstance(outputs, dict) else None)
                cell = self.tbl_sys_output.item(row, 1)
                if cell is None:
                    cell = QTableWidgetItem("-")
                    cell.setTextAlignment(Qt.AlignCenter)
                    self.tbl_sys_output.setItem(row, 1, cell)
                cell.setText(val)
            except Exception:
                pass

        # 刷新 Augmentation Plan 里的 Aug Cap（可能依赖 product_nameplate_capacity）
        try:
            self._recompute_aug_cap()
        except Exception:
            pass

    def set_product(self, product: Optional[str]) -> None:
        """Set current product and toggle visibility of product-specific inputs.

        Other modules (e.g., interface.py) can call this after product selection to
        immediately show/hide the confluence input.
        """
        # Per user request, Confluence input should always be visible.
        try:
            self.label_bol_confluence.setVisible(True)
            self.input_bol_confluence.setVisible(True)
        except Exception:
            pass

    # --------- Event Handlers ---------
    def on_next_clicked(self) -> None:
        """Persist inputs to json and navigate to Output page."""
        self.state.setdefault("calculator", {})
        self.state["calculator"]["inputs"] = {
            "bol_cabinets": self.input_bol_cabinets.text().strip(),
            "bol_confluence": self.input_bol_confluence.text().strip(),
        }

        # Also persist Aug totals and plan into state before saving
        try:
            self._update_aug_totals_in_state()
            self._save_augmentation_plan_to_state()
        except Exception:
            pass

        # Persist current Yearly Result table (what user sees) into state
        try:
            self._persist_yearly_result_from_table()
        except Exception as e:
            print(f"[Calculator] Warning: failed to capture yearly result table: {e}")

        # Save to disk
        try:
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Save Error", str(e))
            return
        
        # Navigate to Output page
        try:
            if OutputPage is not None:
                # Create Output page instance
                self.output_page = OutputPage(state=self.state, save_path=self.save_path)
                
                # Connect back signal to return to this calculator page
                self.output_page.backRequested.connect(self.on_output_back_requested)
                
                # Hide current calculator page and show output page
                self.hide()
                self.output_page.show()
                
                print("[Calculator] Navigated to Output page")
            else:
                QMessageBox.warning(self, "Navigation Error", "Output page module not available.")
        except Exception as e:
            QMessageBox.warning(self, "Navigation Error", f"Failed to open Output page: {str(e)}")
            print(f"[Calculator] Error navigating to Output: {e}")

    def _persist_yearly_result_from_table(self) -> None:
        """Read visible Yearly Result table (tbl_main) and write lists into state['calculator']['yearly_result'].

        Column mapping (index -> key):
          0: year (ignored, derived from row)
          1: containers_in_service (int/float)
          2: soh_percent (store as fraction, e.g. 98.36% -> 0.9836)
          3: kwh_dc_nameplate
          4: kwh_dc_usable
          5: kwh_ac_usable
          6: min_required_kwh (new key)
          7: delta_kwh
        Rows: 0..20 (21 rows) expected.
        Cells containing '-' or empty -> skipped (use last valid or 0.0).
        """
        if not hasattr(self, 'tbl_main'):
            return
        rows = self.tbl_main.rowCount()
        if rows <= 0:
            return

        def _num(cell_text: str, *, percent: bool = False) -> Optional[float]:
            if cell_text is None:
                return None
            t = cell_text.strip()
            if not t or t == '-':
                return None
            try:
                if percent:
                    # remove % and convert to fraction
                    if t.endswith('%'):
                        t = t[:-1]
                    return float(t.replace(',', '')) / 100.0
                return float(t.replace(',', ''))
            except Exception:
                return None

        containers_in_service: list[float] = []
        soh_percent: list[float] = []
        kwh_dc_nameplate: list[float] = []
        kwh_dc_usable: list[float] = []
        kwh_ac_usable: list[float] = []
        min_required_kwh: list[float] = []
        delta_kwh: list[float] = []

        last_vals = {
            'c': 0.0,
            'soh': 0.0,
            'dc_np': 0.0,
            'dc_use': 0.0,
            'ac_use': 0.0,
            'min_req': 0.0,
            'delta': 0.0,
        }

        for r in range(rows):
            # year row r corresponds to end-of-year r
            def cell(col: int) -> Optional[str]:
                it = self.tbl_main.item(r, col)
                return it.text() if it else None

            v_c = _num(cell(1))
            if v_c is None:
                v_c = last_vals['c']
            else:
                last_vals['c'] = v_c
            containers_in_service.append(v_c)

            v_soh = _num(cell(2), percent=True)
            if v_soh is None:
                v_soh = last_vals['soh']
            else:
                last_vals['soh'] = v_soh
            soh_percent.append(v_soh)

            v_dc_np = _num(cell(3))
            if v_dc_np is None:
                v_dc_np = last_vals['dc_np']
            else:
                last_vals['dc_np'] = v_dc_np
            kwh_dc_nameplate.append(v_dc_np)

            v_dc_use = _num(cell(4))
            if v_dc_use is None:
                v_dc_use = last_vals['dc_use']
            else:
                last_vals['dc_use'] = v_dc_use
            kwh_dc_usable.append(v_dc_use)

            v_ac_use = _num(cell(5))
            if v_ac_use is None:
                v_ac_use = last_vals['ac_use']
            else:
                last_vals['ac_use'] = v_ac_use
            kwh_ac_usable.append(v_ac_use)

            v_min_req = _num(cell(6))
            if v_min_req is None:
                v_min_req = last_vals['min_req']
            else:
                last_vals['min_req'] = v_min_req
            min_required_kwh.append(v_min_req)

            v_delta = _num(cell(7))
            if v_delta is None:
                v_delta = last_vals['delta']
            else:
                last_vals['delta'] = v_delta
            delta_kwh.append(v_delta)

        self.state.setdefault('calculator', {})
        yr = self.state['calculator'].setdefault('yearly_result', {})
        yr['containers_in_service'] = containers_in_service
        yr['soh_percent'] = soh_percent
        yr['kwh_dc_nameplate'] = kwh_dc_nameplate
        yr['kwh_dc_usable'] = kwh_dc_usable
        yr['kwh_ac_usable'] = kwh_ac_usable
        yr['min_required_kwh'] = min_required_kwh  # new
        yr['delta_kwh'] = delta_kwh

    def on_output_back_requested(self) -> None:
        """Handle back request from Output page - show Calculator page again."""
        try:
            # Hide the output page and show calculator page
            if hasattr(self, 'output_page') and self.output_page:
                self.output_page.hide()
            self.show()
            print("[Calculator] Returned from Output page")
        except Exception as e:
            print(f"[Calculator] Error handling back from Output: {e}")

    def on_calculate_clicked(self) -> None:
        """Calculate button logic:
        1. Save current inputs.
        2. Compute & display System Output (6 numbers).
        3. Compute Yearly Result dependent lists (containers, SOH, kWh columns, delta).
        4. Refresh Yearly Result table columns.
        5. Show / update graph (after first run resize window & reveal graph section).
        """
        try:
            # 1. Persist inputs only
            self._save_inputs_only()

            # 2. System Output first
            outputs = None
            try:
                if compute_and_persist_system_outputs is not None:
                    outputs = compute_and_persist_system_outputs(self.save_path)
            except Exception as e:
                print('[Calculator] system output compute failed:', e)
            # Merge outputs into in-memory state so later writes don't wipe them
            if outputs:
                try:
                    self.state.setdefault('system_output', {}).update(outputs)
                except Exception:
                    pass
            self._refresh_system_output_table(outputs)

            # 3. Yearly result chain (order matters)
            try:
                self._recompute_containers_via_algo()  # containers_in_service
            except Exception as e:
                print('[Calculator] containers compute failed:', e)
            try:
                from Algorithm import compute_and_persist_soh_percent as _algo_soh
                _algo_soh(self.save_path)
            except Exception as e:
                print('[Calculator] SOH compute failed:', e)
            try:
                from Algorithm import compute_and_persist_kwh_dc_nameplate as _algo_np
                _algo_np(self.save_path)
            except Exception as e:
                print('[Calculator] kWh DC Nameplate compute failed:', e)
            try:
                from Algorithm import compute_and_persist_kwh_dc_usable as _algo_dc_use
                _algo_dc_use(self.save_path)
            except Exception as e:
                print('[Calculator] kWh DC Usable compute failed:', e)
            try:
                from Algorithm import compute_and_persist_kwh_ac_usable as _algo_ac_use
                _algo_ac_use(self.save_path)
            except Exception as e:
                print('[Calculator] kWh AC Usable compute failed:', e)
            try:
                from Algorithm import compute_and_persist_delta as _algo_delta
                _algo_delta(self.save_path)
            except Exception as e:
                print('[Calculator] delta compute failed:', e)

            # 4. Refresh Yearly Result columns from state
            try:
                self._refresh_yearly_result_containers()
            except Exception:
                pass
            try:
                self._refresh_yearly_result_energy_columns()
            except Exception:
                pass
            try:
                self._refresh_min_required()
            except Exception:
                pass
            try:
                self._recompute_delta_via_algo()  # fills delta column styling
            except Exception:
                pass
            try:
                self._refresh_yearly_result_soh()
            except Exception:
                pass

            # 5. Graph
            self._show_usable_graph_section()
            self._update_usable_capacity_graph()
        except Exception as e:
            QMessageBox.warning(self, 'Algorithm Error', f'Failed to calculate:\n{e}')

    def on_back_clicked(self) -> None:
        """Attempt to open the Degradation page and hide this window."""
        try:
            # Lazy import to avoid import errors at module import time
            from Degradation import DegradationSelector
            # Create window if not already present
            if getattr(self, "deg_win", None) is None:
                self.deg_win = DegradationSelector(state=self.state, save_path=self.save_path)

            # Show degradation window and hide this one
            self.deg_win.show(); self.deg_win.raise_(); self.deg_win.activateWindow()
            self.hide()
        except Exception as e:
            QMessageBox.critical(self, "Open Degradation", f"Failed to open Degradation window:\n{e}")

    def center(self) -> None:
        """Center the window on the screen containing the mouse cursor or current screen."""
        qr = self.frameGeometry()
        desktop = QDesktopWidget()
        
        # 获取鼠标当前位置所在的屏幕
        cursor_pos = desktop.cursor().pos()
        screen_num = desktop.screenNumber(cursor_pos)
        
        # 如果无法获取屏幕号，使用主屏幕
        if screen_num < 0:
            screen_num = desktop.primaryScreen()
        
        # 获取目标屏幕的可用区域中心点
        cp = desktop.availableGeometry(screen_num).center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def closeEvent(self, event) -> None:
        """Handle window close event - cleanup any child windows."""
        try:
            # Close output page if it exists
            if hasattr(self, 'output_page') and self.output_page:
                self.output_page.close()
        except Exception:
            pass
        event.accept()

    # --------- Augmentation helpers ---------
    def _get_product_nameplate_capacity(self) -> Optional[float]:
        """从 state['system_output'].product_nameplate_capacity 中提取数值。"""
        try:
            # 优先从内存 state 取
            so = (self.state or {}).get("system_output")
            if isinstance(so, dict) and isinstance(so.get("product_nameplate_capacity"), dict):
                v = so["product_nameplate_capacity"].get("value")
                return float(v) if v not in (None, "") else None
            # 其次尝试从磁盘读取
            if os.path.isfile(self.save_path):
                with open(self.save_path, "r", encoding="utf-8") as f:
                    disk = json.load(f) or {}
                    so = disk.get("system_output") if isinstance(disk, dict) else None
                    if isinstance(so, dict) and isinstance(so.get("product_nameplate_capacity"), dict):
                        v = so["product_nameplate_capacity"].get("value")
                        return float(v) if v not in (None, "") else None
        except Exception:
            return None
        return None

    def _get_product_capacity_unit(self) -> str:
        """读取 product_nameplate_capacity 的 unit（kWh/MWh）。失败返回空串。"""
        try:
            so = (self.state or {}).get("system_output")
            if isinstance(so, dict) and isinstance(so.get("product_nameplate_capacity"), dict):
                u = so["product_nameplate_capacity"].get("unit")
                return str(u).strip() if u else ""
            if os.path.isfile(self.save_path):
                with open(self.save_path, "r", encoding="utf-8") as f:
                    disk = json.load(f) or {}
                    so = disk.get("system_output") if isinstance(disk, dict) else None
                    if isinstance(so, dict) and isinstance(so.get("product_nameplate_capacity"), dict):
                        u = so["product_nameplate_capacity"].get("unit")
                        return str(u).strip() if u else ""
        except Exception:
            pass
        return ""

    def _recompute_aug_cap(self) -> None:
        """按公式：Aug Cap = Qty of Aug * product_nameplate_capacity（逐行），并计算 Total。"""
        rows = self.tbl_aug.rowCount()
        if rows == 0:
            return
        cap_per = self._get_product_nameplate_capacity() or 0.0
        unit = self._get_product_capacity_unit()

        total_qty = 0.0
        total_cap = 0.0

        # 暂停信号避免递归
        self.tbl_aug.blockSignals(True)
        try:
            for r in range(rows - 1):  # 最后一行是 Total
                qty_item = self.tbl_aug.item(r, 1)
                cap_item = self.tbl_aug.item(r, 2)
                try:
                    qty_raw = qty_item.text() if qty_item else ""
                    qty = int(round(float(qty_raw))) if (qty_raw is not None and str(qty_raw).strip() != "") else 0
                except Exception:
                    qty = 0
                # 标准化显示为整数
                if qty_item is None:
                    qty_item = QTableWidgetItem()
                    qty_item.setTextAlignment(Qt.AlignCenter)
                    self.tbl_aug.setItem(r, 1, qty_item)
                qty_item.setText(str(qty))
                cap = qty * cap_per
                total_qty += float(qty)
                total_cap += cap
                if cap_item is None:
                    cap_item = QTableWidgetItem()
                    cap_item.setTextAlignment(Qt.AlignCenter)
                    cap_item.setFlags(cap_item.flags() & ~Qt.ItemIsEditable)
                    self.tbl_aug.setItem(r, 2, cap_item)
                cap_item.setText(f"{cap:.2f}{(' ' + unit) if unit else ''}")

            # Total 行
            qty_total_item = self.tbl_aug.item(rows - 1, 1)
            if qty_total_item is None:
                qty_total_item = QTableWidgetItem()
                qty_total_item.setFlags(qty_total_item.flags() & ~Qt.ItemIsEditable)
                qty_total_item.setTextAlignment(Qt.AlignCenter)
                self.tbl_aug.setItem(rows - 1, 1, qty_total_item)
            qty_total_item.setText(str(int(round(total_qty))))

            cap_total_item = self.tbl_aug.item(rows - 1, 2)
            if cap_total_item is None:
                cap_total_item = QTableWidgetItem()
                cap_total_item.setFlags(cap_total_item.flags() & ~Qt.ItemIsEditable)
                cap_total_item.setTextAlignment(Qt.AlignCenter)
                self.tbl_aug.setItem(rows - 1, 2, cap_total_item)
            cap_total_item.setText(f"{total_cap:.2f}{(' ' + unit) if unit else ''}")
        finally:
            self.tbl_aug.blockSignals(False)

        # Update state with latest totals in memory
        try:
            self._update_aug_totals_in_state(total_qty=int(round(total_qty)), total_cap=total_cap)
        except Exception:
            pass

        # Also update Yearly Result's Containers in Service column
        try:
            self._recompute_containers_via_algo()
        except Exception:
            pass

        # After containers change, recompute dependent kWh metrics & refresh table
        try:
            from Algorithm import (
                compute_and_persist_kwh_dc_nameplate as _algo_dc_np,
                compute_and_persist_kwh_dc_usable as _algo_dc_use,
                compute_and_persist_kwh_ac_usable as _algo_ac_use,
            )
            _algo_dc_np(self.save_path)
            _algo_dc_use(self.save_path)
            _algo_ac_use(self.save_path)
        except Exception:
            pass
        # Refresh table energy columns
        try:
            self._refresh_yearly_result_energy_columns()
        except Exception:
            pass
        # Update delta & graph since usable capacity changed
        try:
            self._recompute_delta_via_algo()
        except Exception:
            pass
        try:
            self._update_usable_capacity_graph()
        except Exception:
            pass

    def on_aug_cell_changed(self, item: QTableWidgetItem) -> None:
        """当 Qty of Aug 修改时，重算对应行 Aug Cap 与合计。只有编辑列=1时处理。"""
        try:
            if item.column() != 1:
                return
        except Exception:
            return
        self._recompute_aug_cap()

    def _update_aug_totals_in_state(self, total_qty: Optional[float] = None, total_cap: Optional[float] = None) -> None:
        """Update totals from Augmentation Plan into self.state['calculator']['augmentation_totals'].

        If totals are not provided, read them from the last row of the table.
        Cap cells may include a unit suffix (e.g., "123.45 kWh").
        """
        # Determine totals if not provided
        if total_qty is None or total_cap is None:
            try:
                rows = self.tbl_aug.rowCount()
                q_item = self.tbl_aug.item(rows - 1, 1)
                c_item = self.tbl_aug.item(rows - 1, 2)
                # Qty total: integer string
                tq_text = q_item.text().strip() if q_item and q_item.text() is not None else ""
                tq_text = tq_text.replace(",", "")
                tq_val = float(tq_text.split()[0]) if tq_text else 0.0
                # Cap total: may include unit suffix
                tc_text = c_item.text().strip() if c_item and c_item.text() is not None else ""
                tc_text = tc_text.replace(",", "")
                tc_val = float(tc_text.split()[0]) if tc_text else 0.0
                if total_qty is None:
                    total_qty = tq_val
                if total_cap is None:
                    total_cap = tc_val
            except Exception:
                if total_qty is None:
                    total_qty = 0.0
                if total_cap is None:
                    total_cap = 0.0

        self.state.setdefault("calculator", {})
        self.state["calculator"]["augmentation_totals"] = {
            "total_number_of_aug": int(round(total_qty or 0.0)),
            "total_aug_cap": float(total_cap or 0.0),
        }

    def _save_augmentation_plan_to_state(self) -> None:
        """Save the current augmentation plan (Qty of Aug for each year) to state."""
        try:
            if not hasattr(self, 'tbl_aug'):
                return
            
            rows = self.tbl_aug.rowCount()
            aug_plan = []
            
            # Read Qty of Aug from each row (exclude Total row)
            for r in range(rows - 1):  # Exclude the last row (Total)
                try:
                    item = self.tbl_aug.item(r, 1)  # Column 1 is "Qty of Aug"
                    if item and item.text().strip():
                        qty = float(item.text().strip())
                    else:
                        qty = 0.0
                except Exception:
                    qty = 0.0
                aug_plan.append(qty)
            
            # Ensure we have exactly 21 elements (years 0-20)
            while len(aug_plan) < 21:
                aug_plan.append(0.0)
            
            # Save to state
            self.state.setdefault("calculator", {})
            self.state["calculator"]["augmentation_plan"] = aug_plan[:21]
            
        except Exception as e:
            print(f"[Calculator] Error saving augmentation plan: {e}")

    def _refresh_yearly_result_containers(self) -> None:
        """Read containers_in_service from state (if available) and populate the table column.

        Falls back to local computation only if state does not have data.
        """
        if not hasattr(self, "tbl_main"):
            return
        rows_main = self.tbl_main.rowCount()

        def fmt_num(x: float) -> str:
            try:
                xi = int(round(x))
                return str(xi) if abs(x - xi) < 1e-9 else f"{x:.2f}"
            except Exception:
                return f"{x:.2f}"

        # Prefer state value and do not compute locally
        containers = None
        try:
            if os.path.isfile(self.save_path):
                with open(self.save_path, "r", encoding="utf-8") as f:
                    disk = json.load(f) or {}
                    calc = disk.get("calculator") if isinstance(disk, dict) else None
                    yr = calc.get("yearly_result") if isinstance(calc, dict) else None
                    lst = yr.get("containers_in_service") if isinstance(yr, dict) else None
                    if isinstance(lst, list) and len(lst) > 0:
                        containers = lst
        except Exception:
            containers = None

        # Populate table column 1
        for r in range(rows_main):
            if not containers:
                # If algorithm hasn't produced data yet, show '-'
                val_text = "-"
            else:
                val = containers[r] if r < len(containers) else (containers[-1] if containers else 0.0)
                val_text = fmt_num(float(val))
            cell = self.tbl_main.item(r, 1)
            if cell is None:
                cell = QTableWidgetItem()
                cell.setTextAlignment(Qt.AlignCenter)
                cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                self.tbl_main.setItem(r, 1, cell)
            cell.setText(val_text)

    def _refresh_yearly_result_energy_columns(self) -> None:
        """Refresh kWh DC Nameplate (col 3), kWh DC Usable (col 4), kWh AC Usable (col 5) from state."""
        if not hasattr(self, 'tbl_main'):
            return
        disk = {}
        try:
            if os.path.isfile(self.save_path):
                with open(self.save_path, 'r', encoding='utf-8') as f:
                    disk = json.load(f) or {}
        except Exception:
            return
        calc = disk.get('calculator') if isinstance(disk, dict) else None
        yr = calc.get('yearly_result') if isinstance(calc, dict) else None
        if not isinstance(yr, dict):
            return
        dc_np = yr.get('kwh_dc_nameplate') if isinstance(yr, dict) else None
        dc_use = yr.get('kwh_dc_usable') if isinstance(yr, dict) else None
        ac_use = yr.get('kwh_ac_usable') if isinstance(yr, dict) else None
        rows_main = self.tbl_main.rowCount()
        def _set_col(col_index: int, lst):
            if not (isinstance(lst, list) and len(lst) > 0):
                return
            for r in range(rows_main):
                try:
                    v = lst[r] if r < len(lst) else lst[-1]
                    text = f"{float(v):.2f}"
                except Exception:
                    text = '-'
                cell = self.tbl_main.item(r, col_index)
                if cell is None:
                    cell = QTableWidgetItem()
                    cell.setTextAlignment(Qt.AlignCenter)
                    cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                    self.tbl_main.setItem(r, col_index, cell)
                cell.setText(text)
        _set_col(3, dc_np)
        _set_col(4, dc_use)
        _set_col(5, ac_use)

    def _refresh_yearly_result_soh(self) -> None:
        """Refresh SOH % column (index 2) from state (soh_percent list as fraction)."""
        if not hasattr(self, 'tbl_main'):
            return
        try:
            disk = {}
            if os.path.isfile(self.save_path):
                with open(self.save_path,'r',encoding='utf-8') as f:
                    disk = json.load(f) or {}
            calc = disk.get('calculator') if isinstance(disk, dict) else None
            yr = calc.get('yearly_result') if isinstance(calc, dict) else None
            lst = yr.get('soh_percent') if isinstance(yr, dict) else None
            if not (isinstance(lst, list) and len(lst)>0):
                return
            rows_main = self.tbl_main.rowCount()
            for r in range(rows_main):
                try:
                    v = lst[r] if r < len(lst) else lst[-1]
                    text = f"{float(v)*100:.2f}%"
                except Exception:
                    text = '-'
                cell = self.tbl_main.item(r,2)
                if cell is None:
                    cell = QTableWidgetItem()
                    cell.setTextAlignment(Qt.AlignCenter)
                    cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                    self.tbl_main.setItem(r,2,cell)
                cell.setText(text)
        except Exception:
            pass

    def _recompute_containers_via_algo(self) -> None:
        """Persist Aug plan to state, call algorithm to compute containers, then refresh UI from state."""
        # Push current Aug plan (0..20) into state
        try:
            # Merge latest disk state first to avoid losing previously written sections (e.g. system_output)
            if os.path.isfile(self.save_path):
                try:
                    with open(self.save_path,'r',encoding='utf-8') as f:
                        disk_state = json.load(f) or {}
                    # shallow merge: keep existing self.state keys, overwrite with disk for freshness
                    for k,v in disk_state.items():
                        if k == 'system_output':
                            # ensure nested merge so we don't drop subkeys
                            self.state.setdefault('system_output', {}).update(v if isinstance(v, dict) else {})
                        else:
                            if k not in self.state:
                                self.state[k] = v
                except Exception:
                    pass
            aug = []
            rows_aug = self.tbl_aug.rowCount() if hasattr(self, "tbl_aug") else 0
            for r in range(max(0, rows_aug - 1)):
                it = self.tbl_aug.item(r, 1)
                try:
                    q = float(it.text()) if it and it.text().strip() != "" else 0.0
                except Exception:
                    q = 0.0
                aug.append(q)
            # ensure length 21
            if len(aug) < 21:
                aug += [0.0] * (21 - len(aug))
            self.state.setdefault("calculator", {})
            self.state["calculator"]["augmentation_plan"] = aug[:21]
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        # Call algorithm
        try:
            from Algorithm import compute_and_persist_containers_in_service as _algo_cont
            _algo_cont(self.save_path)
        except Exception:
            pass

        # Refresh UI from state
        try:
            self._refresh_yearly_result_containers()
        except Exception:
            pass

    def _recompute_soh_via_algo(self) -> None:
        """Call algorithm to compute SOH% and refresh the SOH column from state."""
        # Call algorithm to update state
        try:
            from Algorithm import compute_and_persist_soh_percent as _algo_soh
            _algo_soh(self.save_path)
        except Exception:
            pass

    def _recompute_kwh_dc_nameplate_via_algo(self) -> None:
        """Call algorithm to compute kWh DC Nameplate and fill column 3 from state."""
        # Call algorithm
        try:
            from Algorithm import compute_and_persist_kwh_dc_nameplate as _algo_kwh
            _algo_kwh(self.save_path)
        except Exception:
            pass

    def _recompute_kwh_dc_usable_via_algo(self) -> None:
        """Call algorithm to compute kWh DC Usable and fill column 4 from state."""
        try:
            from Algorithm import compute_and_persist_kwh_dc_usable as _algo_kwhu
            _algo_kwhu(self.save_path)
        except Exception:
            pass

    def _recompute_kwh_ac_usable_via_algo(self) -> None:
        """Call algorithm to compute kWh AC Usable and fill column 5 from state."""
        try:
            from Algorithm import compute_and_persist_kwh_ac_usable as _algo_kwh_ac
            _algo_kwh_ac(self.save_path)
        except Exception:
            pass

    def _refresh_min_required(self) -> None:
        """Populate 'Min. Required (kWh)' column (index 6) from sizing_state.json capacity_kwh."""
        try:
            cap = None
            if os.path.isfile(self.save_path):
                with open(self.save_path, 'r', encoding='utf-8') as f:
                    disk = json.load(f) or {}
                    # capacity_kwh may exist at top-level or inside a section (e.g., interface or site)
                    if 'capacity_kwh' in disk:
                        cap = disk.get('capacity_kwh')
                    else:
                        # Try nested common sections
                        for k in ('interface', 'site', 'calculator'):
                            sect = disk.get(k)
                            if isinstance(sect, dict) and 'capacity_kwh' in sect:
                                cap = sect.get('capacity_kwh')
                                break
            try:
                cap_val = float(str(cap).replace(',', '').strip()) if cap not in (None, '') else None
            except Exception:
                cap_val = None
            rows_main = self.tbl_main.rowCount()
            for r in range(rows_main):
                cell = self.tbl_main.item(r, 6)
                if cell is None:
                    cell = QTableWidgetItem()
                    cell.setTextAlignment(Qt.AlignCenter)
                    cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                    self.tbl_main.setItem(r, 6, cell)
                if cap_val is None:
                    cell.setText('-')
                else:
                    cell.setText(f"{cap_val:.2f}")
        except Exception:
            pass

    def _recompute_delta_via_algo(self) -> None:
        """Compute delta via algorithm and populate column 7 (index 7)."""
        try:
            from Algorithm import compute_and_persist_delta as _algo_delta
            _algo_delta(self.save_path)
        except Exception:
            pass

        # Read back
        try:
            disk = {}
            if os.path.isfile(self.save_path):
                with open(self.save_path, 'r', encoding='utf-8') as f:
                    disk = json.load(f) or {}
            calc = disk.get('calculator') if isinstance(disk, dict) else None
            yr = calc.get('yearly_result') if isinstance(calc, dict) else None
            lst = yr.get('delta_kwh') if isinstance(yr, dict) else None
            if isinstance(lst, list) and len(lst) > 0:
                rows_main = self.tbl_main.rowCount()
                for r in range(rows_main):
                    v = lst[r] if r < len(lst) else lst[-1]
                    text = '-' if v is None else f"{float(v):.2f}"
                    cell = self.tbl_main.item(r, 7)
                    if cell is None:
                        cell = QTableWidgetItem()
                        cell.setTextAlignment(Qt.AlignCenter)
                        cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                        self.tbl_main.setItem(r, 7, cell)
                    cell.setText(text)
                    # Highlight negative values
                    try:
                        if text not in ('-', ''):
                            vfloat = float(text)
                            if vfloat < 0:
                                cell.setBackground(QColor(255, 249, 196))  # light yellow
                            else:
                                cell.setBackground(QColor(255, 255, 255))  # reset to white
                    except Exception:
                        pass
        except Exception:
            pass

    # --------- Graph update ---------
    def _update_usable_capacity_graph(self) -> None:
        """Render usable capacity curve (years 1..20) with shaded area.

        Chooses DC or AC series based on edge_solution (default DC). Shows placeholder if data missing.
        """
        if not hasattr(self, 'usable_ax'):
            return

        # Load latest state from disk
        disk = {}
        try:
            if os.path.isfile(self.save_path):
                with open(self.save_path, 'r', encoding='utf-8') as f:
                    disk = json.load(f) or {}
        except Exception:
            pass

        # Determine solution mode
        edge_solution = None
        try:
            edge_solution = disk.get('edge_solution')
            if edge_solution is None and isinstance(disk.get('interface'), dict):
                edge_solution = disk['interface'].get('edge_solution')
        except Exception:
            edge_solution = None
        mode = (str(edge_solution).strip().upper() if edge_solution not in (None, '') else 'DC')
        if mode not in ('DC', 'AC'):
            mode = 'DC'

        calc = disk.get('calculator') if isinstance(disk, dict) else None
        yr = calc.get('yearly_result') if isinstance(calc, dict) else None
        dc_list = yr.get('kwh_dc_usable') if isinstance(yr, dict) else None
        ac_list = yr.get('kwh_ac_usable') if isinstance(yr, dict) else None
        data_list = dc_list if mode == 'DC' else ac_list

        if not (isinstance(data_list, list) and len(data_list) >= 21):
            self.usable_ax.clear()
            self.usable_ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=self.usable_ax.transAxes, fontsize=9)
            self.usable_ax.set_xticks([])
            self.usable_ax.set_yticks([])
            self.usable_canvas.draw_idle()
            return

        # Get display unit from interface data
        interface_data = disk.get('interface', {})
        capacity_unit_display = interface_data.get("capacity_unit_display", "kWh")

        x = list(range(0, 21))  # years 0..20
        try:
            y_raw = [float(data_list[i]) for i in x]  # Raw kWh values
        except Exception:
            y_raw = []
        if len(y_raw) != 21:
            self.usable_ax.clear()
            self.usable_ax.text(0.5, 0.5, 'Invalid data', ha='center', va='center', transform=self.usable_ax.transAxes, fontsize=9)
            self.usable_canvas.draw_idle()
            return

        # Convert to display unit if needed
        if capacity_unit_display == "MWh":
            # Convert from kWh to MWh
            y = [val / 1000.0 for val in y_raw]
            y_unit = "MWh"
        else:
            # Keep as kWh
            y = y_raw[:]
            y_unit = "kWh"

        self.usable_ax.clear()
        self.usable_ax.set_xlabel('End of Year', fontsize=8)
        self.usable_ax.set_ylabel(f'Usable Capacity ({y_unit})', fontsize=8)
        self.usable_ax.set_title(f'Usable Capacity ({mode})', fontsize=8)
        color = (THEME_RGB[0]/255.0, THEME_RGB[1]/255.0, THEME_RGB[2]/255.0)
        self.usable_ax.plot(x, y, color=color, linewidth=1, label=f'Usable ({mode})')  # no markers
        self.usable_ax.fill_between(x, y, color=color, alpha=0.25)
        self.usable_ax.set_xlim(0, 20)
        self.usable_ax.set_xticks(x)  # x is now [0, 1, 2, 3, ..., 20]
        # Min Required horizontal line (if capacity_kwh available) & keep value for axis scaling
        cap_num = None
        try:
            cap_val = None
            if 'capacity_kwh' in disk:
                cap_val = disk.get('capacity_kwh')
            else:
                for _k in ('interface', 'site', 'calculator'):
                    sect = disk.get(_k)
                    if isinstance(sect, dict) and 'capacity_kwh' in sect:
                        cap_val = sect.get('capacity_kwh')
                        break
            if cap_val not in (None, ''):
                try:
                    cap_num = float(str(cap_val).replace(',', '').strip())
                except Exception:
                    cap_num = None
            if cap_num is not None:
                # Convert min required to display unit if needed
                if capacity_unit_display == "MWh":
                    cap_display = cap_num / 1000.0  # Convert to MWh
                    min_req_label = f'Min Required ({cap_display:.1f} {y_unit})'
                else:
                    cap_display = cap_num  # Keep as kWh
                    min_req_label = f'Min Required ({cap_display:.0f} {y_unit})'
                
                self.usable_ax.plot(x, [cap_display]*len(x), linestyle='--', linewidth=1.5, color="#003CFF", label=min_req_label)
        except Exception:
            cap_num = None

        # Adjust y-limits to include both usable curve and min required line
        try:
            data_for_limits = list(y)
            if cap_num is not None:
                # Use the display unit value for limits calculation
                cap_display_for_limits = cap_display if 'cap_display' in locals() else cap_num
                data_for_limits.append(cap_display_for_limits)
            min_val = min(data_for_limits)
            max_val = max(data_for_limits)
            if min_val == max_val:
                # Expand a tiny range
                min_val -= 0.5 if min_val != 0 else -0.5
                max_val += 0.5 if max_val != 0 else 0.5
            margin = 0.05 * (max_val - min_val)
            ymin = 0 if min_val >= 0 else min_val - margin
            ymax = max_val + margin
            self.usable_ax.set_ylim(ymin, ymax)
        except Exception:
            pass
        self.usable_ax.tick_params(axis='both', labelsize=8)
        try:
            self.usable_ax.legend(fontsize=8, frameon=False)
        except Exception:
            pass
        self.usable_ax.grid(True, linestyle='--', alpha=0.3)
        self.usable_canvas.draw_idle()

    # --------- New unified pipeline helpers ---------
    def _save_inputs_only(self) -> None:
        """Persist current BOL inputs to state file only (no calculations)."""
        try:
            self.state.setdefault("calculator", {})
            self.state["calculator"]["inputs"] = {
                "bol_cabinets": self.input_bol_cabinets.text().strip(),
                "bol_confluence": self.input_bol_confluence.text().strip(),
            }
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _run_full_pipeline(self) -> None:
        """Run full algorithm chain and refresh all UI tables."""
        # 1. System outputs
        try:
            if compute_and_persist_system_outputs is not None:
                compute_and_persist_system_outputs(self.save_path)
        except Exception:
            pass
        # 2. Containers depend on aug + bol
        try:
            self._recompute_containers_via_algo()
        except Exception:
            pass
        # 3. SOH
        try:
            from Algorithm import compute_and_persist_soh_percent as _algo_soh
            _algo_soh(self.save_path)
        except Exception:
            pass
        # 4. kWh metrics
        try:
            from Algorithm import compute_and_persist_kwh_dc_nameplate as _algo_dc_np
            _algo_dc_np(self.save_path)
        except Exception:
            pass
        try:
            from Algorithm import compute_and_persist_kwh_dc_usable as _algo_dc_use
            _algo_dc_use(self.save_path)
        except Exception:
            pass
        try:
            from Algorithm import compute_and_persist_kwh_ac_usable as _algo_ac_use
            _algo_ac_use(self.save_path)
        except Exception:
            pass
        # 5. Delta
        try:
            from Algorithm import compute_and_persist_delta as _algo_delta
            _algo_delta(self.save_path)
        except Exception:
            pass

        # Reload state into memory
        try:
            if os.path.isfile(self.save_path):
                with open(self.save_path, "r", encoding="utf-8") as f:
                    self.state = json.load(f) or self.state
        except Exception:
            pass

        # Refresh displays
        try:
            self._refresh_system_output_table()
        except Exception:
            pass
        try:
            self._refresh_yearly_result_containers()
        except Exception:
            pass
        try:
            # This fills SOH / kWh columns / Delta in one go
            self._recompute_delta_via_algo()
        except Exception:
            pass
        try:
            self._refresh_min_required()
        except Exception:
            pass
        try:
            self._recompute_aug_cap()
        except Exception:
            pass
        try:
            self._update_usable_capacity_graph()
        except Exception:
            pass

    def _on_bol_changed(self) -> None:
        """Triggered when BOL cabinets input loses focus; run full pipeline."""
        self._save_inputs_only()
        self._run_full_pipeline()

        # Update graph after BOL change pipeline
        try:
            self._update_usable_capacity_graph()
        except Exception:
            pass

        # Read back and populate column index 5 (0-based)
        try:
            disk = {}
            if os.path.isfile(self.save_path):
                with open(self.save_path, "r", encoding="utf-8") as f:
                    disk = json.load(f) or {}
            calc = disk.get("calculator") if isinstance(disk, dict) else None
            yr = calc.get("yearly_result") if isinstance(calc, dict) else None
            lst = yr.get("kwh_ac_usable") if isinstance(yr, dict) else None
            if isinstance(lst, list) and len(lst) > 0:
                rows_main = self.tbl_main.rowCount()
                for r in range(rows_main):
                    v = lst[r] if r < len(lst) else lst[-1]
                    text = f"{float(v):.2f}"
                    cell = self.tbl_main.item(r, 5)
                    if cell is None:
                        cell = QTableWidgetItem()
                        cell.setTextAlignment(Qt.AlignCenter)
                        cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                        self.tbl_main.setItem(r, 5, cell)
                    cell.setText(text)
        except Exception:
            pass

        # Read back and populate column index 4 (0-based)
        try:
            disk = {}
            if os.path.isfile(self.save_path):
                with open(self.save_path, "r", encoding="utf-8") as f:
                    disk = json.load(f) or {}
            calc = disk.get("calculator") if isinstance(disk, dict) else None
            yr = calc.get("yearly_result") if isinstance(calc, dict) else None
            lst = yr.get("kwh_dc_usable") if isinstance(yr, dict) else None
            if isinstance(lst, list) and len(lst) > 0:
                rows_main = self.tbl_main.rowCount()
                for r in range(rows_main):
                    v = lst[r] if r < len(lst) else lst[-1]
                    text = f"{float(v):.2f}"
                    cell = self.tbl_main.item(r, 4)
                    if cell is None:
                        cell = QTableWidgetItem()
                        cell.setTextAlignment(Qt.AlignCenter)
                        cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                        self.tbl_main.setItem(r, 4, cell)
                    cell.setText(text)
        except Exception:
            pass

        # Read back and populate column index 3 (0-based)
        try:
            disk = {}
            if os.path.isfile(self.save_path):
                with open(self.save_path, "r", encoding="utf-8") as f:
                    disk = json.load(f) or {}
            calc = disk.get("calculator") if isinstance(disk, dict) else None
            yr = calc.get("yearly_result") if isinstance(calc, dict) else None
            lst = yr.get("kwh_dc_nameplate") if isinstance(yr, dict) else None
            if isinstance(lst, list) and len(lst) > 0:
                rows_main = self.tbl_main.rowCount()
                for r in range(rows_main):
                    v = lst[r] if r < len(lst) else lst[-1]
                    text = f"{float(v):.2f}"
                    cell = self.tbl_main.item(r, 3)
                    if cell is None:
                        cell = QTableWidgetItem()
                        cell.setTextAlignment(Qt.AlignCenter)
                        cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                        self.tbl_main.setItem(r, 3, cell)
                    cell.setText(text)
        except Exception:
            pass

        # Read back and populate column index 2
        try:
            disk = {}
            if os.path.isfile(self.save_path):
                with open(self.save_path, "r", encoding="utf-8") as f:
                    disk = json.load(f) or {}
            calc = disk.get("calculator") if isinstance(disk, dict) else None
            yr = calc.get("yearly_result") if isinstance(calc, dict) else None
            lst = yr.get("soh_percent") if isinstance(yr, dict) else None
            if isinstance(lst, list) and len(lst) > 0:
                rows_main = self.tbl_main.rowCount()
                for r in range(rows_main):
                    v = lst[r] if r < len(lst) else lst[-1]
                    text = f"{float(v) * 100:.2f}%"
                    cell = self.tbl_main.item(r, 2)
                    if cell is None:
                        cell = QTableWidgetItem()
                        cell.setTextAlignment(Qt.AlignCenter)
                        cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                        self.tbl_main.setItem(r, 2, cell)
                    cell.setText(text)
        except Exception:
            pass


# ------------------------------
# Entrypoint
# ------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    w = CalculatorPage()
    w.show()
    sys.exit(app.exec_())
