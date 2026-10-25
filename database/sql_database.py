"""
SQL Database Management Module (SQLite)
EV Charging & Battery Health Intelligence Platform

This module implements the relational database layer using SQLite.
It manages tables for users, vehicles, charging stations, and charging sessions,
enforces foreign key constraints, provides thread-safe access, and supplies
10 advanced SQL queries designed for DCDS Lab ESE demonstration.
"""

import os
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd


class SQLDatabase:
    """Manages SQLite database connections, schema creation, and query executions."""

    def __init__(self, db_path: str = "data/ev_platform.db"):
        self.db_path = db_path
        self._ensure_directory()
        self.init_db()

    def _ensure_directory(self) -> None:
        """Ensure parent directory for database file exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """
        Creates and returns a SQLite connection with foreign keys enabled
        and Row factory configured for dictionary-style column access.
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enforce foreign key constraints in SQLite
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self) -> None:
        """
        Initializes the relational database schema.
        Creates 4 normalized tables with primary keys, foreign keys, and check constraints:
        1. users
        2. vehicles
        3. charging_stations
        4. charging_sessions
        """
        schema_script = """
        -- 1. Users Table
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 2. Vehicles Table
        CREATE TABLE IF NOT EXISTS vehicles (
            vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            model TEXT NOT NULL,
            battery_capacity REAL NOT NULL CHECK(battery_capacity > 0),
            battery_type TEXT NOT NULL,
            manufacturing_year INTEGER NOT NULL CHECK(manufacturing_year >= 2000),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );

        -- 3. Charging Stations Table
        CREATE TABLE IF NOT EXISTS charging_stations (
            station_id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_name TEXT NOT NULL,
            location TEXT NOT NULL,
            charger_type TEXT NOT NULL,
            power_rating REAL NOT NULL CHECK(power_rating > 0),
            availability_status TEXT NOT NULL DEFAULT 'Available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 4. Charging Sessions Table
        CREATE TABLE IF NOT EXISTS charging_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER NOT NULL,
            station_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            energy_consumed REAL NOT NULL CHECK(energy_consumed >= 0),
            charging_cost REAL NOT NULL CHECK(charging_cost >= 0),
            start_soc REAL NOT NULL CHECK(start_soc >= 0 AND start_soc <= 100),
            end_soc REAL NOT NULL CHECK(end_soc >= 0 AND end_soc <= 100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
            FOREIGN KEY (station_id) REFERENCES charging_stations(station_id) ON DELETE RESTRICT
        );

        -- Indices for performance optimization on foreign keys and frequently queried columns
        CREATE INDEX IF NOT EXISTS idx_vehicles_user ON vehicles(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_vehicle ON charging_sessions(vehicle_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_station ON charging_sessions(station_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON charging_sessions(start_time);
        """
        with self.get_connection() as conn:
            conn.executescript(schema_script)
            conn.commit()

    def execute_query(self, query: str, params: tuple = ()) -> Tuple[int, Optional[int]]:
        """
        Executes an INSERT, UPDATE, or DELETE query.
        Returns:
            Tuple of (rows_affected, last_inserted_row_id)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount, cursor.lastrowid
        except sqlite3.Error as e:
            raise RuntimeError(f"Database execution error: {str(e)}")

    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Executes a SELECT query and returns all matching records as a list of dicts."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            raise RuntimeError(f"Database query error: {str(e)}")

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Executes a SELECT query and returns the first matching record as a dict, or None."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise RuntimeError(f"Database query error: {str(e)}")

    def fetch_dataframe(self, query: str, params: tuple = ()) -> pd.DataFrame:
        """Executes a SELECT query and returns the results directly as a Pandas DataFrame."""
        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)
                return df
        except Exception as e:
            raise RuntimeError(f"Failed to fetch DataFrame: {str(e)}")

    def get_table_names(self) -> List[str]:
        """Returns the list of user tables in the SQLite database."""
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        rows = self.fetch_all(query)
        return [row["name"] for row in rows]

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Returns the schema information for a given table using PRAGMA table_info."""
        query = f"PRAGMA table_info({table_name});"
        return self.fetch_all(query)

    def get_table_count(self, table_name: str) -> int:
        """Returns the total number of rows in the given table."""
        query = f"SELECT COUNT(*) as count FROM {table_name};"
        res = self.fetch_one(query)
        return res["count"] if res else 0

    def reset_db(self) -> None:
        """Drops all application tables and re-executes initial schema creation."""
        with self.get_connection() as conn:
            conn.execute("PRAGMA foreign_keys = OFF;")
            tables = ["charging_sessions", "charging_stations", "vehicles", "users"]
            for tbl in tables:
                conn.execute(f"DROP TABLE IF EXISTS {tbl};")
            conn.commit()
        self.init_db()

    # =========================================================================
    # ADVANCED SQL QUERIES (DCDS Lab ESE Demonstration Suite)
    # =========================================================================
    def get_advanced_queries(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns a dictionary of 10 advanced SQL queries demonstrating
        fundamental and advanced relational database concepts:
        - Inner Joins
        - Multi-table Joins
        - Group By & Multi-metric Aggregations
        - Benchmark Aggregations (AVG, MIN, MAX)
        - Having clause filtering
        - Nested Subqueries
        - Ordering and Top-N Ranking
        - Analytical Anomaly Detection
        - Date/Time String Temporal Aggregations
        """
        return {
            "Q1": {
                "title": "1. Vehicle & Session History (INNER JOIN)",
                "concept": "Relational INNER JOIN between vehicles and charging_sessions",
                "description": "Retrieves comprehensive charging logs linked to vehicle specifications and user identity.",
                "sql": """
SELECT 
    s.session_id,
    v.model AS vehicle_model,
    v.battery_capacity,
    v.battery_type,
    u.name AS owner_name,
    s.start_time,
    s.end_time,
    s.energy_consumed,
    s.charging_cost,
    s.start_soc,
    s.end_soc,
    ROUND(s.end_soc - s.start_soc, 2) AS soc_gained
FROM charging_sessions s
INNER JOIN vehicles v ON s.vehicle_id = v.vehicle_id
INNER JOIN users u ON v.user_id = u.user_id
ORDER BY s.start_time DESC
LIMIT 15;
                """
            },
            "Q2": {
                "title": "2. Charging Sessions with Station Specs (INNER JOIN)",
                "concept": "Relational JOIN between charging_sessions and charging_stations",
                "description": "Combines transactional charging data with infrastructure specifications (charger type & power rating).",
                "sql": """
SELECT 
    s.session_id,
    cs.station_name,
    cs.location,
    cs.charger_type,
    cs.power_rating AS station_power_kw,
    s.energy_consumed AS kwh_delivered,
    s.charging_cost,
    s.start_time,
    s.end_time
FROM charging_sessions s
INNER JOIN charging_stations cs ON s.station_id = cs.station_id
ORDER BY s.energy_consumed DESC
LIMIT 15;
                """
            },
            "Q3": {
                "title": "3. Aggregation & Grouping by Vehicle (GROUP BY & Multi-Metrics)",
                "concept": "GROUP BY with multi-metric aggregate functions (SUM, AVG, COUNT)",
                "description": "Calculates cumulative energy consumed, total expenditure, session count, and average SOC delta per vehicle.",
                "sql": """
SELECT 
    v.vehicle_id,
    v.model,
    v.battery_type,
    COUNT(s.session_id) AS total_sessions,
    ROUND(SUM(s.energy_consumed), 2) AS total_energy_kwh,
    ROUND(SUM(s.charging_cost), 2) AS total_cost_inr,
    ROUND(AVG(s.energy_consumed), 2) AS avg_energy_per_session,
    ROUND(AVG(s.end_soc - s.start_soc), 2) AS avg_soc_increase
FROM vehicles v
LEFT JOIN charging_sessions s ON v.vehicle_id = s.vehicle_id
GROUP BY v.vehicle_id, v.model, v.battery_type
ORDER BY total_energy_kwh DESC;
                """
            },
            "Q4": {
                "title": "4. System-Wide Financial & Energy Benchmarks (Scalar Aggregation)",
                "concept": "Scalar Aggregations (AVG, MIN, MAX, SUM) across the entire dataset",
                "description": "Computes fleet-wide financial metrics, average cost per session, and effective unit cost per kWh.",
                "sql": """
SELECT 
    COUNT(session_id) AS total_sessions_recorded,
    ROUND(SUM(energy_consumed), 2) AS total_fleet_energy_kwh,
    ROUND(SUM(charging_cost), 2) AS total_revenue_generated,
    ROUND(AVG(charging_cost), 2) AS avg_session_cost,
    ROUND(MIN(charging_cost), 2) AS min_session_cost,
    ROUND(MAX(charging_cost), 2) AS max_session_cost,
    ROUND(SUM(charging_cost) / SUM(energy_consumed), 2) AS effective_cost_per_kwh
FROM charging_sessions;
                """
            },
            "Q5": {
                "title": "5. Average Energy Consumption by Battery Chemistry (GROUP BY & HAVING)",
                "concept": "GROUP BY with condition filtering using HAVING clause",
                "description": "Evaluates average energy consumed across different battery chemistries (LFP, NMC, Solid-state) with minimum session criteria.",
                "sql": """
SELECT 
    v.battery_type,
    COUNT(DISTINCT v.vehicle_id) AS vehicle_count,
    COUNT(s.session_id) AS total_charging_events,
    ROUND(AVG(s.energy_consumed), 2) AS avg_energy_kwh,
    ROUND(AVG(s.charging_cost), 2) AS avg_cost
FROM vehicles v
INNER JOIN charging_sessions s ON v.vehicle_id = s.vehicle_id
GROUP BY v.battery_type
HAVING COUNT(s.session_id) >= 1
ORDER BY avg_energy_kwh DESC;
                """
            },
            "Q6": {
                "title": "6. Vehicles with Above-Average Energy Consumption (Nested Subquery)",
                "concept": "Nested Subquery in WHERE clause comparing against an aggregate scalar",
                "description": "Identifies high-utilization vehicles whose cumulative charging energy exceeds the fleet-wide vehicle average.",
                "sql": """
SELECT 
    v.vehicle_id,
    v.model,
    u.name AS owner_name,
    v.battery_capacity,
    ROUND(SUM(s.energy_consumed), 2) AS vehicle_total_energy
FROM vehicles v
INNER JOIN users u ON v.user_id = u.user_id
INNER JOIN charging_sessions s ON v.vehicle_id = s.vehicle_id
GROUP BY v.vehicle_id, v.model, u.name, v.battery_capacity
HAVING vehicle_total_energy > (
    SELECT AVG(veh_energy)
    FROM (
        SELECT SUM(energy_consumed) AS veh_energy
        FROM charging_sessions
        GROUP BY vehicle_id
    )
)
ORDER BY vehicle_total_energy DESC;
                """
            },
            "Q7": {
                "title": "7. Station Utilization & Top Earner Ranking (GROUP BY & Top-1)",
                "concept": "Aggregation with ORDER BY and LIMIT to find the most frequently used station",
                "description": "Determines the most heavily utilized charging station, total sessions hosted, and revenue generated.",
                "sql": """
SELECT 
    cs.station_id,
    cs.station_name,
    cs.location,
    cs.charger_type,
    cs.power_rating,
    COUNT(s.session_id) AS sessions_count,
    ROUND(SUM(s.energy_consumed), 2) AS total_energy_delivered,
    ROUND(SUM(s.charging_cost), 2) AS total_revenue
FROM charging_stations cs
INNER JOIN charging_sessions s ON cs.station_id = s.station_id
GROUP BY cs.station_id, cs.station_name, cs.location, cs.charger_type, cs.power_rating
ORDER BY sessions_count DESC
LIMIT 5;
                """
            },
            "Q8": {
                "title": "8. Vehicles with Highest Charging Expenditure (Top-N Analysis)",
                "concept": "Multi-table JOIN, grouping, and descending ordering with LIMIT",
                "description": "Ranks vehicles generating the highest total charging expenditure.",
                "sql": """
SELECT 
    v.vehicle_id,
    v.model,
    u.name AS owner,
    u.email,
    COUNT(s.session_id) AS total_sessions,
    ROUND(SUM(s.charging_cost), 2) AS total_expenditure
FROM vehicles v
INNER JOIN users u ON v.user_id = u.user_id
INNER JOIN charging_sessions s ON v.vehicle_id = s.vehicle_id
GROUP BY v.vehicle_id, v.model, u.name, u.email
ORDER BY total_expenditure DESC
LIMIT 5;
                """
            },
            "Q9": {
                "title": "9. Anomaly Detection: Sessions with Unusually High Energy (Correlated Subquery)",
                "concept": "Subquery filter identifying sessions > 1.35x vehicle's battery capacity or fleet outlier",
                "description": "Flags charging sessions whose energy intake exceeds normal operational thresholds or 1.25x average session energy.",
                "sql": """
SELECT 
    s.session_id,
    v.model,
    v.battery_capacity,
    s.energy_consumed,
    s.charging_cost,
    s.start_soc,
    s.end_soc,
    cs.station_name,
    ROUND((s.energy_consumed / (SELECT AVG(energy_consumed) FROM charging_sessions)), 2) AS ratio_to_average
FROM charging_sessions s
INNER JOIN vehicles v ON s.vehicle_id = v.vehicle_id
INNER JOIN charging_stations cs ON s.station_id = cs.station_id
WHERE s.energy_consumed > 1.25 * (SELECT AVG(energy_consumed) FROM charging_sessions)
ORDER BY s.energy_consumed DESC;
                """
            },
            "Q10": {
                "title": "10. Temporal Trend: Daily Charging Activity & Revenue (Date/Time Functions)",
                "concept": "SQLite Date/Time extraction (substr/strftime) with GROUP BY",
                "description": "Aggregates charging sessions on a chronological daily basis to observe load demand and revenue patterns.",
                "sql": """
SELECT 
    SUBSTR(s.start_time, 1, 10) AS charge_date,
    COUNT(s.session_id) AS total_sessions,
    ROUND(SUM(s.energy_consumed), 2) AS daily_energy_kwh,
    ROUND(SUM(s.charging_cost), 2) AS daily_revenue,
    ROUND(AVG(s.energy_consumed), 2) AS avg_energy_per_session
FROM charging_sessions s
GROUP BY SUBSTR(s.start_time, 1, 10)
ORDER BY charge_date DESC
LIMIT 14;
                """
            }
        }

    def execute_advanced_query(self, query_id: str) -> pd.DataFrame:
        """Executes one of the predefined advanced SQL queries by ID (e.g. 'Q1' to 'Q10')."""
        queries = self.get_advanced_queries()
        if query_id not in queries:
            raise ValueError(f"Unknown query ID: {query_id}. Available: {list(queries.keys())}")
        return self.fetch_dataframe(queries[query_id]["sql"])


# Global singleton factory
_sql_db_instance: Optional[SQLDatabase] = None


def get_sql_db(db_path: str = "data/ev_platform.db") -> SQLDatabase:
    """Returns a singleton instance of the SQLDatabase."""
    global _sql_db_instance
    if _sql_db_instance is None:
        _sql_db_instance = SQLDatabase(db_path)
    return _sql_db_instance
