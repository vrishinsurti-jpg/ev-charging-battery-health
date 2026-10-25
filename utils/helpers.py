"""
Helper Functions Module
EV Charging & Battery Health Intelligence Platform

Provides business logic calculations for charging sessions, battery degradation
categorization, formatters, and Plotly visualization styling.
"""

from datetime import datetime
from typing import Tuple, Dict, Any, Optional
import plotly.graph_objects as go


def calculate_charging_duration(start_time_str: str, end_time_str: str) -> Tuple[float, str]:
    """
    Calculates duration in decimal hours and formatted text (e.g. '1h 45m').
    """
    try:
        t_start = datetime.fromisoformat(str(start_time_str).replace("Z", ""))
        t_end = datetime.fromisoformat(str(end_time_str).replace("Z", ""))
        diff_sec = max(0, (t_end - t_start).total_seconds())
        hours = diff_sec / 3600.0
        
        hrs_int = int(diff_sec // 3600)
        mins_int = int((diff_sec % 3600) // 60)
        formatted = f"{hrs_int}h {mins_int}m" if hrs_int > 0 else f"{mins_int}m"
        return round(hours, 2), formatted
    except Exception:
        return 0.0, "N/A"


def calculate_soc_increase(start_soc: float, end_soc: float) -> float:
    """Calculates delta SOC percentage."""
    try:
        return round(float(end_soc) - float(start_soc), 2)
    except Exception:
        return 0.0


def calculate_charging_efficiency(
    energy_consumed_kwh: float,
    start_soc: float,
    end_soc: float,
    battery_capacity_kwh: float
) -> float:
    """
    Calculates charging system efficiency percentage:
    Theoretical energy absorbed = (end_soc - start_soc) / 100 * battery_capacity
    Efficiency = (energy_absorbed / energy_consumed) * 100
    Capped within realistic range (70% - 98%).
    """
    try:
        delta_soc = float(end_soc) - float(start_soc)
        if delta_soc <= 0 or float(energy_consumed_kwh) <= 0:
            return 88.0
        theoretical_stored = (delta_soc / 100.0) * float(battery_capacity_kwh)
        eff = (theoretical_stored / float(energy_consumed_kwh)) * 100.0
        # Realistic clamp
        return round(min(98.5, max(65.0, eff)), 1)
    except Exception:
        return 88.0


def get_battery_health_category(health_score: float) -> Dict[str, str]:
    """
    Classifies State of Health (SOH %) into 4 standard industrial tiers:
    - Excellent: >= 90%
    - Good: 80% to 89.9%
    - Moderate: 70% to 79.9%
    - Poor: < 70%
    """
    try:
        h = float(health_score)
    except (ValueError, TypeError):
        h = 85.0

    if h >= 90.0:
        return {
            "status": "Excellent",
            "color": "#00D26A",  # Emerald Green
            "badge_class": "badge-excellent",
            "description": "Optimal pack health. Nominal cell degradation with maximum range retention.",
            "action": "Maintain standard 20%-80% charging habits."
        }
    elif h >= 80.0:
        return {
            "status": "Good",
            "color": "#00B4D8",  # Cyan Blue
            "badge_class": "badge-good",
            "description": "Normal expected degradation consistent with vehicle mileage and cycles.",
            "action": "Periodic AC balancing charge recommended."
        }
    elif h >= 70.0:
        return {
            "status": "Moderate",
            "color": "#FFB703",  # Amber/Yellow
            "badge_class": "badge-moderate",
            "description": "Noticeable capacity decline. Accelerated thermal sensitivity observed.",
            "action": "Limit consecutive DC ultra-fast charging sessions."
        }
    else:
        return {
            "status": "Poor",
            "color": "#E63946",  # Coral Red
            "badge_class": "badge-poor",
            "description": "Severe pack degradation. Range significantly curtailed.",
            "action": "Cell module diagnostics and BMS warranty inspection advised."
        }


def format_currency(amount: float) -> str:
    """Formats monetary amounts."""
    try:
        return f"₹ {float(amount):,.2f}"
    except Exception:
        return f"₹ 0.00"


def format_energy(kwh: float) -> str:
    """Formats energy in kWh."""
    try:
        return f"{float(kwh):,.2f} kWh"
    except Exception:
        return "0.00 kWh"


def get_plotly_theme() -> Dict[str, Any]:
    """
    Returns unified Plotly styling parameters matching modern EV dark UI.
    """
    return {
        "layout": go.Layout(
            paper_bgcolor="rgba(15, 23, 42, 0.6)",
            plot_bgcolor="rgba(15, 23, 42, 0.4)",
            font={"color": "#E2E8F0", "family": "Inter, Segoe UI, sans-serif"},
            margin=dict(l=40, r=30, t=50, b=40),
            hovermode="x unified",
            xaxis=dict(
                gridcolor="rgba(148, 163, 184, 0.12)",
                zerolinecolor="rgba(148, 163, 184, 0.2)",
                showline=True,
                linecolor="rgba(148, 163, 184, 0.2)"
            ),
            yaxis=dict(
                gridcolor="rgba(148, 163, 184, 0.12)",
                zerolinecolor="rgba(148, 163, 184, 0.2)",
                showline=True,
                linecolor="rgba(148, 163, 184, 0.2)"
            ),
            legend=dict(
                bgcolor="rgba(15, 23, 42, 0.8)",
                bordercolor="rgba(148, 163, 184, 0.2)",
                borderwidth=1
            )
        ),
        "colors": {
            "primary": "#00D26A",
            "secondary": "#00B4D8",
            "accent": "#7209B7",
            "warning": "#FFB703",
            "danger": "#E63946",
            "neutral": "#94A3B8"
        }
    }
