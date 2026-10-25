"""
Vehicle Service Module
EV Charging & Battery Health Intelligence Platform

Provides business logic and CRUD operations for electric vehicles and owners.
Integrates with SQLite for relational persistence and validates all inputs.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
from database.sql_database import get_sql_db
from database.mongo_database import get_mongo_db
from utils.validation import validate_vehicle_data, validate_user_data


class VehicleService:
    """Encapsulates business operations on vehicles and users."""

    def __init__(self):
        self.sql_db = get_sql_db()
        self.mongo_db = get_mongo_db()

    def get_all_vehicles(self) -> pd.DataFrame:
        """Retrieves all registered vehicles enriched with owner details."""
        query = """
        SELECT 
            v.vehicle_id,
            v.model,
            v.battery_capacity,
            v.battery_type,
            v.manufacturing_year,
            v.user_id,
            u.name AS owner_name,
            u.email AS owner_email,
            u.phone AS owner_phone,
            v.created_at
        FROM vehicles v
        INNER JOIN users u ON v.user_id = u.user_id
        ORDER BY v.vehicle_id ASC;
        """
        return self.sql_db.fetch_dataframe(query)

    def get_vehicle_by_id(self, vehicle_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single vehicle record by primary key."""
        query = """
        SELECT 
            v.vehicle_id,
            v.model,
            v.battery_capacity,
            v.battery_type,
            v.manufacturing_year,
            v.user_id,
            u.name AS owner_name,
            u.email AS owner_email,
            u.phone AS owner_phone
        FROM vehicles v
        INNER JOIN users u ON v.user_id = u.user_id
        WHERE v.vehicle_id = ?;
        """
        return self.sql_db.fetch_one(query, (int(vehicle_id),))

    def add_vehicle(
        self,
        user_id: int,
        model: str,
        battery_capacity: float,
        battery_type: str,
        manufacturing_year: int
    ) -> Dict[str, Any]:
        """Validates and creates a new vehicle."""
        is_valid, err = validate_vehicle_data(
            user_id, model, battery_capacity, battery_type, manufacturing_year
        )
        if not is_valid:
            return {"success": False, "error": err}

        try:
            query = """
            INSERT INTO vehicles (user_id, model, battery_capacity, battery_type, manufacturing_year)
            VALUES (?, ?, ?, ?, ?);
            """
            rows, new_id = self.sql_db.execute_query(
                query,
                (int(user_id), model.strip(), float(battery_capacity), battery_type.strip(), int(manufacturing_year))
            )
            return {"success": True, "vehicle_id": new_id, "message": f"Vehicle '{model}' added successfully!"}
        except Exception as e:
            return {"success": False, "error": f"Database insertion failed: {str(e)}"}

    def update_vehicle(
        self,
        vehicle_id: int,
        user_id: int,
        model: str,
        battery_capacity: float,
        battery_type: str,
        manufacturing_year: int
    ) -> Dict[str, Any]:
        """Validates and updates an existing vehicle."""
        is_valid, err = validate_vehicle_data(
            user_id, model, battery_capacity, battery_type, manufacturing_year
        )
        if not is_valid:
            return {"success": False, "error": err}

        try:
            query = """
            UPDATE vehicles
            SET user_id = ?, model = ?, battery_capacity = ?, battery_type = ?, manufacturing_year = ?
            WHERE vehicle_id = ?;
            """
            rows, _ = self.sql_db.execute_query(
                query,
                (int(user_id), model.strip(), float(battery_capacity), battery_type.strip(), int(manufacturing_year), int(vehicle_id))
            )
            if rows == 0:
                return {"success": False, "error": f"Vehicle ID {vehicle_id} not found."}
            return {"success": True, "message": f"Vehicle '{model}' updated successfully!"}
        except Exception as e:
            return {"success": False, "error": f"Database update failed: {str(e)}"}

    def delete_vehicle(self, vehicle_id: int) -> Dict[str, Any]:
        """
        Deletes a vehicle from SQLite (cascading to charging_sessions)
        and purges its battery telemetry documents from MongoDB.
        """
        try:
            # Check vehicle existence
            veh = self.get_vehicle_by_id(vehicle_id)
            if not veh:
                return {"success": False, "error": f"Vehicle ID {vehicle_id} not found."}

            # Delete from SQLite
            self.sql_db.execute_query("DELETE FROM vehicles WHERE vehicle_id = ?;", (int(vehicle_id),))

            # Delete associated MongoDB telemetry
            if self.mongo_db.is_connected and self.mongo_db.collection is not None:
                self.mongo_db.collection.delete_many({"vehicle_id": int(vehicle_id)})
            else:
                self.mongo_db._fallback_telemetry = [
                    d for d in self.mongo_db._fallback_telemetry if d.get("vehicle_id") != int(vehicle_id)
                ]
                self.mongo_db._save_fallback_to_disk()

            return {"success": True, "message": f"Vehicle #{vehicle_id} ({veh['model']}) and all related telemetry deleted."}
        except Exception as e:
            return {"success": False, "error": f"Vehicle deletion failed: {str(e)}"}

    def filter_vehicles(
        self,
        search_query: str = "",
        battery_type: str = "All",
        min_capacity: float = 0.0,
        max_capacity: float = 300.0
    ) -> pd.DataFrame:
        """Filters vehicles dynamically based on search keywords and specifications."""
        conditions = ["v.battery_capacity >= ?", "v.battery_capacity <= ?"]
        params: List[Any] = [float(min_capacity), float(max_capacity)]

        if battery_type != "All":
            conditions.append("v.battery_type = ?")
            params.append(battery_type)

        if search_query and search_query.strip():
            kw = f"%{search_query.strip()}%"
            conditions.append("(v.model LIKE ? OR u.name LIKE ? OR u.email LIKE ?)")
            params.extend([kw, kw, kw])

        where_clause = " WHERE " + " AND ".join(conditions)

        sql = f"""
        SELECT 
            v.vehicle_id,
            v.model,
            v.battery_capacity,
            v.battery_type,
            v.manufacturing_year,
            u.name AS owner_name,
            u.email AS owner_email
        FROM vehicles v
        INNER JOIN users u ON v.user_id = u.user_id
        {where_clause}
        ORDER BY v.vehicle_id ASC;
        """
        return self.sql_db.fetch_dataframe(sql, tuple(params))

    # User operations
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Returns all registered EV owners."""
        return self.sql_db.fetch_all("SELECT user_id, name, email, phone FROM users ORDER BY name ASC;")

    def add_user(self, name: str, email: str, phone: Optional[str] = None) -> Dict[str, Any]:
        """Validates and creates a new user."""
        is_valid, err = validate_user_data(name, email, phone)
        if not is_valid:
            return {"success": False, "error": err}

        # Check unique email
        existing = self.sql_db.fetch_one("SELECT user_id FROM users WHERE email = ?;", (email.strip().lower(),))
        if existing:
            return {"success": False, "error": f"A user with email '{email}' already exists."}

        try:
            _, new_id = self.sql_db.execute_query(
                "INSERT INTO users (name, email, phone) VALUES (?, ?, ?);",
                (name.strip(), email.strip().lower(), phone.strip() if phone else None)
            )
            return {"success": True, "user_id": new_id, "message": f"User '{name}' registered successfully!"}
        except Exception as e:
            return {"success": False, "error": f"Failed to register user: {str(e)}"}

    def get_vehicle_full_dossier(self, vehicle_id: int) -> Dict[str, Any]:
        """
        Builds a comprehensive dossier combining SQL vehicle/owner specs,
        relational charging session history, and NoSQL MongoDB battery telemetry.
        """
        vehicle = self.get_vehicle_by_id(vehicle_id)
        if not vehicle:
            return {}

        # Fetch charging sessions
        sessions_df = self.sql_db.fetch_dataframe("""
        SELECT 
            s.session_id,
            cs.station_name,
            s.start_time,
            s.end_time,
            s.energy_consumed,
            s.charging_cost,
            s.start_soc,
            s.end_soc,
            ROUND(s.end_soc - s.start_soc, 2) AS soc_increase
        FROM charging_sessions s
        INNER JOIN charging_stations cs ON s.station_id = cs.station_id
        WHERE s.vehicle_id = ?
        ORDER BY s.start_time DESC;
        """, (int(vehicle_id),))

        # Fetch MongoDB telemetry summary
        latest_telemetry = self.mongo_db.get_latest_telemetry(vehicle_id)
        telemetry_logs = self.mongo_db.get_vehicle_telemetry(vehicle_id, limit=30)

        return {
            "vehicle": vehicle,
            "sessions": sessions_df,
            "latest_telemetry": latest_telemetry,
            "telemetry_logs": telemetry_logs,
            "total_sessions": len(sessions_df),
            "total_energy": round(sessions_df["energy_consumed"].sum(), 2) if not sessions_df.empty else 0.0,
            "total_cost": round(sessions_df["charging_cost"].sum(), 2) if not sessions_df.empty else 0.0
        }
