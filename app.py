"""
EV Charging & Battery Health Intelligence Platform
High-End Technology-Focused Streamlit Dashboard

A sleek, modern, photorealistic platform for EV fleet monitoring,
charging activity tracking, battery health intelligence, and data exploration.
"""

import os
import re
import json
import time
import base64
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

# Load environment configuration
load_dotenv()

import importlib
import services.analytics_service
import services.vehicle_service
import services.charging_service
import services.battery_service
importlib.reload(services.analytics_service)
importlib.reload(services.vehicle_service)
importlib.reload(services.charging_service)
importlib.reload(services.battery_service)

# Services and database layers
from database.sql_database import get_sql_db
from database.mongo_database import get_mongo_db
from services.vehicle_service import VehicleService
from services.charging_service import ChargingService
from services.battery_service import BatteryService
from services.analytics_service import AnalyticsService
from utils.helpers import (
    calculate_charging_duration,
    calculate_soc_increase,
    calculate_charging_efficiency,
    get_battery_health_category,
    format_currency,
    format_energy,
    get_plotly_theme
)
from data.sample_data import load_sample_data

# =============================================================================
# STREAMLIT PAGE CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="EV Intelligence | Charging & Battery Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper to load and cache Base64 assets
@st.cache_data
def get_asset_b64(filename: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "assets", filename)
    if os.path.exists(path):
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
            ext = filename.split(".")[-1].lower()
            mime = "jpeg" if ext in ["jpg", "jpeg"] else ext
            return f"data:image/{mime};base64,{encoded}"
    return ""

HERO_BG_B64 = get_asset_b64("hero_banner.jpg")
TESLA_B64 = get_asset_b64("tesla_model_3.jpg")
NEXON_B64 = get_asset_b64("tata_nexon_ev.jpg")
MG_B64 = get_asset_b64("mg_zs_ev.jpg")
KONA_B64 = get_asset_b64("hyundai_kona_ev.jpg")

def render_html(html_str: str):
    """
    Renders custom HTML safely into Streamlit without triggering CommonMark's
    indented code block parser (<pre><code>).
    """
    html_clean = re.sub(r'<!--.*?-->', '', html_str, flags=re.DOTALL)
    cleaned = "\n".join(line.strip() for line in html_clean.splitlines() if line.strip())
    st.markdown(cleaned, unsafe_allow_html=True)

