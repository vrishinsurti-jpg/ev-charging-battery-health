"""
Battery Health Service Module
EV Charging & Battery Health Intelligence Platform

Manages battery telemetry analytics, State of Health (SOH) diagnostics,
thermal monitoring, degradation modeling, and intelligent warning systems.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from database.mongo_database import get_mongo_db
from database.sql_database import get_sql_db
from utils.validation import validate_telemetry_data
from utils.helpers import get_battery_health_category


class BatteryService:
    """Provides battery analytics, diagnostic rules, and telemetry persistence."""

    def __init__(self):
        self.mongo_db = get_mongo_db()
        self.sql_db = get_sql_db()

    def get_latest_battery_status(self, vehicle_id: int) -> Dict[str, Any]:
        """
        Retrieves the latest telemetry reading for a vehicle and evaluates
        its health tier, thermal safety, and operating parameters.
        """
        latest = self.mongo_db.get_latest_telemetry(vehicle_id)
        if not latest:
            # Fallback default values
            return {
                "has_data": False,
                "vehicle_id": vehicle_id,
                "battery_health": 95.0,
                "category": get_battery_health_category(95.0),
                "temperature": 28.0,
                "soc": 65.0,
                "voltage": 395.0,
                "current": 12.0,
                "cycle_count": 50,
                "internal_resistance_mohm": 20.0,
                "timestamp": "N/A"
            }

        soh = latest.get("battery_health", 90.0)
        category = get_battery_health_category(soh)

        return {
            "has_data": True,
            "vehicle_id": vehicle_id,
            "battery_health": round(soh, 1),
            "category": category,
            "temperature": round(latest.get("temperature", 28.0), 1),
            "soc": round(latest.get("soc", 50.0), 1),
            "voltage": round(latest.get("voltage", 390.0), 1),
            "current": round(latest.get("current", 0.0), 1),
            "cycle_count": int(latest.get("cycle_count", 0)),
            "internal_resistance_mohm": round(latest.get("internal_resistance_mohm", 21.0), 2),
            "timestamp": latest.get("timestamp", "N/A")
        }

    def get_telemetry_dataframe(self, vehicle_id: int, limit: int = 100) -> pd.DataFrame:
        """Retrieves chronological telemetry logs for a vehicle as a DataFrame."""
        records = self.mongo_db.get_vehicle_telemetry(vehicle_id, limit=limit)
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.sort_values("timestamp", ascending=True)
        return df

    def analyze_battery_diagnostics(self, vehicle_id: int) -> Dict[str, Any]:
        """
        Analyzes historical telemetry to generate statistical summaries
        and evaluate intelligent warning triggers:
        - Low SOH alert
        - High temperature alert
        - Rapid degradation alert
        - Stress charging pattern alert
        """
        df = self.get_telemetry_dataframe(vehicle_id, limit=100)
        status = self.get_latest_battery_status(vehicle_id)

        if df.empty:
            return {
                "status": status,
                "warnings": [],
                "stats": {
                    "avg_temp": 28.0,
                    "max_temp": 32.0,
                    "avg_soc": 60.0,
                    "net_degradation": 0.0,
                    "data_points": 0
                }
            }

        avg_temp = round(df["temperature"].mean(), 1)
        max_temp = round(df["temperature"].max(), 1)
        avg_soc = round(df["soc"].mean(), 1)
        avg_health = round(df["battery_health"].mean(), 2)

        initial_health = df["battery_health"].iloc[0]
        latest_health = df["battery_health"].iloc[-1]
        net_degradation = round(initial_health - latest_health, 2)

        warnings = []

        # Rule 1: Low Battery Health Warning (< 75% critical, < 80% advisory)
        if latest_health < 75.0:
            warnings.append({
                "severity": "CRITICAL",
                "title": "Low Battery State of Health (< 75%)",
                "message": f"Pack health has degraded to {latest_health}%. Usable EV driving range is substantially limited. Recommend professional diagnostic testing and module balancing."
            })
        elif latest_health < 82.0:
            warnings.append({
                "severity": "WARNING",
                "title": "Moderate Battery Degradation Alert (< 82%)",
                "message": f"Current battery health is {latest_health}%. Approaching end-of-warranty threshold. Recommended to minimize high-rate fast charging."
            })

        # Rule 2: High Operating Temperature Alert (> 40°C)
        if max_temp >= 42.0:
            warnings.append({
                "severity": "CRITICAL",
                "title": f"Unusually High Cell Temperature Detected (Peak {max_temp}°C)",
                "message": f"Peak battery temperature reached {max_temp}°C (threshold: 40°C). Prolonged operation at elevated temperatures accelerates solid electrolyte interphase (SEI) growth and thermal stress."
            })
        elif avg_temp >= 36.0:
            warnings.append({
                "severity": "WARNING",
                "title": f"Elevated Average Thermal Profile ({avg_temp}°C)",
                "message": f"Average operating temperature ({avg_temp}°C) is above optimal 25°C-30°C range. Verify BMS coolant flow and ambient conditions."
            })

        # Rule 3: Rapid Degradation Rate
        if len(df) >= 4 and net_degradation > 4.0:
            warnings.append({
                "severity": "WARNING",
                "title": f"Accelerated Capacity Loss Detected (-{net_degradation}% SOH)",
                "message": f"State of Health declined by {net_degradation}% over {len(df)} logged cycles, which is higher than the standard nominal degradation curve (~1.5% per annum)."
            })

        # Rule 4: Potential Battery Stress Charging Pattern
        # Check if frequent deep discharges (< 15% SOC) or consecutive high-temp fast charges
        low_soc_events = len(df[df["soc"] < 15.0])
        high_temp_charge_events = len(df[(df["temperature"] > 38.0) & (df["current"] > 40.0)])

        if high_temp_charge_events >= 2:
            warnings.append({
                "severity": "INFO",
                "title": "Frequent High-Rate Fast Charging Under Thermal Load",
                "message": f"Detected {high_temp_charge_events} charging events where battery was fast-charged above 38°C. Consider pre-conditioning battery before DC fast charge sessions."
            })
        elif low_soc_events >= 3:
            warnings.append({
                "severity": "INFO",
                "title": "Frequent Deep Discharge Cycling",
                "message": f"Detected {low_soc_events} cycles discharging below 15% SOC. Maintaining battery state above 20% prolongs cell life."
            })

        return {
            "status": status,
            "warnings": warnings,
            "stats": {
                "avg_temp": avg_temp,
                "max_temp": max_temp,
                "avg_soc": avg_soc,
                "avg_health": avg_health,
                "initial_health": initial_health,
                "latest_health": latest_health,
                "net_degradation": net_degradation,
                "data_points": len(df)
            }
        }

    def record_telemetry(
        self,
        vehicle_id: int,
        soc: float,
        temperature: float,
        voltage: float,
        current: float,
        battery_health: float,
        cycle_count: int
    ) -> Dict[str, Any]:
        """Validates and persists a new battery telemetry document into MongoDB."""
        is_valid, err = validate_telemetry_data(
            vehicle_id, soc, temperature, voltage, current, battery_health, cycle_count
        )
        if not is_valid:
            return {"success": False, "error": err}

        try:
            doc_id = self.mongo_db.insert_telemetry({
                "vehicle_id": int(vehicle_id),
                "soc": float(soc),
                "temperature": float(temperature),
                "voltage": float(voltage),
                "current": float(current),
                "battery_health": float(battery_health),
                "cycle_count": int(cycle_count)
            })
            return {"success": True, "id": doc_id, "message": "Telemetry point logged into NoSQL database successfully!"}
        except Exception as e:
            return {"success": False, "error": f"Failed to log telemetry: {str(e)}"}
