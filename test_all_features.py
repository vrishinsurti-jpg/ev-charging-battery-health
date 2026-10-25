import sys
from datetime import datetime
import pandas as pd

from database.sql_database import get_sql_db
from database.mongo_database import get_mongo_db
from services.vehicle_service import VehicleService
from services.charging_service import ChargingService
from services.battery_service import BatteryService
from services.analytics_service import AnalyticsService

def test_all():
    print("=== Testing Database Connections ===")
    sql_db = get_sql_db()
    mongo_db = get_mongo_db()
    assert sql_db.get_table_count("vehicles") == 8
    assert sql_db.get_table_count("charging_stations") == 6
    assert sql_db.get_table_count("charging_sessions") >= 50
    assert mongo_db.count_telemetry() > 0
    print("Database connections verified.")

    print("\n=== Testing Overview Date Filtering ===")
    analytics = AnalyticsService()
    # 7-day preset
    s_7 = analytics.get_dashboard_summary_metrics("2026-10-24", "2026-10-30")
    print("7-Day metrics:", s_7)
    assert s_7["total_sessions"] == 38
    assert round(s_7["total_energy_kwh"], 1) == 1499.2
    assert round(s_7["total_cost_inr"], 0) == 29165.0

    # All history preset
    s_all = analytics.get_dashboard_summary_metrics("2026-10-18", "2026-10-30")
    print("All-time metrics:", s_all)
    assert s_all["total_sessions"] == 56
    assert s_all["total_energy_kwh"] == 2126.6
    assert s_all["total_cost_inr"] == 41408.0

    print("\n=== Testing Temporal Trends Filtering ===")
    t_7 = analytics.get_temporal_energy_trends("2026-10-24", "2026-10-30")
    print(f"7-Day daily rows: {len(t_7)}, sessions sum: {t_7['sessions_count'].sum()}")
    assert len(t_7) == 7
    assert t_7["sessions_count"].sum() == 38

    t_all = analytics.get_temporal_energy_trends()
    print(f"All-time daily rows: {len(t_all)}, sessions sum: {t_all['sessions_count'].sum()}")
    assert t_all["sessions_count"].sum() == 56

    print("\n=== Testing Fleet Battery Health & MongoDB Telemetry ===")
    battery = BatteryService()
    for vid in [1, 2, 3, 6]:
        diag = battery.analyze_battery_diagnostics(vid)
        st = diag["status"]
        print(f"Vehicle #{vid}: SOH={st['battery_health']}%, SOC={st['soc']}%, Temp={st['temperature']}°C, Volt={st['voltage']}V, Curr={st['current']}A, Cycles={st['cycle_count']}")
        assert "battery_health" in st
        assert "soc" in st
        assert "temperature" in st
        assert "voltage" in st
        assert "current" in st
        assert "cycle_count" in st

    print("\n=== Testing Vehicle Performance & Dossier ===")
    vehicles = VehicleService()
    top_veh = analytics.get_top_vehicle_performance(limit=4)
    print("Top 4 vehicles:", [v["model"] for v in top_veh])
    assert len(top_veh) == 4
    for v in top_veh:
        dossier = vehicles.get_vehicle_full_dossier(v["rank"])
        assert "vehicle" in dossier
        assert "total_sessions" in dossier
        assert "total_energy" in dossier

    print("\n=== Testing Charging History Formatting ===")
    charging = ChargingService()
    sessions_df = charging.get_all_sessions()
    assert not sessions_df.empty
    expected_cols = ["session_id", "vehicle_model", "station_name", "start_time", "duration_formatted", "energy_consumed", "charging_cost"]
    for col in expected_cols:
        assert col in sessions_df.columns, f"Missing column {col}"
    print(f"Verified {len(sessions_df)} sessions with required columns.")

    print("\n=== Testing Insights Subtabs ===")
    fleet_df = analytics.get_energy_cost_per_vehicle()
    assert not fleet_df.empty
    station_df = analytics.get_sessions_per_station()
    assert not station_df.empty
    corr_df = analytics.get_battery_health_vs_charging_activity()
    assert not corr_df.empty
    breakdown_df = analytics.get_charger_type_breakdown()
    assert not breakdown_df.empty
    print("All 4 Insights data sources verified.")

    print("\n=== Testing Data Page Tables ===")
    assert not sql_db.fetch_dataframe("SELECT * FROM vehicles;").empty
    assert not sql_db.fetch_dataframe("SELECT * FROM charging_sessions;").empty
    assert not sql_db.fetch_dataframe("SELECT * FROM charging_stations;").empty
    assert not sql_db.fetch_dataframe("SELECT * FROM users;").empty
    tel_sample = mongo_db.get_all_telemetry(limit=5)
    assert len(tel_sample) > 0
    print("All Data page SQL and MongoDB sources verified.")

    print("\n>>> ALL TESTS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    test_all()
