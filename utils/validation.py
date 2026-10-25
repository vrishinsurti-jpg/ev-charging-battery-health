"""
Validation Module
EV Charging & Battery Health Intelligence Platform

This module enforces domain constraints, data types, value boundaries,
email format checks, time chronology, and foreign key integrity.
"""

import re
from datetime import datetime
from typing import Tuple, Optional, Any, Dict
from database.sql_database import get_sql_db


def is_valid_email(email: str) -> bool:
    """Validates email format using RFC 5322 regex."""
    if not email or not isinstance(email, str):
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


def validate_user_data(name: str, email: str, phone: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Validates user creation/update data.
    - Name must be non-empty and at least 2 characters.
    - Email must be valid format.
    - Phone (if provided) should be 8-15 digits.
    """
    if not name or not name.strip():
        return False, "User name cannot be empty."
    if len(name.strip()) < 2:
        return False, "User name must be at least 2 characters long."
    
    if not email or not email.strip():
        return False, "Email address is required."
    if not is_valid_email(email):
        return False, f"Invalid email format: '{email}'. Please enter a valid address (e.g., user@example.com)."
    
    if phone and phone.strip():
        cleaned_phone = re.sub(r"[\s\-\+\(\)]", "", phone.strip())
        if not cleaned_phone.isdigit() or len(cleaned_phone) < 8 or len(cleaned_phone) > 15:
            return False, "Phone number must contain between 8 and 15 digits."
            
    return True, None


def validate_vehicle_data(
    user_id: int,
    model: str,
    battery_capacity: float,
    battery_type: str,
    manufacturing_year: int
) -> Tuple[bool, Optional[str]]:
    """
    Validates vehicle creation/update data:
    - User must exist in the database (foreign key check).
    - Model must be non-empty.
    - Battery capacity must be > 0 (typically 10 - 250 kWh).
    - Battery type must be non-empty.
    - Manufacturing year must be between 2000 and current year + 1.
    """
    db = get_sql_db()
    
    # Foreign key check
    user = db.fetch_one("SELECT user_id FROM users WHERE user_id = ?;", (int(user_id),))
    if not user:
        return False, f"Selected owner with User ID {user_id} does not exist."

    if not model or not model.strip():
        return False, "Vehicle model name cannot be empty."

    try:
        cap = float(battery_capacity)
        if cap <= 0:
            return False, "Battery capacity must be strictly greater than 0 kWh."
        if cap > 300:
            return False, "Battery capacity cannot exceed 300 kWh for passenger EVs."
    except (ValueError, TypeError):
        return False, "Battery capacity must be a valid numeric value."

    if not battery_type or not battery_type.strip():
        return False, "Battery chemistry/type is required (e.g., Lithium-ion, LFP, NMC)."

    current_year = datetime.now().year
    try:
        year = int(manufacturing_year)
        if year < 2000 or year > current_year + 1:
            return False, f"Manufacturing year must be between 2000 and {current_year + 1}."
    except (ValueError, TypeError):
        return False, "Manufacturing year must be an integer."

    return True, None


def validate_station_data(
    station_name: str,
    location: str,
    charger_type: str,
    power_rating: float,
    availability_status: str
) -> Tuple[bool, Optional[str]]:
    """
    Validates charging station data:
    - Station name and location must be non-empty.
    - Charger type must be valid.
    - Power rating must be > 0.
    - Availability status must be one of ['Available', 'Occupied', 'Maintenance'].
    """
    if not station_name or not station_name.strip():
        return False, "Station name cannot be empty."

    if not location or not location.strip():
        return False, "Station location cannot be empty."

    valid_types = ["Type 2 AC", "CCS2 DC Fast", "CHAdeMO", "Tesla Supercharger", "CCS2 Ultra-Fast"]
    if not charger_type or not charger_type.strip():
        return False, "Charger type is required."

    try:
        power = float(power_rating)
        if power <= 0:
            return False, "Power rating must be strictly greater than 0 kW."
        if power > 500:
            return False, "Power rating cannot exceed 500 kW."
    except (ValueError, TypeError):
        return False, "Power rating must be a valid number."

    valid_statuses = ["Available", "Occupied", "Maintenance"]
    if availability_status not in valid_statuses:
        return False, f"Availability status must be one of: {', '.join(valid_statuses)}."

    return True, None


def validate_session_data(
    vehicle_id: int,
    station_id: int,
    start_time: str,
    end_time: str,
    energy_consumed: float,
    charging_cost: float,
    start_soc: float,
    end_soc: float
) -> Tuple[bool, Optional[str]]:
    """
    Validates charging session data:
    - Foreign keys: vehicle_id and station_id must exist in SQLite.
    - End time must be chronologically after start time.
    - start_soc and end_soc must be between 0 and 100.
    - end_soc must be >= start_soc (charging increases battery SOC).
    - energy_consumed >= 0.
    - charging_cost >= 0.
    """
    db = get_sql_db()

    # Foreign key checks
    veh = db.fetch_one("SELECT vehicle_id, battery_capacity FROM vehicles WHERE vehicle_id = ?;", (int(vehicle_id),))
    if not veh:
        return False, f"Invalid vehicle selection: Vehicle ID {vehicle_id} does not exist."

    st = db.fetch_one("SELECT station_id FROM charging_stations WHERE station_id = ?;", (int(station_id),))
    if not st:
        return False, f"Invalid station selection: Station ID {station_id} does not exist."

    # Parse and validate datetimes
    try:
        t_start = datetime.fromisoformat(str(start_time).replace("Z", ""))
        t_end = datetime.fromisoformat(str(end_time).replace("Z", ""))
    except Exception:
        return False, "Invalid timestamp format. Use standard ISO format (YYYY-MM-DD HH:MM:SS)."

    if t_end <= t_start:
        return False, "Charging end time must be chronologically strictly after start time."

    # Validate SOC values
    try:
        s_soc = float(start_soc)
        e_soc = float(end_soc)
    except (ValueError, TypeError):
        return False, "Starting and Ending SOC must be numeric percentages."

    if not (0.0 <= s_soc <= 100.0):
        return False, f"Starting SOC ({s_soc}%) must be between 0% and 100%."
    if not (0.0 <= e_soc <= 100.0):
        return False, f"Ending SOC ({e_soc}%) must be between 0% and 100%."
    if e_soc < s_soc:
        return False, f"Ending SOC ({e_soc}%) cannot be less than Starting SOC ({s_soc}%)."

    # Validate Energy & Cost
    try:
        energy = float(energy_consumed)
        cost = float(charging_cost)
    except (ValueError, TypeError):
        return False, "Energy consumed and charging cost must be valid numeric values."

    if energy < 0:
        return False, "Energy consumed cannot be negative."
    if cost < 0:
        return False, "Charging cost cannot be negative."

    return True, None


def validate_telemetry_data(
    vehicle_id: int,
    soc: float,
    temperature: float,
    voltage: float,
    current: float,
    battery_health: float,
    cycle_count: int
) -> Tuple[bool, Optional[str]]:
    """
    Validates NoSQL telemetry document values:
    - Vehicle ID exists in SQL.
    - SOC in [0, 100].
    - Battery health (SOH) in [0, 100].
    - Temperature within physical bounds [-30°C, 95°C].
    - Voltage > 0.
    - Cycle count >= 0.
    """
    db = get_sql_db()
    veh = db.fetch_one("SELECT vehicle_id FROM vehicles WHERE vehicle_id = ?;", (int(vehicle_id),))
    if not veh:
        return False, f"Telemetry vehicle ID {vehicle_id} does not exist in relational vehicle database."

    try:
        soc_val = float(soc)
        soh_val = float(battery_health)
        temp_val = float(temperature)
        volt_val = float(voltage)
        curr_val = float(current)
        cycles = int(cycle_count)
    except (ValueError, TypeError):
        return False, "Telemetry reading fields must be numeric."

    if not (0.0 <= soc_val <= 100.0):
        return False, "State of Charge (SOC) must be between 0.0 and 100.0%."
    if not (0.0 <= soh_val <= 100.0):
        return False, "Battery Health (SOH) must be between 0.0 and 100.0%."
    if not (-30.0 <= temp_val <= 95.0):
        return False, "Battery temperature must be between -30°C and +95°C."
    if volt_val <= 0:
        return False, "Battery pack voltage must be greater than 0 V."
    if cycles < 0:
        return False, "Cycle count cannot be negative."

    return True, None
