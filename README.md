# BESS Sizing Tool - Streamlit Web Application

## 依赖安装

```bash
pip install streamlit requests
```

## 运行应用

```bash
streamlit run ui.py
```

应用将在浏览器中自动打开，默认地址：`http://localhost:8501`

## 文件结构

```
Standard-Solution-Tool/
├── ui.py              # UI界面（三页式流程）
├── algorithm.py       # 算法模块（计算、API调用）
├── images/            # 图片资源文件夹
│   ├── 760+DC.png    # PCS Configuration A 图片
│   └── 760+AC.png    # PCS Configuration B 图片
├── requirements.txt   # Python依赖
└── README.md         # 本文件
```

## 功能特性

### 当前实现：

#### 第一页：Project Overview（项目概览）
- ✅ 项目基本信息输入（Customer、Project、Use Case等）
- ✅ 温度自动查询（支持城市名或邮编，基于Open-Meteo API）
- ✅ 产品选择（EDGE/GRID5015/GRID3421）
- ✅ EDGE型号选择（760kWh/676kWh/591kWh等）
- ✅ 解决方案类型（DC/AC）
- ✅ 系统参数配置（Power、Capacity，支持kW/MW、kWh/MWh单位切换）
- ✅ C-rate自动计算并显示
- ✅ 生命周期信息（Delivery Date、COD、Augmentation）
- ✅ 右下角 Next 按钮进入下一页

#### 第二页：System Configuration（系统配置）
- ✅ PCS配置选择（Configuration A 和 Configuration B）
- ✅ 配置图片显示（760+DC.png / 760+AC.png）
- ✅ PCS详细信息展示（型号、数量、电池配置、总功率）
- ✅ 选择后仅显示已选配置
- ✅ 导航按钮：
  - "← Edit Info" - 返回第一页修改项目信息
  - "↻ Re-select PCS" - 重新选择PCS配置

#### 第三页：Results & Analysis（结果分析）
- ✅ Capacity Analysis Table（容量分析表）
  - 9列数据：End of Year, Containers in Service, PCS in Service, SOH, DC Nameplate, DC Usable, AC Usable @ MVT, Min. Required, Δ
  - 20行数据（Year 1-20）
  - 紧凑型表格样式，刚好显示20行
- ✅ Performance Chart（性能图表）
  - 折线图显示 DC Usable, AC Usable, Min. Required
- ✅ 导航按钮：
  - "← Edit Info" - 返回第一页修改项目信息
  - "↻ Change PCS" - 返回第二页重新选择PCS
- ✅ Export Configuration 按钮（右下角，自适应宽度）

### 数据管理：
- ✅ 全程使用 session_state 保存数据
- ✅ 支持跨页面数据持久化
- ✅ 支持灵活的页面导航和数据修改

### 待实现：
- ⏳ Export Configuration 功能（网页截图/PDF导出）
- ⏳ 表格数据自动填充（基于算法计算）
- ⏳ 性能图表数据动态生成

## 部署到云端

### Streamlit Cloud (推荐，免费)

1. 创建 GitHub repository
2. 推送代码到 GitHub
3. 访问 https://streamlit.io/cloud
4. 连接 GitHub repo 并部署
5. 获得永久URL，分享给销售团队

### 优势

- ✅ 无需打包，体积小
- ✅ 自动更新，推送代码即部署
- ✅ 跨平台，浏览器即用
- ✅ 便于维护和快速迭代

## 技术栈

- **Streamlit**: Python Web框架，实现三页式交互流程
- **Requests**: HTTP请求库（温度API）
- **Open-Meteo API**: 免费天气数据API
- **Pandas**: 数据处理和表格展示
- **NumPy**: 数值计算（图表数据生成）

## UI 设计特点

### 响应式设计
- 自适应不同屏幕尺寸（手机、平板、桌面）
- 小屏幕、超大屏幕特别优化
- 按钮宽度自适应文字内容

### 主题色
- 主色调：RGB(234, 85, 32) - 橙色
- 所有按钮、标题、分组框统一使用主题色
- Hover 效果：85% 不透明度

### 交互体验
- 三页式流程，清晰明了
- 灵活的导航系统，支持任意页面跳转
- 数据持久化，修改后自动保存
- 紧凑布局，信息密度高

## 更新日志

### v2.0.0 (2025-01-XX)
- ✨ 完整实现三页式工作流程
- ✨ 第二页：PCS配置选择（Configuration A/B）
- ✨ 第三页：结果分析（表格 + 图表）
- ✨ 灵活的导航系统（Edit Info / Change PCS / Re-select PCS）
- ✨ 图片资源管理（images文件夹）
- ✨ Export Configuration 按钮（待实现截图功能）
- 🎨 响应式设计优化
- 🎨 主题色统一应用
- 🐛 修复数据持久化问题

### v0.0.0 (2025-11-XX)
- 初始版本：PyQt5 → Streamlit 迁移
- 实现项目信息输入页面
- 保留所有原有功能
### v0.0.1 (2025-12-02)
- UI界面完成，还差导出按键