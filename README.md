# BESS Sizing Tool - Streamlit Web Application

## Installation

```bash
pip install -r requirements.txt
# or
pip install streamlit requests pandas numpy Pillow
```

## Run

```bash
streamlit run ui.py
```

The app will open in your browser at: `http://localhost:8501`.

## Project Structure

```
Standard-Solution-Tool/
├── ui.py              # Streamlit UI (three-step flow)
├── algorithm.py       # Business logic & API calls
├── images/            # Image assets
│   ├── 760+DC.png
│   ├── 760+AC.png
│   └── ...
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

## Features

### Current Implementation

#### Page 1: Project Overview
- Basic info inputs (Customer, Project, Use Case, Life Stage)
- Temperature fetch (City or Zipcode) using Open-Meteo API
- System design inputs (Power/Capacity with kW/MW and kWh/MWh units)
- Auto C-rate calculation and display
- Lifecycle inputs (Delivery Date, COD, Augmentation)
- Bottom-right Next button to proceed
- Note: Product/Model/Solution selection is moved to Page 2

#### Page 2: System Configuration
- Top title and subtitle
- Compact selectors for Product, Model (only for EDGE), and Solution
- Single button: “↻ Load Options”
  - Updates Product/Model/Solution
  - Recomputes C-rate from current inputs on Page 1 (no need to go back)
  - Regenerates two PCS options when applicable
- PCS options rendering (Configuration A/B) with images and text
- Safe image rendering (no errors if file missing)
- When selected, only the chosen configuration is shown
- Special rules:
  - EDGE with 422kWh or 338kWh → No recommended solution
  - GRID5015 with DC solution → No recommended solution

#### Page 3: Results & Analysis
- Capacity Analysis Table (9 columns, 20 rows)
- Performance Chart (sample line chart)
- Navigation buttons on this page:
  - “← Edit Info” (back to Page 1)
  - “↻ Change PCS” (back to Page 2)
- Export Configuration (placeholder)

### Data Management
- All data persisted in `st.session_state`
- Cross-page state continuity

### TODO
- Export Configuration (image/PDF)
- Auto-fill table values based on calculations
- Dynamic chart data

## Deployment

### Streamlit Cloud (free)
1. Create a GitHub repository
2. Push code to GitHub
3. Visit https://streamlit.io/cloud
4. Connect your repo and deploy
5. Share the permanent URL

## Tech Stack
- Streamlit: three-step interactive UI
- Requests: HTTP calls (weather API)
- Open-Meteo API: free weather data
- Pandas: data tables
- NumPy: numeric utilities
- Pillow: image support

## UI Notes
- Responsive layout for various screen sizes
- Unified theme color: RGB(234, 85, 32) with hover effects
- Compact components and spacing tuned for a dense layout

## Changelog

### v0.0.1 (2025-12-02)
- Initial Streamlit UI completed (export pending)
- Completed three-step workflow
- Page 2: PCS options A/B with image-based rendering
- Page 3: Results table + chart
- Navigation system (Edit Info / Change PCS)
- Image assets under `images/`
- Export Configuration button (placeholder)
- Responsive design and theme improvements
- Session state persistence fixes

### v0.0.0 (2025-11-XX)
- Migration start: PyQt5 → Streamlit
- Implemented basic Project Overview page