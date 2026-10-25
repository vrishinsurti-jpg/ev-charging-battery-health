"""
Charging Service Module
EV Charging & Battery Health Intelligence Platform

Manages charging stations and charging sessions. Enforces relational integrity,
performs automatic metric derivations (duration, SOC delta, charging speed, efficiency),
and supports multi-attribute filtering.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from database.sql_database import get_sql_db
from database.mongo_database import get_mongo_db
from utils.validation import validate_station_data, validate_session_data
from utils.helpers import calculate_charging_duration, calculate_soc_increase, calculate_charging_efficiency


class ChargingService:
    """Business operations for charging infrastructure and charging sessions."""

    def __init__(self):
        self.sql_db = get_sql_db()
        self.mongo_db = get_mongo_db()

    # =========================================================================
    # CHARGING STATIONS CRUD
    # =========================================================================
    def get_all_stations(self) -> pd.DataFrame:
        """Retrieves all registered charging stations with live session counts."""
        query = """
        SELECT 
            cs.station_id,
            cs.station_name,
            cs.location,
            cs.charger_type,
            cs.power_rating,
            cs.availability_status,
            COUNT(s.session_id) AS total_sessions_hosted,
            ROUND(COALESCE(SUM(s.energy_consumed), 0), 2) AS total_energy_delivered,
            ROUND(COALESCE(SUM(s.charging_cost), 0), 2) AS total_revenue
        FROM charging_stations cs
        LEFT JOIN charging_sessions s ON cs.station_id = s.station_id
        GROUP BY cs.station_id, cs.station_name, cs.location, cs.charger_type, cs.power_rating, cs.availability_status
        ORDER BY cs.station_id ASC;
        """
        return self.sql_db.fetch_dataframe(query)

    def get_station_by_id(self, station_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single charging station by ID."""
        return self.sql_db.fetch_one(
            "SELECT * FROM charging_stations WHERE station_id = ?;",
            (int(station_id),)
        )

    def add_station(
        self,
        station_name: str,
        location: str,
        charger_type: str,
        power_rating: float,
        availability_status: str = "Available"
    ) -> Dict[str, Any]:
        """Validates and registers a new charging station."""
        is_valid, err = validate_station_data(
            station_name, location, charger_type, power_rating, availability_status
        )
        if not is_valid:
            return {"success": False, "error": err}

        try:
            query = """
            INSERT INTO charging_stations (station_name, location, charger_type, power_rating, availability_status)
            VALUES (?, ?, ?, ?, ?);
            """
            _, new_id = self.sql_db.execute_query(
                query,
                (station_name.strip(), location.strip(), charger_type.strip(), float(power_rating), availability_status)
            )
            return {"success": True, "station_id": new_id, "message": f"Station '{station_name}' registered successfully!"}
        except Exception as e:
            return {"success": False, "error": f"Database insertion failed: {str(e)}"}

    def update_station(
        self,
        station_id: int,
        station_name: str,
        location: str,
        charger_type: str,
        power_rating: float,
        availability_status: str
    ) -> Dict[str, Any]:
        """Validates and updates charging station information."""
        is_valid, err = validate_station_data(
            station_name, location, charger_type, power_rating, availability_status
        )
        if not is_valid:
            return {"success": False, "error": err}

        try:
            query = """
            UPDATE charging_stations
            SET station_name = ?, location = ?, charger_type = ?, power_rating = ?, availability_status = ?
            WHERE station_id = ?;
            """
            rows, _ = self.sql_db.execute_query(
                query,
                (station_name.strip(), location.strip(), charger_type.strip(), float(power_rating), availability_status, int(station_id))
            )
            if rows == 0:
                return {"success": False, "error": f"Station ID {station_id} not found."}
            return {"success": True, "message": f"Station '{station_name}' updated successfully!"}
        except Exception as e:
            return {"success": False, "error": f"Database update failed: {str(e)}"}

    def delete_station(self, station_id: int) -> Dict[str, Any]:
        """Deletes a charging station if it has no associated sessions (RESTRICT constraint)."""
        # Check sessions
        session_count = self.sql_db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM charging_sessions WHERE station_id = ?;",
            (int(station_id),)
        )
        if session_count and session_count["cnt"] > 0:
            return {
                "success": False,
                "error": f"Cannot delete station #{station_id}: It has {session_count['cnt']} associated charging session records (Relational Integrity constraint)."
            }

        try:
            rows, _ = self.sql_db.execute_query("DELETE FROM charging_stations WHERE station_id = ?;", (int(station_id),))
            if rows == 0:
                return {"success": False, "error": f"Station #{station_id} not found."}
            return {"success": True, "message": f"Station #{station_id} deleted successfully."}
        except Exception as e:
            return {"success": False, "error": f"Deletion failed: {str(e)}"}

    # =========================================================================
    # CHARGING SESSIONS CRUD & DERIVATIONS
    # =========================================================================
    def get_all_sessions(self) -> pd.DataFrame:
        """Retrieves all charging sessions joined with vehicle and station details."""
        query = """
        SELECT 
            s.session_id,
            v.model AS vehicle_model,
            v.battery_capacity,
            v.vehicle_id,
            u.name AS owner_name,
            cs.station_name,
            cs.charger_type,
            cs.power_rating AS station_power,
            s.station_id,
            s.start_time,
            s.end_time,
            s.energy_consumed,
            s.charging_cost,
            s.start_soc,
            s.end_soc,
            ROUND(s.end_soc - s.start_soc, 2) AS soc_increase
        FROM charging_sessions s
        INNER JOIN vehicles v ON s.vehicle_id = v.vehicle_id
        INNER JOIN users u ON v.user_id = u.user_id
        INNER JOIN charging_stations cs ON s.station_id = cs.station_id
        ORDER BY s.start_time DESC;
        """
        df = self.sql_db.fetch_dataframe(query)
        if not df.empty:
            # Derive duration string & efficiency
            durations = []
            dur_hours = []
            efficiencies = []
            for _, row in df.iterrows():
                h, s_str = calculate_charging_duration(row["start_time"], row["end_time"])
                durations.append(s_str)
                dur_hours.append(h)
                eff = calculate_charging_efficiency(
                    row["energy_consumed"], row["start_soc"], row["end_soc"], row["battery_capacity"]
                )
                efficiencies.append(eff)
            df["duration_formatted"] = durations
            df["duration_hours"] = dur_hours
            df["efficiency_pct"] = efficiencies
        return df

    def get_session_by_id(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single session record."""
        return self.sql_db.fetch_one("SELECT * FROM charging_sessions WHERE session_id = ?;", (int(session_id),))

    def create_session(
        self,
        vehicle_id: int,
        station_id: int,
        start_time: str,
        end_time: str,
        energy_consumed: float,
        charging_cost: float,
        start_soc: float,
        end_soc: float,
        sync_telemetry: bool = True
    ) -> Dict[str, Any]:
        """
        Validates, derives metrics, and registers a new charging session.
        Optionally logs a corresponding battery telemetry reading in MongoDB.
        """
        is_valid, err = validate_session_data(
            vehicle_id, station_id, start_time, end_time, energy_consumed, charging_cost, start_soc, end_soc
        )
        if not is_valid:
            return {"success": False, "error": err}

        try:
            query = """
            INSERT INTO charging_sessions 
            (vehicle_id, station_id, start_time, end_time, energy_consumed, charging_cost, start_soc, end_soc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """
            _, new_id = self.sql_db.execute_query(
                query,
                (
                    int(vehicle_id),
                    int(station_id),
                    str(start_time),
                    str(end_time),
                    float(energy_consumed),
                    float(charging_cost),
                    float(start_soc),
                    float(end_soc)
                )
            )

            # Derivations
            dur_h, dur_str = calculate_charging_duration(start_time, end_time)
            soc_gain = calculate_soc_increase(start_soc, end_soc)

            # Sync to MongoDB telemetry if requested
            if sync_telemetry:
                latest = self.mongo_db.get_latest_telemetry(vehicle_id)
                current_health = latest["battery_health"] - 0.05 if latest else 95.0
                cycle_count = (latest["cycle_count"] + 1) if latest else 100
                st_info = self.get_station_by_id(station_id)
                power = st_info["power_rating"] if st_info else 50.0
                temp = 32.0 + (power / 25.0)  # Faster charge produces more thermal rise

                self.mongo_db.insert_telemetry({
                    "vehicle_id": int(vehicle_id),
                    "timestamp": end_time,
                    "soc": float(end_soc),
                    "temperature": round(temp, 1),
                    "voltage": round(380.0 + (end_soc / 100.0) * 40.0, 1),
                    "current": round(power * 1000 / 400, 1),
                    "battery_health": round(current_health, 2),
                    "cycle_count": cycle_count,
                    "internal_resistance_mohm": round(21.0 + (100.0 - current_health) * 0.4, 2),
                    "ambient_temp": 28.0
                })

            return {
                "success": True,
                "session_id": new_id,
                "duration_formatted": dur_str,
                "soc_gain": soc_gain,
                "message": f"Charging session #{new_id} recorded successfully!"
            }
        except Exception as e:
            return {"success": False, "error": f"Session insertion failed: {str(e)}"}

    def delete_session(self, session_id: int) -> Dict[str, Any]:
        """Deletes a charging session record."""
        try:
            rows, _ = self.sql_db.execute_query(
                "DELETE FROM charging_sessions WHERE session_id = ?;",
                (int(session_id),)
            )
            if rows == 0:
                return {"success": False, "error": f"Session #{session_id} not found."}
            return {"success": True, "message": f"Session #{session_id} deleted successfully."}
        except Exception as e:
            return {"success": False, "error": f"Deletion error: {str(e)}"}

    def filter_sessions(
        self,
        vehicle_id: Optional[int] = None,
        station_id: Optional[int] = None,
        min_cost: float = 0.0,
        max_cost: float = 10000.0
    ) -> pd.DataFrame:
        """Filters sessions by vehicle, station, and cost range."""
        conditions = ["s.charging_cost >= ?", "s.charging_cost <= ?"]
        params: List[Any] = [float(min_cost), float(max_cost)]

        if vehicle_id is not None and vehicle_id != 0:
            conditions.append("s.vehicle_id = ?")
            params.append(int(vehicle_id))

        if station_id is not None and station_id != 0:
            conditions.append("s.station_id = ?")
            params.append(int(station_id))

        where_clause = " WHERE " + " AND ".join(conditions)

        sql = f"""
        SELECT 
            s.session_id,
            v.model AS vehicle_model,
            v.battery_capacity,
            cs.station_name,
            cs.charger_type,
            s.start_time,
            s.end_time,
            s.energy_consumed,
            s.charging_cost,
            s.start_soc,
            s.end_soc,
            ROUND(s.end_soc - s.start_soc, 2) AS soc_increase
        FROM charging_sessions s
        INNER JOIN vehicles v ON s.vehicle_id = v.vehicle_id
        INNER JOIN charging_stations cs ON s.station_id = cs.station_id
        {where_clause}
        ORDER BY s.start_time DESC;
        """
        df = self.sql_db.fetch_dataframe(sql, tuple(params))
        if not df.empty:
            df["duration_formatted"] = [
                calculate_charging_duration(r["start_time"], r["end_time"])[1]
                for _, r in df.iterrows()
            ]
        return df
