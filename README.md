# BESS Sizing Tool

A professional Battery Energy Storage System (BESS) sizing and configuration tool built with Streamlit for sales teams.

## 📋 Features

- **Project Overview Input**: Customer info, location, system requirements
- **Temperature Data**: Auto-fetch max/min temperature by location
- **System Design**: Power/capacity input with automatic C-rate calculation
- **Product Selection**: EDGE and GRID5015 product lines
- **PCS Configuration**: Multiple configuration options with visual comparison
- **Performance Analysis**: 
  - 20-year capacity degradation curves
  - SOH (State of Health) tracking
  - DC/AC usable capacity calculations
  - Augmentation planning support
- **Interactive Charts**: Capacity vs. time visualization

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. Clone or download this repository:
```bash
cd Standard-Solution-Tool
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run ui.py
```

4. Open your browser and navigate to:
```
http://localhost:8501
```

## 📁 Project Structure

```
Standard-Solution-Tool/
├── ui.py                      # Main Streamlit application
├── algorithm.py               # Core calculation algorithms
├── requirements.txt           # Python dependencies
├── data/
│   ├── BESS_Specs.xlsx       # BESS product specifications
│   ├── degradation_curves/   # Battery degradation data
│   └── PCS_images/           # PCS configuration images
└── README.md
```

## 🔧 Configuration

### Custom Theme (Optional)

Create `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#EA5520"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"

[server]
port = 8501
maxUploadSize = 200
```

## 🌐 Deployment Options

### Option 1: Internal Network Sharing (Simple)

```bash
streamlit run ui.py --server.address=0.0.0.0 --server.port=8501
```

Share the URL: `http://YOUR_IP:8501`

### Option 2: Company Server (Recommended)

```bash
# Install as system service
nohup streamlit run ui.py --server.port=8501 --server.address=0.0.0.0 &
```

### Option 3: Cloud Deployment

Deploy to AWS, Azure, or use Streamlit Cloud (see documentation)

## 🔒 Security

For production deployment, consider adding:

1. **Password Protection**: Add authentication in `ui.py`
2. **HTTPS**: Use reverse proxy (nginx/Apache)
3. **Access Control**: VPN or IP whitelist
4. **Data Encryption**: For sensitive information

## 📊 Usage Guide

### Step 1: Project Overview
- Enter customer and project details
- Fetch location temperature data
- Input power/capacity requirements

### Step 2: System Configuration
- Select product type (EDGE/GRID5015)
- Choose model and solution (DC/AC)
- Compare PCS configurations

### Step 3: Results & Analysis
- Review capacity degradation curves
- Analyze 20-year performance
- Plan augmentation strategy (if applicable)

## 🛠️ Troubleshooting

### Common Issues

**Port already in use:**
```bash
streamlit run ui.py --server.port=8502
```

**Missing dependencies:**
```bash
pip install -r requirements.txt --upgrade
```

**Data file not found:**
Ensure all Excel files are in the `data/` folder

## 📝 Version History

- **v1.0** (2024) - Initial release
  - Project overview input
  - PCS configuration selection
  - Performance analysis and visualization

## 👥 Support

For internal support, contact your IT administrator or the development team.

## 📄 License

Internal company use only. Do not distribute without authorization.