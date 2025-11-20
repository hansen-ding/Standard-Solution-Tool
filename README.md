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
Sales Tool/
├── ui.py              # UI界面（项目信息输入页面）
├── algorithm.py       # 算法模块（计算、API调用）
├── requirements.txt   # Python依赖
└── README.md         # 本文件
```

## 功能特性

### 当前实现：
- ✅ 项目基本信息输入
- ✅ 产品选择（EDGE/GRID5015/GRID3421）
- ✅ 系统参数配置（Power、Capacity、C-rate自动计算）
- ✅ 温度API自动查询（Open-Meteo）
- ✅ 生命周期信息录入
- ✅ 数据自动保存（session_state）

### 待实现：
- ⏳ 第二页：PCS选择
- ⏳ 第三页：项目汇总
- ⏳ PDF报告导出

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

- **Streamlit**: Python Web框架
- **Requests**: HTTP请求库（温度API）
- **Open-Meteo API**: 免费天气数据API

## 更新日志

### v1.0.0 (2025-01-XX)
- 初始版本：PyQt5 → Streamlit 迁移
- 实现项目信息输入页面
- 保留所有原有功能