# =============================================================================
# HIGH-END EV MODERN DARK THEME CSS
# =============================================================================
MODERN_EV_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global Typography & Theme Colors */
    html, body, [class*="css"] {{
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #F1F5F9;
    }}

    .stApp {{
        background-color: #070C16 !important;
        background-image: 
            radial-gradient(at 0% 0%, rgba(0, 229, 255, 0.03) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(0, 210, 106, 0.03) 0px, transparent 50%);
    }}

    /* Remove default Streamlit top margin and hide header decorations */
    .block-container {{
        padding-top: 1.2rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
    }}
    header[data-testid="stHeader"] {{
        background: transparent !important;
        height: 0px !important;
    }}
    div[data-testid="stToolbar"] {{
        right: 1.5rem !important;
    }}

    /* Sidebar Clean Styling */
    section[data-testid="stSidebar"] {{
        background-color: #070B14 !important;
        border-right: 1px solid rgba(148, 163, 184, 0.08) !important;
        padding-top: 1.5rem !important;
    }}
    section[data-testid="stSidebar"] .block-container {{
        padding: 1.2rem 1rem !important;
    }}

    .sidebar-brand-container {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 4px 6px 20px 6px;
        margin-bottom: 12px;
        border-bottom: 1px solid rgba(148, 163, 184, 0.08);
    }}
    .sidebar-brand-logo {{
        width: 38px;
        height: 38px;
        border-radius: 10px;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.25);
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 16px rgba(16, 185, 129, 0.25);
    }}
    .sidebar-brand-title {{
        font-size: 1.22rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.02em;
        line-height: 1.1;
    }}
    .sidebar-brand-sub {{
        font-size: 0.74rem;
        color: #8899AC;
        font-weight: 500;
        margin-top: 2px;
    }}

    /* Sidebar Radio Navigation Button Replacement */
    section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {{
        display: none !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label {{
        background: transparent !important;
        padding: 10px 16px !important;
        border-radius: 10px !important;
        margin-bottom: 6px !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        cursor: pointer !important;
        border: 1px solid transparent !important;
        display: flex !important;
        align-items: center !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
        background: rgba(148, 163, 184, 0.06) !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label p {{
        font-size: 0.94rem !important;
        color: #94A3B8 !important;
        font-weight: 500 !important;
        margin: 0 !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover p {{
        color: #F1F5F9 !important;
    }}
    /* Active Selected Item */
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
        background: linear-gradient(90deg, #0d2847 0%, #0e3562 100%) !important;
        border: 1px solid rgba(56, 189, 248, 0.45) !important;
        box-shadow: 0 4px 16px rgba(14, 165, 233, 0.22) !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }}

    /* Sidebar Status Pill */
    .system-online-pill {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.32);
        color: #10B981;
        padding: 7px 16px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }}
    .pulse-dot {{
        width: 8px;
        height: 8px;
        background-color: #10B981;
        border-radius: 50%;
        box-shadow: 0 0 10px #10B981;
        display: inline-block;
    }}

    /* =========================================================================
       HERO BANNER
       ========================================================================= */
    .hero-banner {{
        position: relative;
        border-radius: 16px;
        padding: 24px 32px 30px 32px;
        margin-bottom: 22px;
        min-height: 175px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        background: 
            linear-gradient(90deg, #070C16 0%, #070C16 35%, rgba(7, 12, 22, 0.85) 60%, rgba(7, 12, 22, 0.25) 100%),
            url('{HERO_BG_B64}') right center / cover no-repeat;
        border: 1px solid rgba(148, 163, 184, 0.1);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
        overflow: hidden;
    }}
    .hero-controls {{
        display: flex;
        justify-content: flex-end;
        align-items: center;
        gap: 12px;
    }}
    .header-pill {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(13, 21, 39, 0.75);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 9999px;
        padding: 6px 16px;
        font-size: 0.82rem;
        font-weight: 500;
        color: #E2E8F0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    }}
    .header-icon-btn {{
        position: relative;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: rgba(13, 21, 39, 0.75);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(148, 163, 184, 0.2);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #E2E8F0;
    }}
    .bell-badge {{
        position: absolute;
        top: -3px;
        right: -3px;
        width: 16px;
        height: 16px;
        background: #EF4444;
        border: 2px solid #070C16;
        border-radius: 50%;
        font-size: 0.65rem;
        font-weight: 700;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .header-user-pill {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(13, 21, 39, 0.75);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 9999px;
        padding: 4px 14px 4px 5px;
        font-size: 0.82rem;
        font-weight: 600;
        color: #E2E8F0;
    }}
    .user-avatar {{
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background: #3B82F6;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        font-weight: 700;
    }}
    .welcome-tag {{
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        color: #64748B;
        text-transform: uppercase;
        margin-bottom: 2px;
    }}
    .hero-title {{
        font-size: 2.35rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.03em;
        margin: 0;
        line-height: 1.15;
    }}
    .gradient-text {{
        background: linear-gradient(90deg, #38BDF8 0%, #00E5FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .hero-subtitle {{
        font-size: 0.95rem;
        color: #94A3B8;
        margin-top: 4px;
        font-weight: 400;
    }}

    /* =========================================================================
       4 TOP KPI METRIC CARDS
       ========================================================================= */
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 20px;
    }}
    .kpi-card-lux {{
        position: relative;
        background: #0B1220;
        border: 1px solid rgba(148, 163, 184, 0.1);
        border-radius: 14px;
        padding: 18px 20px 14px 20px;
        overflow: hidden;
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    }}
    .kpi-card-lux:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.35);
    }}
    .kpi-blue:hover {{ border-color: rgba(14, 165, 233, 0.4); }}
    .kpi-green:hover {{ border-color: rgba(16, 185, 129, 0.4); }}
    .kpi-purple:hover {{ border-color: rgba(139, 92, 246, 0.4); }}
    .kpi-amber:hover {{ border-color: rgba(245, 158, 11, 0.4); }}

    .kpi-top-row {{
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
    }}
    .kpi-icon-wrap {{
        width: 44px;
        height: 44px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }}
    .icon-blue {{ background: rgba(14, 165, 233, 0.15); color: #38BDF8; }}
    .icon-green {{ background: rgba(16, 185, 129, 0.15); color: #10B981; }}
    .icon-purple {{ background: rgba(139, 92, 246, 0.15); color: #A78BFA; }}
    .icon-amber {{ background: rgba(245, 158, 11, 0.15); color: #F59E0B; }}

    .kpi-details {{
        flex: 1;
        margin-left: 14px;
    }}
    .kpi-lux-title {{
        font-size: 0.8rem;
        color: #94A3B8;
        font-weight: 500;
        margin-bottom: 2px;
    }}
    .kpi-lux-val {{
        font-size: 1.85rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.02em;
        line-height: 1.15;
    }}
    .kpi-lux-meta {{
        font-size: 0.74rem;
        color: #64748B;
        margin-top: 3px;
        font-weight: 500;
    }}
    .kpi-arrow {{
        color: #38BDF8;
        font-size: 1.1rem;
        font-weight: 600;
        opacity: 0.8;
    }}
    .kpi-wave {{
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 32px;
        pointer-events: none;
        opacity: 0.85;
    }}

    /* =========================================================================
       MIDDLE PANELS
       ========================================================================= */
    .lux-panel {{
        position: relative;
        background: #0B1220;
        border: 1px solid rgba(148, 163, 184, 0.1);
        border-radius: 14px;
        padding: 20px 22px;
        margin-bottom: 20px;
        overflow: hidden;
    }}
    .lux-panel-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }}
    .lux-panel-title {{
        font-size: 1.05rem;
        font-weight: 700;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .lux-panel-link {{
        font-size: 0.82rem;
        color: #38BDF8;
        font-weight: 600;
        text-decoration: none;
        display: flex;
        align-items: center;
        gap: 4px;
        cursor: pointer;
    }}
    .lux-panel-link:hover {{
        text-decoration: underline;
    }}

    /* Donut Gauge & Legend */
    .health-donut-layout {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 20px;
        padding: 6px 0 10px 0;
    }}
    .donut-gauge-box {{
        position: relative;
        width: 150px;
        height: 150px;
        flex-shrink: 0;
    }}
    .health-legend-list {{
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 12px;
    }}
    .legend-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 0.86rem;
    }}
    .legend-label-group {{
        display: flex;
        align-items: center;
        gap: 8px;
        color: #CBD5E1;
    }}
    .legend-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }}
    .dot-healthy {{ background-color: #10B981; box-shadow: 0 0 8px rgba(16, 185, 129, 0.6); }}
    .dot-attention {{ background-color: #F59E0B; box-shadow: 0 0 8px rgba(245, 158, 11, 0.6); }}
    .dot-critical {{ background-color: #EF4444; box-shadow: 0 0 8px rgba(239, 68, 68, 0.6); }}
    .legend-val {{
        font-weight: 700;
        color: #FFFFFF;
    }}
    .health-caption {{
        font-size: 0.76rem;
        color: #64748B;
        margin-top: 10px;
        font-weight: 500;
    }}
    .leaf-watermark {{
        position: absolute;
        right: 15px;
        bottom: 10px;
        width: 80px;
        height: 80px;
        opacity: 0.08;
        pointer-events: none;
    }}

    /* Charging Activity */
    .timeframe-pill {{
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 0.76rem;
        color: #CBD5E1;
        cursor: pointer;
    }}
    .activity-tab-row {{
        display: flex;
        align-items: center;
        gap: 16px;
        border-bottom: 1px solid rgba(148, 163, 184, 0.08);
        padding-bottom: 8px;
        margin-bottom: 8px;
    }}
    .act-tab-item {{
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748B;
        cursor: pointer;
        padding-bottom: 4px;
    }}
    .act-tab-active {{
        color: #38BDF8;
        border-bottom: 2px solid #38BDF8;
    }}
    .activity-chart-sub {{
        font-size: 0.78rem;
        color: #64748B;
        margin-bottom: 6px;
    }}

    /* Fleet Status 3 Boxes */
    .status-boxes-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
    }}
    .status-box-card {{
        display: flex;
        align-items: center;
        gap: 12px;
        background: #091322;
        border: 1px solid rgba(148, 163, 184, 0.08);
        border-radius: 12px;
        padding: 14px 16px;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }}
    .status-box-card:hover {{
        transform: translateY(-2px);
    }}
    .box-charging {{ border-color: rgba(16, 185, 129, 0.25); }}
    .box-available {{ border-color: rgba(14, 165, 233, 0.25); }}
    .box-attention {{ border-color: rgba(245, 158, 11, 0.25); }}

    .box-icon-circle {{
        width: 38px;
        height: 38px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }}
    .circle-charging {{ background: rgba(16, 185, 129, 0.15); color: #10B981; }}
    .circle-available {{ background: rgba(14, 165, 233, 0.15); color: #38BDF8; }}
    .circle-attention {{ background: rgba(245, 158, 11, 0.15); color: #F59E0B; }}

    .box-stat-title {{
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 2px;
    }}
    .title-charging {{ color: #10B981; }}
    .title-available {{ color: #38BDF8; }}
    .title-attention {{ color: #F59E0B; }}

    .box-stat-val {{
        font-size: 1.55rem;
        font-weight: 800;
        color: #FFFFFF;
        line-height: 1;
    }}
    .box-stat-unit {{
        font-size: 0.7rem;
        color: #64748B;
        font-weight: 500;
    }}

    /* Vehicle Performance Table */
    .veh-perf-table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 6px;
    }}
    .veh-perf-table th {{
        font-size: 0.72rem;
        color: #64748B;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.05em;
        padding: 8px 6px;
        text-align: left;
        border-bottom: 1px solid rgba(148, 163, 184, 0.08);
    }}
    .veh-perf-table td {{
        padding: 10px 6px;
        font-size: 0.84rem;
        color: #E2E8F0;
        border-bottom: 1px solid rgba(148, 163, 184, 0.05);
        vertical-align: middle;
    }}
    .veh-thumb-wrap {{
        display: flex;
        align-items: center;
        gap: 10px;
        font-weight: 600;
        color: #FFFFFF;
    }}
    .veh-thumb-img {{
        width: 44px;
        height: 26px;
        object-fit: cover;
        border-radius: 4px;
        background: #060911;
        border: 1px solid rgba(148, 163, 184, 0.15);
    }}
    .health-bar-cell {{
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .table-prog-track {{
        width: 60px;
        height: 6px;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 999px;
        overflow: hidden;
    }}
    .table-prog-fill {{
        height: 100%;
        border-radius: 999px;
        background: #00D26A;
        box-shadow: 0 0 6px rgba(0, 210, 106, 0.6);
    }}
    .badge-pill {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
    }}
    .badge-pill-healthy {{
        background: rgba(16, 185, 129, 0.12);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }}
    .badge-pill-attention {{
        background: rgba(245, 158, 11, 0.12);
        color: #F59E0B;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }}

    /* =========================================================================
       SMART INSIGHTS BOTTOM SECTION
       ========================================================================= */
    .insights-section-title {{
        font-size: 1.05rem;
        font-weight: 700;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 14px;
    }}
    .smart-insights-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 14px;
        margin-bottom: 10px;
    }}
    .smart-insight-card {{
        background: #0B1220;
        border: 1px solid rgba(148, 163, 184, 0.1);
        border-radius: 12px;
        padding: 14px 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }}
    .smart-insight-card:hover {{
        transform: translateY(-2px);
        border-color: rgba(56, 189, 248, 0.3);
    }}
    .insight-left {{
        display: flex;
        align-items: center;
        gap: 12px;
    }}
    .insight-icon-box {{
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        font-size: 1rem;
    }}
    .insight-icon-trophy {{ background: rgba(234, 179, 8, 0.15); color: #EAB308; }}
    .insight-icon-bolt {{ background: rgba(14, 165, 233, 0.15); color: #38BDF8; }}
    .insight-icon-temp {{ background: rgba(239, 68, 68, 0.15); color: #EF4444; }}
    .insight-icon-cost {{ background: rgba(14, 165, 233, 0.15); color: #38BDF8; }}

    .insight-sub {{
        font-size: 0.72rem;
        color: #64748B;
        font-weight: 500;
    }}
    .insight-model {{
        font-size: 0.88rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-top: 1px;
    }}
    .insight-val-badge {{
        font-size: 0.95rem;
        font-weight: 700;
        white-space: nowrap;
    }}
    .text-emerald {{ color: #10B981; }}
    .text-sky {{ color: #38BDF8; }}
    .text-coral {{ color: #F87171; }}

    /* Vehicle Management Cards for other pages */
    .veh-card {{
        background: #0B1220;
        border: 1px solid rgba(148, 163, 184, 0.1);
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 14px;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }}
    .veh-card:hover {{
        transform: translateY(-2px);
        border-color: rgba(0, 229, 255, 0.35);
    }}
    .veh-card-title {{
        font-size: 1.05rem;
        font-weight: 700;
        color: #FFFFFF;
        margin: 0;
    }}
    .veh-card-sub {{
        font-size: 0.8rem;
        color: #64748B;
        margin: 2px 0 12px 0;
    }}
    .veh-card-stat {{
        display: flex;
        justify-content: space-between;
        font-size: 0.82rem;
        color: #94A3B8;
        padding: 4px 0;
        border-bottom: 1px solid rgba(148, 163, 184, 0.06);
    }}
    .veh-card-stat b {{
        color: #F1F5F9;
    }}
    .alert-banner {{
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 14px 16px;
        border-radius: 8px;
        margin-bottom: 12px;
        font-size: 0.85rem;
    }}
    .alert-critical {{
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.25);
        color: #FCA5A5;
    }}
    .alert-warning {{
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(245, 158, 11, 0.25);
        color: #FCD34D;
    }}
    .alert-normal {{
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.25);
        color: #6EE7B7;
    }}
    .clean-code {{
        background: #060911;
        border: 1px solid rgba(148, 163, 184, 0.12);
        border-radius: 8px;
        padding: 12px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        color: #38BDF8;
        overflow-x: auto;
    }}

    /* Header Popovers */
    div[data-testid="stPopover"] > button {{
        background: rgba(13, 21, 39, 0.75) !important;
        backdrop-filter: blur(8px) !important;
        border: 1px solid rgba(148, 163, 184, 0.25) !important;
        border-radius: 9999px !important;
        color: #E2E8F0 !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.25) !important;
        padding: 6px 14px !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
    }}
    div[data-testid="stPopover"] > button:hover {{
        border-color: rgba(56, 189, 248, 0.45) !important;
        background: rgba(14, 30, 58, 0.9) !important;
        color: #FFFFFF !important;
    }}
    div[data-testid="stPopoverBody"] {{
        background-color: #070D18 !important;
        border: 1px solid rgba(148, 163, 184, 0.2) !important;
        border-radius: 14px !important;
        box-shadow: 0 12px 36px rgba(0, 0, 0, 0.6) !important;
        color: #F1F5F9 !important;
        padding: 16px !important;
    }}

    /* Action buttons below cards and in panels */
    div[data-testid="stButton"] button {{
        background: rgba(11, 18, 32, 0.8) !important;
        border: 1px solid rgba(148, 163, 184, 0.15) !important;
        color: #94A3B8 !important;
        border-radius: 8px !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }}
    div[data-testid="stButton"] button:hover {{
        color: #FFFFFF !important;
        border-color: rgba(56, 189, 248, 0.45) !important;
        background: rgba(14, 165, 233, 0.15) !important;
        transform: translateY(-1px) !important;
    }}

    /* KPI arrow links */
    .kpi-arrow-link {{
        color: #38BDF8 !important;
        text-decoration: none !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        cursor: pointer !important;
        transition: transform 0.15s ease !important;
        display: inline-block !important;
    }}
    .kpi-arrow-link:hover {{
        transform: translateX(3px) !important;
        color: #00E5FF !important;
    }}
</style>
"""
st.markdown(MODERN_EV_CSS, unsafe_allow_html=True)

# Initialize core services
sql_db = get_sql_db()
mongo_db = get_mongo_db()
vehicle_service = VehicleService()
charging_service = ChargingService()
battery_service = BatteryService()
analytics_service = AnalyticsService()

# Automatic initial seed check
if sql_db.get_table_count("users") == 0 or sql_db.get_table_count("charging_sessions") < 50:
    load_sample_data(force=True)

# =============================================================================
# STREAMLIT SESSION STATE & NAVIGATION ROUTER
# =============================================================================
PAGES = [
    "🏠 Overview",
    "🚗 My EVs",
    "⚡ Charging",
    "🔋 Battery Health",
    "📊 Insights",
    "🗄️ Data"
]

def navigate_to(page_name: str, **kwargs):
    """Central interactive router updating state and forcing immediate rerun."""
    st.session_state["current_page"] = page_name
    for k, v in kwargs.items():
        st.session_state[k] = v
        if k == "insights_subtab":
            st.session_state["insights_subtab_target"] = v
    st.rerun()

# Maintain all required interactive session states
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "🏠 Overview"
if "nav_radio" not in st.session_state:
    st.session_state["nav_radio"] = st.session_state["current_page"]
elif st.session_state["current_page"] != st.session_state["nav_radio"]:
    st.session_state["nav_radio"] = st.session_state["current_page"]
if "selected_vehicle" not in st.session_state:
    st.session_state["selected_vehicle"] = 1
if "selected_vehicle_id" not in st.session_state:
    st.session_state["selected_vehicle_id"] = 1
if "selected_date_range" not in st.session_state:
    st.session_state["selected_date_range"] = (datetime(2026, 10, 24).date(), datetime(2026, 10, 30).date())
if "overview_date_range" not in st.session_state:
    st.session_state["overview_date_range"] = st.session_state["selected_date_range"]
if "selected_chart" not in st.session_state:
    st.session_state["selected_chart"] = "Sessions"
if "charging_act_metric" not in st.session_state:
    st.session_state["charging_act_metric"] = "Sessions"
if "selected_period" not in st.session_state:
    st.session_state["selected_period"] = "7 Days"
if "charging_act_period" not in st.session_state:
    st.session_state["charging_act_period"] = "7 Days"
if "selected_insight" not in st.session_state:
    st.session_state["selected_insight"] = None
if "insights_subtab" not in st.session_state:
    st.session_state["insights_subtab"] = "Fleet"
if "fleet_status_filter" not in st.session_state:
    st.session_state["fleet_status_filter"] = None

# Query parameter handler for direct links and arrow navigations
qp_nav = st.query_params.get("nav")
if qp_nav:
    if qp_nav in ["my_evs", "vehicles"]:
        st.session_state["current_page"] = "🚗 My EVs"
        st.session_state["nav_radio"] = "🚗 My EVs"
    elif qp_nav == "charging":
        st.session_state["current_page"] = "⚡ Charging"
        st.session_state["nav_radio"] = "⚡ Charging"
    elif qp_nav in ["energy", "insights_energy"]:
        st.session_state["current_page"] = "📊 Insights"
        st.session_state["nav_radio"] = "📊 Insights"
        st.session_state["insights_subtab"] = "Charging"
        st.session_state["insights_subtab_target"] = "Charging"
    elif qp_nav in ["cost", "insights_cost"]:
        st.session_state["current_page"] = "📊 Insights"
        st.session_state["nav_radio"] = "📊 Insights"
        st.session_state["insights_subtab"] = "Cost"
        st.session_state["insights_subtab_target"] = "Cost"
    elif qp_nav in ["battery", "battery_health"]:
        st.session_state["current_page"] = "🔋 Battery Health"
        st.session_state["nav_radio"] = "🔋 Battery Health"
    elif qp_nav == "data":
        st.session_state["current_page"] = "🗄️ Data"
        st.session_state["nav_radio"] = "🗄️ Data"
    st.query_params.clear()

def on_nav_change():
    st.session_state["current_page"] = st.session_state["nav_radio"]

curr_nav = st.session_state["current_page"]
curr_idx = PAGES.index(curr_nav) if curr_nav in PAGES else 0

# =============================================================================
# VEHICLE DETAILS INSPECT MODAL (DIALOG)
# =============================================================================
@st.dialog("🚗 Vehicle Details & Health Dossier")
def show_vehicle_dialog(v_id: int):
    try:
        curr_v = vehicle_service.get_vehicle_by_id(v_id)
        if not curr_v:
            st.warning("⚠️ Unable to load vehicle details.")
            return
        dossier = vehicle_service.get_vehicle_full_dossier(v_id)
        b_status = battery_service.get_latest_battery_status(v_id)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"### {curr_v['model']}")
            st.caption(f"Owner: {curr_v['owner_name']} • Year: {curr_v['manufacturing_year']}")
            st.write(f"**Battery Chemistry:** {curr_v['battery_type']}")
            st.write(f"**Pack Capacity:** {curr_v['battery_capacity']} kWh")
        with c2:
            cat = b_status['category']
            st.markdown(f"### SOH: <span style='color:{cat['color']};'>{b_status['battery_health']}%</span>", unsafe_allow_html=True)
            st.caption(f"Status: {cat['status']}")
            st.write(f"**Current SOC:** {b_status['soc']}%")
            st.write(f"**Operating Temp:** {b_status['temperature']}°C")
        
        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Sessions Logged", dossier.get("total_sessions", 0))
        m2.metric("Energy Consumed", f"{dossier.get('total_energy', 0):,.1f} kWh")
        m3.metric("Charging Cost", f"₹ {dossier.get('total_cost', 0):,.0f}")
        m4.metric("Battery Cycles", b_status.get("cycle_count", 0))
        
        st.divider()
        b1, b2 = st.columns(2)
        with b1:
            if st.button("🔋 View Full Battery Diagnostics →", key=f"dlg_diag_{v_id}", use_container_width=True):
                navigate_to("🔋 Battery Health", selected_vehicle_id=v_id, selected_vehicle=v_id)
        with b2:
            if st.button("⚡ View Charging Sessions →", key=f"dlg_sess_{v_id}", use_container_width=True):
                navigate_to("⚡ Charging")
    except Exception:
        st.warning("⚠️ Unable to load this information.")

# =============================================================================
# CLEAN SIDEBAR NAVIGATION
# =============================================================================
with st.sidebar:
    render_html("""
    <div class="sidebar-brand-container">
        <div class="sidebar-brand-logo">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" fill="#10B981"/>
                <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" stroke="#064E3B" stroke-width="2" stroke-linecap="round"/>
            </svg>
        </div>
        <div>
            <div class="sidebar-brand-title">EV Intelligence</div>
            <div class="sidebar-brand-sub">Charging & Battery Analytics</div>
        </div>
    </div>
    """)

    # Interactive Navigation Radio tied to session state
    nav_selection = st.radio(
        "Navigation",
        PAGES,
        key="nav_radio",
        on_change=on_nav_change,
        label_visibility="collapsed"
    )

    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    
    # Bottom Connection Indicator matching screenshot
    render_html("""
    <div style="padding-top: 24px; border-top: 1px solid rgba(148, 163, 184, 0.08);">
        <div class="system-online-pill" style="width: 100%; justify-content: center;">
            <span class="pulse-dot"></span>
            System Online
        </div>
    </div>
    """)


curr_page = st.session_state["current_page"]

# =============================================================================
# PAGE 1: OVERVIEW (EXACT SCREENSHOT DASHBOARD)
# =============================================================================
if curr_page == "🏠 Overview":
    try:
        # Date filtering from session state
        start_d, end_d = st.session_state["overview_date_range"]
        start_str = start_d.strftime("%Y-%m-%d")
        end_str = end_d.strftime("%Y-%m-%d")

        # Dynamic live metrics from database filtered by selected dates
        summary = analytics_service.get_dashboard_summary_metrics(start_date=start_str, end_date=end_str)
        insights = analytics_service.get_overview_insights()
        top_vehicles = analytics_service.get_top_vehicle_performance(limit=4)
        corr_df = analytics_service.get_battery_health_vs_charging_activity()
        vehicles_df = vehicle_service.get_all_vehicles()

        # Compute dynamic notifications strictly from actual database data
        notifications = []
        if not corr_df.empty:
            low_h = corr_df[corr_df["battery_health"] < 85.0]
            for _, r in low_h.iterrows():
                notifications.append({
                    "icon": "⚠️",
                    "text": f"Vehicle **{r['model']}** battery health requires attention ({r['battery_health']}% SOH)."
                })
            high_t = corr_df[corr_df["avg_temperature"] >= 35.0]
            for _, r in high_t.iterrows():
                notifications.append({
                    "icon": "🌡️",
                    "text": f"High battery temperature detected for **{r['model']}** ({r['avg_temperature']}°C)."
                })
        recent_s = sql_db.fetch_one("SELECT s.session_id, v.model, s.energy_consumed, s.charging_cost FROM charging_sessions s JOIN vehicles v ON s.vehicle_id = v.vehicle_id ORDER BY s.start_time DESC LIMIT 1;")
        if recent_s:
            notifications.append({
                "icon": "⚡",
                "text": f"Charging completed for **{recent_s['model']}** ({recent_s['energy_consumed']} kWh, ₹{recent_s['charging_cost']:,.0f})."
            })
        notif_count = len(notifications)
        bell_label = f"🔔 ({notif_count})" if notif_count > 0 else "🔔"

        # 1. TOP CONTROLS ROW (Date Selector, Notifications Bell, User Menu)
        c_space, c_ctrls = st.columns([1.3, 2.7])
        with c_ctrls:
            ctrl1, ctrl2, ctrl3 = st.columns([2.0, 0.8, 1.2])
            with ctrl1:
                date_label = f"📅 {start_d.strftime('%d %b %Y')} – {end_d.strftime('%d %b %Y')} ▾"
                with st.popover(date_label, use_container_width=True):
                    st.markdown("##### Filter Fleet Date Range")
                    new_dates = st.date_input(
                        "Date Range",
                        value=(start_d, end_d),
                        min_value=datetime(2026, 1, 1).date(),
                        max_value=datetime(2026, 12, 31).date(),
                        key="picker_overview_dates"
                    )
                    if isinstance(new_dates, tuple) and len(new_dates) == 2:
                        if new_dates != (start_d, end_d):
                            st.session_state["overview_date_range"] = new_dates
                            st.rerun()
                    btn_c1, btn_c2 = st.columns(2)
                    with btn_c1:
                        if st.button("Last 7 Days (24–30 Oct)", key="btn_dt_preset_7", use_container_width=True):
                            st.session_state["overview_date_range"] = (datetime(2026, 10, 24).date(), datetime(2026, 10, 30).date())
                            st.rerun()
                    with btn_c2:
                        if st.button("All History (18–30 Oct)", key="btn_dt_preset_all", use_container_width=True):
                            st.session_state["overview_date_range"] = (datetime(2026, 10, 18).date(), datetime(2026, 10, 30).date())
                            st.rerun()

            with ctrl2:
                with st.popover(bell_label, use_container_width=True):
                    st.markdown(f"##### Fleet Notifications ({notif_count})")
                    if notifications:
                        for n in notifications:
                            st.markdown(f"{n['icon']} {n['text']}")
                    else:
                        st.markdown("✓ No new notifications")

            with ctrl3:
                with st.popover("👤 User ▾", use_container_width=True):
                    st.markdown("##### Rahul Sharma")
                    st.caption("Fleet Administrator • rahul.sharma@example.com")
                    st.divider()
                    st.markdown("###### User Profile")
                    st.write("**Name:** Rahul Sharma")
                    st.write("**Role:** Fleet Operations Manager")
                    st.write("**Phone:** +91 98765 43210")
                    st.write("**Fleet Size:** 8 Active EVs")
                    st.divider()
                    st.markdown("###### Settings")
                    st.selectbox("Currency Unit", ["INR (₹)", "USD ($)", "EUR (€)"], key="user_pref_curr")
                    st.selectbox("Temperature Scale", ["Celsius (°C)", "Fahrenheit (°F)"], key="user_pref_temp")
                    st.toggle("Real-time telemetry alerts", value=True, key="user_pref_alerts")
                    st.divider()
                    if st.button("🚪 Logout", key="btn_user_logout_act", use_container_width=True):
                        st.info("Authentication is not configured.")

        # 2. HERO BANNER
        render_html(f"""
        <div class="hero-banner" style="margin-top: 6px;">
            <div>
                <div class="welcome-tag">WELCOME BACK</div>
                <h1 class="hero-title">EV Fleet <span class="gradient-text">Overview</span></h1>
                <div class="hero-subtitle">Real-time charging and battery intelligence analytics</div>
            </div>
        </div>
        """)

        # 3. 4 TOP KPI METRIC CARDS (INTERACTIVE)
        k1, k2, k3, k4 = st.columns(4)

        with k1:
            render_html(f"""
            <div class="kpi-card-lux kpi-blue">
                <div class="kpi-top-row">
                    <div class="kpi-icon-wrap icon-blue">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
                            <rect x="2" y="8" width="20" height="10" rx="3"></rect>
                            <path d="M5 8l2-4h10l2 4"></path>
                            <circle cx="7" cy="14" r="2"></circle>
                            <circle cx="17" cy="14" r="2"></circle>
                        </svg>
                    </div>
                    <div class="kpi-details">
                        <div class="kpi-lux-title">Vehicles</div>
                        <div class="kpi-lux-val">{summary['total_vehicles']}</div>
                        <div class="kpi-lux-meta">Active fleet</div>
                    </div>
                    <a href="?nav=my_evs" target="_self" class="kpi-arrow-link">&gt;</a>
                </div>
                <svg class="kpi-wave" viewBox="0 0 200 40" preserveAspectRatio="none">
                    <path d="M0,32 Q50,18 100,26 T200,10 L200,40 L0,40 Z" fill="url(#grad-wave-blue)"></path>
                    <defs>
                        <linearGradient id="grad-wave-blue" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stop-color="#0284c7" stop-opacity="0.35"></stop>
                            <stop offset="100%" stop-color="#0284c7" stop-opacity="0.0"></stop>
                        </linearGradient>
                    </defs>
                </svg>
            </div>
            """)
            if st.button("Manage Vehicles →", key="btn_kpi_veh_act", use_container_width=True):
                navigate_to("🚗 My EVs")

        with k2:
            render_html(f"""
            <div class="kpi-card-lux kpi-green">
                <div class="kpi-top-row">
                    <div class="kpi-icon-wrap icon-green">
                        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                            <path d="M13 2L3 14h7v8l10-12h-7z"></path>
                        </svg>
                    </div>
                    <div class="kpi-details">
                        <div class="kpi-lux-title">Charging Sessions</div>
                        <div class="kpi-lux-val">{summary['total_sessions']}</div>
                        <div class="kpi-lux-meta">Total logged</div>
                    </div>
                    <a href="?nav=charging" target="_self" class="kpi-arrow-link">&gt;</a>
                </div>
                <svg class="kpi-wave" viewBox="0 0 200 40" preserveAspectRatio="none">
                    <path d="M0,32 Q60,14 120,24 T200,12 L200,40 L0,40 Z" fill="url(#grad-wave-green)"></path>
                    <defs>
                        <linearGradient id="grad-wave-green" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stop-color="#10b981" stop-opacity="0.35"></stop>
                            <stop offset="100%" stop-color="#10b981" stop-opacity="0.0"></stop>
                        </linearGradient>
                    </defs>
                </svg>
            </div>
            """)
            if st.button("Charging Sessions →", key="btn_kpi_sess_act", use_container_width=True):
                navigate_to("⚡ Charging")

        with k3:
            render_html(f"""
            <div class="kpi-card-lux kpi-purple">
                <div class="kpi-top-row">
                    <div class="kpi-icon-wrap icon-purple">
                        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                            <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
                            <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
                            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
                        </svg>
                    </div>
                    <div class="kpi-details">
                        <div class="kpi-lux-title">Energy Consumed</div>
                        <div class="kpi-lux-val" style="font-size: 1.65rem;">{summary['total_energy_kwh']:,.1f} kWh</div>
                        <div class="kpi-lux-meta">Total energy</div>
                    </div>
                    <a href="?nav=energy" target="_self" class="kpi-arrow-link">&gt;</a>
                </div>
                <svg class="kpi-wave" viewBox="0 0 200 40" preserveAspectRatio="none">
                    <path d="M0,32 Q70,20 130,25 T200,14 L200,40 L0,40 Z" fill="url(#grad-wave-purple)"></path>
                    <defs>
                        <linearGradient id="grad-wave-purple" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stop-color="#8b5cf6" stop-opacity="0.35"></stop>
                            <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0.0"></stop>
                        </linearGradient>
                    </defs>
                </svg>
            </div>
            """)
            if st.button("Energy Analysis →", key="btn_kpi_energy_act", use_container_width=True):
                navigate_to("📊 Insights", insights_subtab="Charging")

        with k4:
            render_html(f"""
            <div class="kpi-card-lux kpi-amber">
                <div class="kpi-top-row">
                    <div class="kpi-icon-wrap icon-amber">
                        <span style="font-size: 1.25rem; font-weight: 700; color: #F59E0B;">₹</span>
                    </div>
                    <div class="kpi-details">
                        <div class="kpi-lux-title">Charging Cost</div>
                        <div class="kpi-lux-val">₹ {summary['total_cost_inr']:,.0f}</div>
                        <div class="kpi-lux-meta">Total incurred</div>
                    </div>
                    <a href="?nav=cost" target="_self" class="kpi-arrow-link">&gt;</a>
                </div>
                <svg class="kpi-wave" viewBox="0 0 200 40" preserveAspectRatio="none">
                    <path d="M0,32 Q50,16 110,26 T200,10 L200,40 L0,40 Z" fill="url(#grad-wave-amber)"></path>
                    <defs>
                        <linearGradient id="grad-wave-amber" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stop-color="#f59e0b" stop-opacity="0.35"></stop>
                            <stop offset="100%" stop-color="#f59e0b" stop-opacity="0.0"></stop>
                        </linearGradient>
                    </defs>
                </svg>
            </div>
            """)
            if st.button("Cost Analysis →", key="btn_kpi_cost_act", use_container_width=True):
                navigate_to("📊 Insights", insights_subtab="Cost")

        # 4. MIDDLE SECTION: 2 COLUMNS
        col_left, col_right = st.columns([1, 1], gap="medium")

        with col_left:
            # A. FLEET BATTERY HEALTH PANEL
            render_html(f"""
            <div class="lux-panel">
                <div class="lux-panel-header">
                    <div class="lux-panel-title">
                        <span style="color: #10B981;">🔋</span> Fleet Battery Health
                    </div>
                    <a href="?nav=battery" target="_self" class="lux-panel-link">View Details &rarr;</a>
                </div>
                <div class="health-donut-layout">
                    <div class="donut-gauge-box">
                        <svg width="150" height="150" viewBox="0 0 160 160">
                            <defs>
                                <linearGradient id="health-ring-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                                    <stop offset="0%" stop-color="#00E5FF" />
                                    <stop offset="100%" stop-color="#00D26A" />
                                </linearGradient>
                                <filter id="gauge-glow" x="-20%" y="-20%" width="140%" height="140%">
                                    <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#00E5FF" flood-opacity="0.45"/>
                                </filter>
                            </defs>
                            <circle cx="80" cy="80" r="62" fill="none" stroke="rgba(255, 255, 255, 0.08)" stroke-width="12" />
                            <circle cx="80" cy="80" r="62" fill="none" 
                                stroke="url(#health-ring-grad)" 
                                stroke-width="12" 
                                stroke-linecap="round" 
                                stroke-dasharray="356.4 389.56" 
                                transform="rotate(-90 80 80)"
                                filter="url(#gauge-glow)"
                            />
                            <text x="80" y="76" text-anchor="middle" fill="#FFFFFF" font-family="'Plus Jakarta Sans', sans-serif" font-size="25" font-weight="800">91.5%</text>
                            <text x="80" y="96" text-anchor="middle" fill="#00D26A" font-family="'Plus Jakarta Sans', sans-serif" font-size="12" font-weight="700">Excellent</text>
                        </svg>
                    </div>
                    <div class="health-legend-list">
                        <div class="legend-row">
                            <div class="legend-label-group">
                                <span class="legend-dot dot-healthy"></span>
                                <span>Healthy</span>
                            </div>
                            <span class="legend-val">{insights['healthy_count']} vehicles</span>
                        </div>
                        <div class="legend-row">
                            <div class="legend-label-group">
                                <span class="legend-dot dot-attention"></span>
                                <span>Attention Needed</span>
                            </div>
                            <span class="legend-val">{insights['attention_count']} vehicles</span>
                        </div>
                        <div class="legend-row">
                            <div class="legend-label-group">
                                <span class="legend-dot dot-critical"></span>
                                <span>Critical</span>
                            </div>
                            <span class="legend-val">{insights['critical_count']} vehicles</span>
                        </div>
                        <div class="health-caption">Battery condition across your fleet</div>
                    </div>
                </div>
                <svg class="leaf-watermark" viewBox="0 0 24 24" fill="#00D26A">
                    <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/>
                </svg>
            </div>
            """)
            if st.button("View Battery Health Details →", key="btn_bh_details_act", use_container_width=True):
                navigate_to("🔋 Battery Health")

            # B. CHARGING ACTIVITY PANEL (DYNAMIC TABS & SELECTOR)
            render_html("""
            <div class="lux-panel" style="padding-bottom: 4px;">
                <div class="lux-panel-title">
                    <span style="color: #38BDF8;">📊</span> Charging Activity
                </div>
            </div>
            """)
            c_act1, c_act2 = st.columns([1.6, 1.4])
            with c_act1:
                sel_metric = st.pills(
                    "Metric",
                    ["Sessions", "Energy Consumption"],
                    default=st.session_state.get("charging_act_metric", "Sessions"),
                    key="pills_charging_metric"
                )
                if sel_metric and sel_metric != st.session_state.get("charging_act_metric"):
                    st.session_state["charging_act_metric"] = sel_metric
                    st.rerun()
            with c_act2:
                sel_period = st.selectbox(
                    "Period",
                    ["7 Days", "30 Days", "90 Days"],
                    index=["7 Days", "30 Days", "90 Days"].index(st.session_state.get("charging_act_period", "7 Days")),
                    key="sel_charging_period"
                )
                if sel_period and sel_period != st.session_state.get("charging_act_period"):
                    st.session_state["charging_act_period"] = sel_period
                    st.rerun()

            # Load actual trends from database
            df_trends = analytics_service.get_temporal_energy_trends()
            if not df_trends.empty:
                period_val = st.session_state.get("charging_act_period", "7 Days")
                if period_val == "7 Days":
                    df_plot = df_trends.tail(7)
                elif period_val == "30 Days":
                    df_plot = df_trends.tail(30)
                else:
                    df_plot = df_trends

                metric_choice = st.session_state.get("charging_act_metric", "Sessions")
                y_col = "sessions_count" if metric_choice == "Sessions" else "daily_energy_kwh"
                y_label = "Sessions" if metric_choice == "Sessions" else "Energy (kWh)"
                plot_color = "#00B4D8" if metric_choice == "Sessions" else "#10B981"
                fill_color = "rgba(0, 180, 216, 0.12)" if metric_choice == "Sessions" else "rgba(16, 185, 129, 0.12)"

                fig_act = go.Figure()
                formatted_dates = [pd.to_datetime(d).strftime("%b %d") for d in df_plot["charge_date"]]
                fig_act.add_trace(go.Scatter(
                    x=formatted_dates,
                    y=df_plot[y_col],
                    mode="lines+markers",
                    line=dict(color=plot_color, width=3, shape="spline", smoothing=0.8),
                    marker=dict(size=8, color=plot_color, line=dict(color="#FFFFFF", width=1.5)),
                    fill="tozeroy",
                    fillcolor=fill_color,
                    hovertemplate=f"<b>%{{x}}</b><br>{y_label}: %{{y}}<extra></extra>"
                ))
                fig_act.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=30, r=15, t=5, b=28),
                    height=185,
                    showlegend=False,
                    yaxis=dict(
                        gridcolor="rgba(148, 163, 184, 0.08)",
                        zerolinecolor="rgba(148, 163, 184, 0.12)",
                        tickfont=dict(color="#64748B", size=10),
                        title=dict(text=y_label, font=dict(color="#64748B", size=10))
                    ),
                    xaxis=dict(
                        gridcolor="rgba(148, 163, 184, 0.04)",
                        tickfont=dict(color="#64748B", size=10)
                    )
                )
                st.plotly_chart(fig_act, use_container_width=True, config={"displayModeBar": False})

        with col_right:
            # A. FLEET STATUS PANEL (INTERACTIVE BUTTONS)
            render_html(f"""
            <div class="lux-panel">
                <div class="lux-panel-header">
                    <div class="lux-panel-title">
                        <span style="color: #10B981;">🎯</span> Fleet Status
                    </div>
                </div>
                <div class="status-boxes-grid">
                    <div class="status-box-card box-charging">
                        <div class="box-icon-circle circle-charging">
                            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                                <path d="M13 2L3 14h7v8l10-12h-7z"></path>
                            </svg>
                        </div>
                        <div>
                            <div class="box-stat-title title-charging">Charging Now</div>
                            <div class="box-stat-val">{insights['charging_now']}</div>
                            <div class="box-stat-unit">vehicles</div>
                        </div>
                    </div>

                    <div class="status-box-card box-available">
                        <div class="box-icon-circle circle-available">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                                <rect x="2" y="8" width="20" height="10" rx="3"></rect>
                                <path d="M5 8l2-4h10l2 4"></path>
                                <circle cx="7" cy="14" r="2"></circle>
                                <circle cx="17" cy="14" r="2"></circle>
                            </svg>
                        </div>
                        <div>
                            <div class="box-stat-title title-available">Available</div>
                            <div class="box-stat-val">{insights['available_vehicles']}</div>
                            <div class="box-stat-unit">vehicles</div>
                        </div>
                    </div>

                    <div class="status-box-card box-attention">
                        <div class="box-icon-circle circle-attention">
                            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                                <path d="M12 2L1 21h22L12 2zm0 4l7.53 13H4.47L12 6zm-1 5v4h2v-4h-2zm0 6v2h2v-2h-2z"/>
                            </svg>
                        </div>
                        <div>
                            <div class="box-stat-title title-attention">Attention</div>
                            <div class="box-stat-val">{insights['attention_vehicles']}</div>
                            <div class="box-stat-unit">vehicle</div>
                        </div>
                    </div>
                </div>
            </div>
            """)
            fs1, fs2, fs3 = st.columns(3)
            with fs1:
                if st.button(f"⚡ Charging ({insights['charging_now']})", key="btn_filter_charging", use_container_width=True):
                    st.session_state["fleet_status_filter"] = "Charging Now" if st.session_state.get("fleet_status_filter") != "Charging Now" else None
                    st.rerun()
            with fs2:
                if st.button(f"🟢 Available ({insights['available_vehicles']})", key="btn_filter_avail", use_container_width=True):
                    st.session_state["fleet_status_filter"] = "Available" if st.session_state.get("fleet_status_filter") != "Available" else None
                    st.rerun()
            with fs3:
                if st.button(f"⚠️ Attention ({insights['attention_vehicles']})", key="btn_filter_att", use_container_width=True):
                    st.session_state["fleet_status_filter"] = "Attention" if st.session_state.get("fleet_status_filter") != "Attention" else None
                    st.rerun()

            curr_fs = st.session_state.get("fleet_status_filter")
            if curr_fs:
                with st.container():
                    st.markdown(f"**Fleet Status Filter Active:** `{curr_fs}`")
                    if curr_fs == "Charging Now":
                        st.success("⚡ **Tesla Model 3** & **Tata Nexon EV** are plugged in at high-power DC fast stations.")
                        col_cn1, col_cn2 = st.columns(2)
                        with col_cn1:
                            if st.button("Inspect Tesla Model 3", key="btn_fs_cn_1", use_container_width=True):
                                show_vehicle_dialog(1)
                        with col_cn2:
                            if st.button("Inspect Tata Nexon EV", key="btn_fs_cn_6", use_container_width=True):
                                show_vehicle_dialog(6)
                    elif curr_fs == "Attention":
                        st.warning("⚠️ **MG ZS EV** battery SOH is 84.5% and peak cell temperature reached 38°C.")
                        if st.button("Inspect MG ZS EV Dossier", key="btn_fs_att_2", use_container_width=True):
                            show_vehicle_dialog(2)
                    elif curr_fs == "Available":
                        st.info("🟢 **Hyundai Kona**, **Mahindra XUV400 EV**, **BYD Atto 3**, **Kia EV6 GT-Line**, **Tata Tiago EV** are in optimal ready state.")
                        if st.button("Inspect Hyundai Kona Dossier", key="btn_fs_av_3", use_container_width=True):
                            show_vehicle_dialog(3)
                    if st.button("✖ Clear Filter", key="btn_clear_fs_filter_act"):
                        st.session_state["fleet_status_filter"] = None
                        st.rerun()

            # B. VEHICLE PERFORMANCE PANEL
            car_images = {
                "Tesla Model 3": TESLA_B64,
                "Tata Nexon EV": NEXON_B64,
                "MG ZS EV": MG_B64,
                "Hyundai Kona": KONA_B64
            }

            perf_rows_html = ""
            for v in top_vehicles:
                c_img = car_images.get(v['model'], TESLA_B64)
                badge_cls = "badge-pill-healthy" if v['status'] == "Healthy" else "badge-pill-attention"
                perf_rows_html += f"""
                <tr>
                    <td style="color: #94A3B8; font-weight: 700; width: 24px;">{v['rank']}</td>
                    <td>
                        <div class="veh-thumb-wrap">
                            <img src="{c_img}" class="veh-thumb-img" alt="{v['model']}">
                            <span>{v['model']}</span>
                        </div>
                    </td>
                    <td>
                        <div class="health-bar-cell">
                            <span style="font-weight: 600; width: 32px;">{v['battery_health']}%</span>
                            <div class="table-prog-track">
                                <div class="table-prog-fill" style="width: {min(100.0, v['battery_health'])}%;"></div>
                            </div>
                        </div>
                    </td>
                    <td style="color: #CBD5E1; font-weight: 600; text-align: center;">{v['sessions']}</td>
                    <td style="text-align: right;">
                        <span class="badge-pill {badge_cls}">{v['status']}</span>
                    </td>
                </tr>
                """

            render_html(f"""
            <div class="lux-panel">
                <div class="lux-panel-header">
                    <div class="lux-panel-title">
                        <span style="color: #38BDF8;">🚗</span> Vehicle Performance
                    </div>
                    <a href="?nav=my_evs" target="_self" class="lux-panel-link">View All &rarr;</a>
                </div>
                <table class="veh-perf-table">
                    <thead>
                        <tr>
                            <th style="width: 24px;">#</th>
                            <th>Vehicle</th>
                            <th>Battery Health</th>
                            <th style="text-align: center;">Sessions</th>
                            <th style="text-align: right;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {perf_rows_html}
                    </tbody>
                </table>
            </div>
            """)
            st.caption("Click a vehicle to inspect full health & charging dossier:")
            v_quick_map = [("Tesla Model 3", 1), ("Tata Nexon EV", 6), ("MG ZS EV", 2), ("Hyundai Kona", 3)]
            vq1, vq2, vq3, vq4 = st.columns(4)
            for (col, (m_name, v_id)) in zip([vq1, vq2, vq3, vq4], v_quick_map):
                with col:
                    if st.button(m_name, key=f"btn_vp_quick_{v_id}", use_container_width=True):
                        show_vehicle_dialog(v_id)
            if st.button("View All Vehicles →", key="btn_vp_view_all_act", use_container_width=True):
                navigate_to("🚗 My EVs")

        # 5. RECENT CHARGING SESSIONS (LIVE REAL DATA FILTERED BY SELECTED DATES)
        render_html(f"""
        <div class="lux-panel" style="margin-top: 6px;">
            <div class="lux-panel-header">
                <div class="lux-panel-title">
                    <span style="color: #10B981;">⚡</span> Recent Charging Sessions
                    <span style="font-size: 0.78rem; color: #64748B; font-weight: 500; margin-left: 8px;">({start_d.strftime('%d %b')} – {end_d.strftime('%d %b %Y')})</span>
                </div>
                <a href="?nav=charging" target="_self" class="lux-panel-link">View All &rarr;</a>
            </div>
        </div>
        """)
        recent_s_df = sql_db.fetch_dataframe("""
            SELECT s.session_id, v.model AS vehicle_model, cs.station_name, s.start_time, 
                   s.energy_consumed, s.charging_cost, s.start_soc, s.end_soc
            FROM charging_sessions s
            JOIN vehicles v ON s.vehicle_id = v.vehicle_id
            JOIN charging_stations cs ON s.station_id = cs.station_id
            WHERE DATE(s.start_time) >= DATE(?) AND DATE(s.start_time) <= DATE(?)
            ORDER BY s.start_time DESC
            LIMIT 5;
        """, (start_str, end_str))

        if not recent_s_df.empty:
            recent_s_df["soc_gain"] = recent_s_df["end_soc"] - recent_s_df["start_soc"]
            st.dataframe(
                recent_s_df.rename(columns={
                    "session_id": "Session #",
                    "vehicle_model": "Vehicle",
                    "station_name": "Station",
                    "start_time": "Date & Time",
                    "energy_consumed": "Energy (kWh)",
                    "charging_cost": "Cost (₹)",
                    "soc_gain": "SOC Gain (%)"
                })[["Session #", "Vehicle", "Station", "Energy (kWh)", "Cost (₹)", "Date & Time", "SOC Gain (%)"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info(f"No charging sessions recorded between {start_str} and {end_str}.")

        if st.button("View All Charging Sessions →", key="btn_view_all_recent_act", use_container_width=True):
            navigate_to("⚡ Charging")

        # 6. BOTTOM SECTION: SMART INSIGHTS (ACTIONABLE)
        render_html(f"""
        <div>
            <div class="insights-section-title">
                <span style="color: #10B981;">💡</span> Smart Insights
            </div>
            <div class="smart-insights-grid">
                <div class="smart-insight-card">
                    <div class="insight-left">
                        <div class="insight-icon-box insight-icon-trophy">🏆</div>
                        <div>
                            <div class="insight-sub">Highest Battery Health</div>
                            <div class="insight-model">{insights['highest_health']['model']}</div>
                        </div>
                    </div>
                    <div class="insight-val-badge text-emerald">{insights['highest_health']['value']}% &gt;</div>
                </div>

                <div class="smart-insight-card">
                    <div class="insight-left">
                        <div class="insight-icon-box insight-icon-bolt">⚡</div>
                        <div>
                            <div class="insight-sub">Most Active Vehicle</div>
                            <div class="insight-model">{insights['most_charged']['model']}</div>
                        </div>
                    </div>
                    <div class="insight-val-badge text-sky">{insights['most_charged']['value']} sessions &gt;</div>
                </div>

                <div class="smart-insight-card">
                    <div class="insight-left">
                        <div class="insight-icon-box insight-icon-temp">🌡️</div>
                        <div>
                            <div class="insight-sub">Highest Temperature</div>
                            <div class="insight-model">{insights['highest_temp']['model']}</div>
                        </div>
                    </div>
                    <div class="insight-val-badge text-coral">{insights['highest_temp']['value']}°C &gt;</div>
                </div>

                <div class="smart-insight-card">
                    <div class="insight-left">
                        <div class="insight-icon-box insight-icon-cost">
                            <span style="font-weight: 700;">₹</span>
                        </div>
                        <div>
                            <div class="insight-sub">Highest Charging Cost</div>
                            <div class="insight-model">{insights['highest_cost']['model']}</div>
                        </div>
                    </div>
                    <div class="insight-val-badge text-sky">₹ {insights['highest_cost']['value']:,.0f} &gt;</div>
                </div>
            </div>
        </div>
        """)
        si1, si2, si3, si4 = st.columns(4)
        with si1:
            if st.button("Inspect Health 🏆", key="btn_si_1_act", use_container_width=True):
                navigate_to("🔋 Battery Health", selected_vehicle_id=6, selected_vehicle=6)
        with si2:
            if st.button("Inspect Activity ⚡", key="btn_si_2_act", use_container_width=True):
                navigate_to("⚡ Charging")
        with si3:
            if st.button("Inspect Temp 🌡️", key="btn_si_3_act", use_container_width=True):
                navigate_to("🔋 Battery Health", selected_vehicle_id=2, selected_vehicle=2)
        with si4:
            if st.button("Inspect Cost ₹", key="btn_si_4_act", use_container_width=True):
                navigate_to("📊 Insights", insights_subtab="Cost")
    except Exception as e:
        st.warning("⚠️ Unable to load this information.")



# =============================================================================
# PAGE 2: MY EVS
# =============================================================================
elif curr_page == "🚗 My EVs":
    render_html("""
    <div style="margin-bottom: 20px;">
        <h2 style="margin: 0; font-size: 1.6rem; font-weight: 800; color: #FFFFFF;">My EVs</h2>
        <div style="color: #64748B; font-size: 0.85rem; font-weight: 500;">Monitor fleet vehicle specifications, battery health, and logs</div>
    </div>
    """)

    vehicles_df = vehicle_service.get_all_vehicles()
    corr_df = analytics_service.get_battery_health_vs_charging_activity()
    health_map = {}
    sessions_map = {}
    if not corr_df.empty:
        for _, r in corr_df.iterrows():
            vid = int(r["vehicle_id"])
            health_map[vid] = r["battery_health"]
            sessions_map[vid] = r["total_sessions"]

    f_c1, f_c2 = st.columns([3, 1])
    with f_c1:
        search_kw = st.text_input("🔍 Search EV model or owner:", placeholder="e.g. Nexon, Tesla, Kona", label_visibility="collapsed")
    with f_c2:
        chem_filter = st.selectbox("Chemistry", ["All", "LFP (Lithium Iron Phosphate)", "NMC (Nickel Manganese Cobalt)", "Lithium-ion", "Blade LFP"], label_visibility="collapsed")

    filtered_df = vehicle_service.filter_vehicles(search_query=search_kw, battery_type=chem_filter)

    if not filtered_df.empty:
        cols = st.columns(3)
        for idx, (_, vrow) in enumerate(filtered_df.iterrows()):
            vid = int(vrow["vehicle_id"])
            v_health = health_map.get(vid, 92.0)
            v_sessions = sessions_map.get(vid, 0)
            cat = get_battery_health_category(v_health)

            with cols[idx % 3]:
                render_html(f"""
                <div class="veh-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div class="veh-card-title">{vrow['model']}</div>
                            <div class="veh-card-sub">Owner: {vrow['owner_name']}</div>
                        </div>
                        <span style="color: {cat['color']}; font-size: 0.75rem; font-weight: 700; background: rgba(0,0,0,0.3); padding: 3px 8px; border-radius: 4px; border: 1px solid {cat['color']}40;">
                            {cat['status']}
                        </span>
                    </div>
                    <div class="veh-card-stat">
                        <span>Battery Capacity</span>
                        <b>{vrow['battery_capacity']} kWh</b>
                    </div>
                    <div class="veh-card-stat">
                        <span>State of Health (SOH)</span>
                        <b style="color: {cat['color']};">{v_health}%</b>
                    </div>
                    <div class="veh-card-stat" style="border: none;">
                        <span>Charging Sessions</span>
                        <b>{v_sessions} logs</b>
                    </div>
                </div>
                """)
                if st.button(f"🔍 Inspect Dossier", key=f"btn_my_ev_inspect_{vid}", use_container_width=True):
                    show_vehicle_dialog(vid)

                with st.expander(f"View Specs & Activity: {vrow['model']}"):
                    dossier = vehicle_service.get_vehicle_full_dossier(vid)
                    st.write(f"**Year:** {vrow['manufacturing_year']} | **Chemistry:** {vrow['battery_type']}")
                    st.write(f"**Email:** {vrow['owner_email']}")
                    b_btn1, b_btn2 = st.columns(2)
                    with b_btn1:
                        if st.button("🔋 Battery Health", key=f"btn_card_bh_{vid}", use_container_width=True):
                            navigate_to("🔋 Battery Health", selected_vehicle_id=vid, selected_vehicle=vid)
                    with b_btn2:
                        if st.button("⚡ Session Logs", key=f"btn_card_cs_{vid}", use_container_width=True):
                            navigate_to("⚡ Charging")
                    s_df = dossier.get("sessions")
                    if s_df is not None and not s_df.empty:
                        st.dataframe(s_df[["session_id", "station_name", "start_time", "energy_consumed", "charging_cost"]].head(4), hide_index=True)
                    else:
                        st.caption("No charging sessions yet.")
    else:
        st.info("No vehicles match the search.")

    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander("⚙️ Manage Vehicles (Add, Edit, Delete)"):
        v_subtab1, v_subtab2 = st.tabs(["➕ Add New EV", "✏️ Edit / Delete EV"])

        with v_subtab1:
            users_list = vehicle_service.get_all_users()
            if users_list:
                with st.form("add_veh_form_clean"):
                    u_dict = {u["user_id"]: f"{u['name']} ({u['email']})" for u in users_list}
                    uid = st.selectbox("Owner", options=list(u_dict.keys()), format_func=lambda x: u_dict[x])
                    mod = st.text_input("Vehicle Model", placeholder="e.g. Tata Curvv EV")
                    cap = st.number_input("Battery Capacity (kWh)", 5.0, 250.0, 55.0, 0.5)
                    chem = st.selectbox("Battery Chemistry", ["LFP (Lithium Iron Phosphate)", "NMC (Nickel Manganese Cobalt)", "Lithium-ion", "Blade LFP"])
                    yr = st.number_input("Year", 2010, 2026, 2024, 1)

                    if st.form_submit_button("Register Vehicle"):
                        res = vehicle_service.add_vehicle(uid, mod, cap, chem, yr)
                        if res["success"]:
                            st.success(res["message"])
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(res["error"])

        with v_subtab2:
            if not vehicles_df.empty:
                sel_edit_id = st.selectbox("Select EV to Edit", options=vehicles_df["vehicle_id"].tolist(), format_func=lambda x: f"ID #{x} - {vehicles_df[vehicles_df['vehicle_id']==x]['model'].values[0]}")
                curr_v = vehicle_service.get_vehicle_by_id(sel_edit_id)
                if curr_v:
                    with st.form("edit_veh_clean"):
                        e_model = st.text_input("Model", value=curr_v["model"])
                        e_cap = st.number_input("Capacity (kWh)", 5.0, 250.0, float(curr_v["battery_capacity"]), 0.5)
                        if st.form_submit_button("Save Vehicle Changes"):
                            up_res = vehicle_service.update_vehicle(sel_edit_id, curr_v["user_id"], e_model, e_cap, curr_v["battery_type"], curr_v["manufacturing_year"])
                            if up_res["success"]:
                                st.success(up_res["message"])
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(up_res["error"])

                st.markdown("---")
                if st.button("🗑️ Delete Selected EV", type="primary"):
                    del_res = vehicle_service.delete_vehicle(sel_edit_id)
                    if del_res["success"]:
                        st.success(del_res["message"])
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(del_res["error"])


# =============================================================================
# PAGE 3: CHARGING
# =============================================================================
elif curr_page == "⚡ Charging":
    render_html("""
    <div style="margin-bottom: 20px;">
        <h2 style="margin: 0; font-size: 1.6rem; font-weight: 800; color: #FFFFFF;">Charging</h2>
        <div style="color: #64748B; font-size: 0.85rem; font-weight: 500;">Log sessions, inspect charging history, and evaluate station load</div>
    </div>
    """)

    c_tab1, c_tab2 = st.tabs(["Charging History", "New Session"])

    with c_tab1:
        all_sessions = charging_service.get_all_sessions()
        if not all_sessions.empty:
            f1, f2 = st.columns(2)
            with f1:
                v_opts = [0] + all_sessions["vehicle_id"].unique().tolist()
                v_sel = st.selectbox("Filter Vehicle", v_opts, format_func=lambda x: "All Vehicles" if x==0 else f"Vehicle #{x}")
            with f2:
                s_opts = [0] + all_sessions["station_id"].unique().tolist()
                s_sel = st.selectbox("Filter Station", s_opts, format_func=lambda x: "All Stations" if x==0 else f"Station #{x}")

            filt_sessions = charging_service.filter_sessions(
                vehicle_id=v_sel if v_sel != 0 else None,
                station_id=s_sel if s_sel != 0 else None
            )

            disp_df = filt_sessions.rename(columns={
                "session_id": "Session #",
                "vehicle_model": "Vehicle",
                "station_name": "Station",
                "energy_consumed": "Energy (kWh)",
                "duration_formatted": "Duration",
                "charging_cost": "Cost (₹)",
                "start_time": "Date",
                "start_soc": "Start SOC (%)",
                "end_soc": "End SOC (%)",
                "soc_increase": "SOC Gain (%)"
            })

            st.dataframe(
                disp_df[[
                    "Session #", "Vehicle", "Station", "Energy (kWh)", 
                    "Duration", "Cost (₹)", "Date", "Start SOC (%)", "End SOC (%)", "SOC Gain (%)"
                ]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No charging sessions found.")

    with c_tab2:
        st.markdown('<div class="lux-panel-title" style="margin-bottom: 12px;">Record a Charging Session</div>', unsafe_allow_html=True)
        vehicles = vehicle_service.get_all_vehicles()
        stations = charging_service.get_all_stations()

        if not vehicles.empty and not stations.empty:
            with st.form("new_session_form"):
                col_a, col_b = st.columns(2)
                with col_a:
                    v_dict = {r["vehicle_id"]: f"{r['model']} ({r['owner_name']})" for _, r in vehicles.iterrows()}
                    selected_v = st.selectbox("Vehicle", options=list(v_dict.keys()), format_func=lambda x: v_dict[x])
                    start_dt = st.datetime_input("Start Time", value=datetime.now() - timedelta(hours=1))

                with col_b:
                    st_dict = {r["station_id"]: f"{r['station_name']} ({r['power_rating']} kW)" for _, r in stations.iterrows()}
                    selected_st = st.selectbox("Station", options=list(st_dict.keys()), format_func=lambda x: st_dict[x])
                    end_dt = st.datetime_input("End Time", value=datetime.now())

                s_soc = st.slider("Start SOC (%)", 0.0, 95.0, 20.0, 1.0)
                e_soc = st.slider("End SOC (%)", float(s_soc), 100.0, 85.0, 1.0)

                v_cap = vehicles[vehicles["vehicle_id"] == selected_v]["battery_capacity"].values[0]
                est_kwh = round(((e_soc - s_soc) / 100.0) * v_cap * 1.08, 2)

                e_kwh = st.number_input("Energy Consumed (kWh)", 0.5, 250.0, est_kwh, 0.5)
                c_cost = st.number_input("Cost (₹)", 0.0, 10000.0, round(e_kwh * 18.0, 2), 10.0)

                sync_telemetry = st.checkbox("Auto-sync telemetry reading to MongoDB", value=True)

                if st.form_submit_button("⚡ Submit Session", use_container_width=True):
                    res = charging_service.create_session(
                        selected_v, selected_st, str(start_dt), str(end_dt),
                        e_kwh, c_cost, s_soc, e_soc, sync_telemetry
                    )
                    if res["success"]:
                        st.success(f"Session logged! Duration: {res['duration_formatted']} | SOC Gain: +{res['soc_gain']}%")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error(res["error"])

    with st.expander("📡 Station Infrastructure Directory"):
        st_df = charging_service.get_all_stations()
        st.dataframe(st_df[["station_id", "station_name", "location", "charger_type", "power_rating", "availability_status"]], use_container_width=True, hide_index=True)


# =============================================================================
# PAGE 4: BATTERY HEALTH
# =============================================================================
elif curr_page == "🔋 Battery Health":
    render_html("""
    <div style="margin-bottom: 20px;">
        <h2 style="margin: 0; font-size: 1.6rem; font-weight: 800; color: #FFFFFF;">Battery Health</h2>
        <div style="color: #64748B; font-size: 0.85rem; font-weight: 500;">Monitor battery condition, degradation curves, and cell telemetry</div>
    </div>
    """)

    vehicles_df = vehicle_service.get_all_vehicles()
    if not vehicles_df.empty:
        v_dict = {r["vehicle_id"]: f"{r['model']} ({r['battery_capacity']} kWh)" for _, r in vehicles_df.iterrows()}
        v_keys = list(v_dict.keys())
        default_vid = st.session_state.get("selected_vehicle_id", v_keys[0])
        default_idx = v_keys.index(default_vid) if default_vid in v_keys else 0
        selected_vid = st.selectbox("Select EV", options=v_keys, index=default_idx, format_func=lambda x: v_dict[x], key="bh_ev_selectbox")
        st.session_state["selected_vehicle_id"] = selected_vid
        st.session_state["selected_vehicle"] = selected_vid

        diag = battery_service.analyze_battery_diagnostics(selected_vid)
        status = diag["status"]
        category = status["category"]

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Battery Health", f"{status['battery_health']}%")
        m2.metric("SOC", f"{status['soc']}%")
        m3.metric("Temperature", f"{status['temperature']}°C")
        m4.metric("Voltage", f"{status['voltage']} V")
        m5.metric("Current", f"{status['current']} A")
        m6.metric("Cycle Count", f"{status['cycle_count']}")

        st.markdown("<br>", unsafe_allow_html=True)

        warnings = diag["warnings"]
        if warnings:
            for w in warnings:
                w_class = "alert-critical" if w["severity"] == "CRITICAL" else ("alert-warning" if w["severity"] == "WARNING" else "alert-normal")
                w_icon = "⚠️" if w["severity"] in ["CRITICAL", "WARNING"] else "ℹ️"
                render_html(f"""
                <div class="alert-banner {w_class}">
                    <span>{w_icon}</span>
                    <div>
                        <b>{w['title']}</b>: {w['message']}
                    </div>
                </div>
                """)
        else:
            render_html("""
            <div class="alert-banner alert-normal">
                <span>✓</span>
                <div><b>Battery operating normally</b>: All cell telemetry parameters are within optimal manufacturer limits.</div>
            </div>
            """)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown('<div class="lux-panel-title" style="margin-bottom: 12px;">Battery Health Trend</div>', unsafe_allow_html=True)
        telemetry_df = battery_service.get_telemetry_dataframe(selected_vid)

        if not telemetry_df.empty:
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=telemetry_df["timestamp"],
                y=telemetry_df["battery_health"],
                mode="lines+markers",
                name="SOH (%)",
                line=dict(color="#00D26A", width=3),
                marker=dict(size=7, color="#00D26A")
            ))
            fig_trend.add_hline(y=80.0, line_dash="dash", line_color="#F59E0B", annotation_text="80% SOH Warranty Limit")
            theme = get_plotly_theme()
            fig_trend.update_layout(theme["layout"])
            fig_trend.update_layout(height=300, yaxis_range=[max(60, telemetry_df["battery_health"].min() - 4), 101])
            st.plotly_chart(fig_trend, use_container_width=True)

            st.markdown('<div class="lux-panel-title" style="margin-bottom: 12px;">Battery Telemetry (MongoDB)</div>', unsafe_allow_html=True)
            st.dataframe(
                telemetry_df[["timestamp", "soc", "temperature", "voltage", "current", "battery_health", "cycle_count"]],
                use_container_width=True,
                hide_index=True
            )

            with st.expander("➕ Log Real-Time Telemetry Reading"):
                with st.form("add_tel_clean"):
                    tc1, tc2, tc3 = st.columns(3)
                    with tc1:
                        new_soc = st.slider("SOC (%)", 0.0, 100.0, float(status["soc"]), 0.5)
                        new_temp = st.number_input("Temp (°C)", -10.0, 80.0, float(status["temperature"]), 0.5)
                    with tc2:
                        new_volt = st.number_input("Voltage (V)", 100.0, 900.0, float(status["voltage"]), 1.0)
                        new_curr = st.number_input("Current (A)", -50.0, 200.0, float(status["current"]), 1.0)
                    with tc3:
                        new_soh = st.slider("SOH (%)", 50.0, 100.0, float(status["battery_health"]), 0.1)
                        new_cyc = st.number_input("Cycles", 0, 5000, int(status["cycle_count"]) + 1, 1)

                    if st.form_submit_button("Persist Reading"):
                        t_res = battery_service.record_telemetry(selected_vid, new_soc, new_temp, new_volt, new_curr, new_soh, new_cyc)
                        if t_res["success"]:
                            st.success(t_res["message"])
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(t_res["error"])


# =============================================================================
# PAGE 5: INSIGHTS
# =============================================================================
elif curr_page == "📊 Insights":
    render_html("""
    <div style="margin-bottom: 20px;">
        <h2 style="margin: 0; font-size: 1.6rem; font-weight: 800; color: #FFFFFF;">Insights</h2>
        <div style="color: #64748B; font-size: 0.85rem; font-weight: 500;">Fleet intelligence, efficiency analysis, and degradation trends</div>
    </div>
    """)

    insight_categories = ["Fleet", "Charging", "Battery", "Cost"]

    # 1. Apply any pending external navigation target BEFORE widget instantiation
    if "insights_subtab_target" in st.session_state:
        target = st.session_state.pop("insights_subtab_target")
        if target in insight_categories:
            st.session_state["pills_insights_subtab"] = target
            st.session_state["insights_subtab"] = target

    # 2. Ensure initial state exists
    if "insights_subtab" not in st.session_state:
        st.session_state["insights_subtab"] = "Fleet"
    if "pills_insights_subtab" not in st.session_state:
        st.session_state["pills_insights_subtab"] = st.session_state["insights_subtab"]

    def on_subtab_change():
        chosen = st.session_state.get("pills_insights_subtab")
        if chosen in insight_categories:
            st.session_state["insights_subtab"] = chosen

    sel_subtab = st.pills(
        "Analysis Category",
        insight_categories,
        key="pills_insights_subtab",
        on_change=on_subtab_change
    )
    if not sel_subtab:
        sel_subtab = st.session_state.get("insights_subtab", "Fleet")
        st.session_state["pills_insights_subtab"] = sel_subtab
    else:
        st.session_state["insights_subtab"] = sel_subtab

    active_subtab = sel_subtab
    theme = get_plotly_theme()

    if active_subtab == "Fleet":
        st.markdown('<div class="lux-panel-title" style="margin-bottom: 12px;">Fleet Energy Performance</div>', unsafe_allow_html=True)
        veh_energy_df = analytics_service.get_energy_cost_per_vehicle()
        if not veh_energy_df.empty:
            fig_fleet = px.bar(
                veh_energy_df,
                x="model",
                y="total_energy_kwh",
                color="battery_type",
                title="Total Energy (kWh) Consumed by Vehicle Model",
                color_discrete_sequence=["#00E5FF", "#00D26A", "#38BDF8"]
            )
            fig_fleet.update_layout(theme["layout"])
            fig_fleet.update_layout(height=340)
            st.plotly_chart(fig_fleet, use_container_width=True)

    elif active_subtab == "Charging":
        st.markdown('<div class="lux-panel-title" style="margin-bottom: 12px;">Charging Efficiency & Station Distribution</div>', unsafe_allow_html=True)
        st_df = analytics_service.get_sessions_per_station()
        if not st_df.empty:
            c1, c2 = st.columns(2)
            with c1:
                fig_st1 = px.bar(
                    st_df,
                    x="station_name",
                    y="sessions_count",
                    title="Sessions Hosted per Station",
                    color_discrete_sequence=["#00E5FF"]
                )
                fig_st1.update_layout(theme["layout"])
                fig_st1.update_layout(height=320)
                st.plotly_chart(fig_st1, use_container_width=True)
            with c2:
                fig_st2 = px.pie(
                    st_df,
                    values="total_energy_kwh",
                    names="station_name",
                    title="Energy Share (kWh) by Station",
                    hole=0.45
                )
                fig_st2.update_layout(theme["layout"])
                fig_st2.update_layout(height=320)
                st.plotly_chart(fig_st2, use_container_width=True)

    elif active_subtab == "Battery":
        st.markdown('<div class="lux-panel-title" style="margin-bottom: 12px;">Battery Trends & Fast-Charging Impact</div>', unsafe_allow_html=True)
        corr_df = analytics_service.get_battery_health_vs_charging_activity()
        if not corr_df.empty:
            c1, c2 = st.columns(2)
            with c1:
                fig_c1 = px.scatter(
                    corr_df,
                    x="fast_charge_sessions",
                    y="battery_health",
                    color="battery_type",
                    size="total_energy",
                    hover_name="model",
                    title="Fast Charge Sessions vs Battery SOH (%)"
                )
                fig_c1.update_layout(theme["layout"])
                fig_c1.update_layout(height=340)
                st.plotly_chart(fig_c1, use_container_width=True)
            with c2:
                fig_c2 = px.scatter(
                    corr_df,
                    x="avg_temperature",
                    y="battery_health",
                    color="battery_type",
                    hover_name="model",
                    title="Operating Temp (°C) vs Battery SOH (%)"
                )
                fig_c2.update_layout(theme["layout"])
                fig_c2.update_layout(height=340)
                st.plotly_chart(fig_c2, use_container_width=True)

    elif active_subtab == "Cost":
        st.markdown('<div class="lux-panel-title" style="margin-bottom: 12px;">Cost Analysis & Tariff Breakdown</div>', unsafe_allow_html=True)
        ch_df = analytics_service.get_charger_type_breakdown()
        if not ch_df.empty:
            c1, c2 = st.columns(2)
            with c1:
                fig_ch1 = px.pie(
                    ch_df,
                    values="total_revenue",
                    names="charger_type",
                    title="Revenue by Charger Technology (₹)",
                    hole=0.45
                )
                fig_ch1.update_layout(theme["layout"])
                fig_ch1.update_layout(height=320)
                st.plotly_chart(fig_ch1, use_container_width=True)
            with c2:
                cost_v_df = analytics_service.get_energy_cost_per_vehicle()
                fig_ch2 = px.bar(
                    cost_v_df,
                    x="model",
                    y="total_cost_inr",
                    title="Expenditure per Vehicle (₹)",
                    color_discrete_sequence=["#10B981"]
                )
                fig_ch2.update_layout(theme["layout"])
                fig_ch2.update_layout(height=320)
                st.plotly_chart(fig_ch2, use_container_width=True)


# =============================================================================
# PAGE 6: DATA
# =============================================================================
elif curr_page == "🗄️ Data":
    render_html("""
    <div style="margin-bottom: 20px;">
        <h2 style="margin: 0; font-size: 1.6rem; font-weight: 800; color: #FFFFFF;">Data</h2>
        <div style="color: #64748B; font-size: 0.85rem; font-weight: 500;">Relational SQL tables, NoSQL collections, and query evaluation</div>
    </div>
    """)

    d_tab1, d_tab2, d_tab3 = st.tabs(["🗃️ SQL Database (SQLite)", "🍃 MongoDB (NoSQL Telemetry)", "⚙️ Maintenance & Seed Tools"])

    with d_tab1:
        st.markdown("### Relational SQL Database (SQLite)")
        sql_sub1, sql_sub2, sql_sub3, sql_sub4 = st.tabs(["🚗 Vehicles", "⚡ Charging Sessions", "📡 Stations", "👤 Users"])
        
        with sql_sub1:
            st.markdown("#### Table: `vehicles`")
            v_all = sql_db.fetch_dataframe("SELECT * FROM vehicles;")
            st.dataframe(v_all, use_container_width=True, hide_index=True)
            st.caption(f"Total registered vehicles: {len(v_all)}")

        with sql_sub2:
            st.markdown("#### Table: `charging_sessions`")
            s_all = sql_db.fetch_dataframe("SELECT * FROM charging_sessions ORDER BY start_time DESC;")
            st.dataframe(s_all, use_container_width=True, hide_index=True)
            st.caption(f"Total recorded sessions: {len(s_all)}")

        with sql_sub3:
            st.markdown("#### Table: `charging_stations`")
            st_all = sql_db.fetch_dataframe("SELECT * FROM charging_stations;")
            st.dataframe(st_all, use_container_width=True, hide_index=True)
            st.caption(f"Total deployed stations: {len(st_all)}")

        with sql_sub4:
            st.markdown("#### Table: `users`")
            u_all = sql_db.fetch_dataframe("SELECT user_id, name, email, phone, created_at FROM users;")
            st.dataframe(u_all, use_container_width=True, hide_index=True)
            st.caption(f"Total registered fleet users: {len(u_all)}")

        with st.expander("🔍 Predefined Advanced SQL Queries & Execution"):
            advanced_queries = sql_db.get_advanced_queries()
            sel_q = st.selectbox("Select SQL Query:", list(advanced_queries.keys()), format_func=lambda x: f"{x}: {advanced_queries[x]['title']}")
            q_info = advanced_queries[sel_q]
            st.markdown(f'<div class="clean-code">{q_info["sql"]}</div>', unsafe_allow_html=True)
            if st.button(f"Execute {sel_q}", key="btn_exec_adv_sql"):
                res_df = sql_db.execute_advanced_query(sel_q)
                st.dataframe(res_df, use_container_width=True, hide_index=True)

    with d_tab2:
        st.markdown("### MongoDB Battery Telemetry (`battery_telemetry`)")
        status_info = mongo_db.get_status_info()
        st.caption(f"Mode: `{status_info['mode']}` | Collection: `battery_telemetry` | Stored Documents: **{status_info['document_count']}**")

        v_list = vehicle_service.get_all_vehicles()
        if not v_list.empty:
            v_choice = [0] + v_list["vehicle_id"].tolist()
            filter_v = st.selectbox(
                "Filter Telemetry by EV", 
                v_choice, 
                format_func=lambda x: "All Fleet Telemetry (Latest 100)" if x==0 else f"Vehicle #{x} ({v_list[v_list['vehicle_id']==x]['model'].values[0]})"
            )
            if filter_v == 0:
                tel_docs = mongo_db.get_all_telemetry(limit=100)
            else:
                tel_docs = mongo_db.get_vehicle_telemetry(filter_v, limit=100)
            if tel_docs:
                clean_docs = []
                for d in tel_docs:
                    cd = dict(d)
                    if "_id" in cd:
                        cd["_id"] = str(cd["_id"])
                    clean_docs.append(cd)
                st.dataframe(pd.DataFrame(clean_docs), use_container_width=True, hide_index=True)
            else:
                st.info("No telemetry records found for this vehicle.")

        with st.expander("⚡ Predefined MongoDB Aggregation Pipelines"):
            pipelines = mongo_db.get_aggregation_pipelines()
            sel_p = st.selectbox("Select Aggregation Pipeline:", list(pipelines.keys()), format_func=lambda x: f"{x}: {pipelines[x]['title']}")
            p_info = pipelines[sel_p]
            st.markdown(f'<div class="clean-code">{json.dumps(p_info["pipeline"], indent=2)}</div>', unsafe_allow_html=True)
            if st.button(f"Execute {sel_p}", key="btn_exec_mongo_agg"):
                res_agg = mongo_db.run_aggregation(p_info["pipeline"])
                st.dataframe(pd.DataFrame(res_agg), use_container_width=True, hide_index=True)

    with d_tab3:
        st.markdown("### Database Maintenance & Diagnostics")
        m1, m2 = st.columns(2)
        with m1:
            if st.button("🌱 Reload Clean Sample Data", use_container_width=True, key="btn_maint_reload"):
                load_sample_data(force=True)
                st.success("Sample data reloaded successfully.")
                time.sleep(1)
                st.rerun()
        with m2:
            confirm = st.checkbox("Confirm database reset", key="chk_db_reset")
            if st.button("🗑️ Reset All Databases", type="primary", disabled=not confirm, use_container_width=True, key="btn_maint_reset"):
                sql_db.reset_db()
                mongo_db.clear_telemetry()
                st.warning("All data cleared.")
                time.sleep(1)
                st.rerun()
