"""
Verification & Test Suite
EV Charging & Battery Health Intelligence Platform

Tests SQLite relational models, MongoDB NoSQL operations,
validation rules, 10 Advanced SQL queries, and 8 MongoDB aggregation pipelines.
"""

import os
import sys
import unittest
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database.sql_database import get_sql_db
from database.mongo_database import get_mongo_db
from services.vehicle_service import VehicleService
from services.charging_service import ChargingService
from services.battery_service import BatteryService
from services.analytics_service import AnalyticsService
from utils.validation import (
    validate_user_data,
    validate_vehicle_data,
    validate_station_data,
    validate_session_data,
    validate_telemetry_data
)
from utils.helpers import (
    calculate_charging_duration,
    calculate_soc_increase,
    calculate_charging_efficiency,
    get_battery_health_category
)
from data.sample_data import load_sample_data


class TestEVPlatform(unittest.TestCase):
    """Automated test cases for DCDS Lab ESE requirements."""

    @classmethod
    def setUpClass(cls):
        """Seed sample data before tests."""
        cls.sql_db = get_sql_db()
        cls.mongo_db = get_mongo_db()
        cls.v_service = VehicleService()
        cls.c_service = ChargingService()
        cls.b_service = BatteryService()
        cls.a_service = AnalyticsService()
        load_sample_data(force=True)

    def test_database_initialization(self):
        """Test 1: Verify tables exist and contain seeded records."""
        tables = self.sql_db.get_table_names()
        self.assertIn("users", tables)
        self.assertIn("vehicles", tables)
        self.assertIn("charging_stations", tables)
        self.assertIn("charging_sessions", tables)

        self.assertGreaterEqual(self.sql_db.get_table_count("users"), 5)
        self.assertGreaterEqual(self.sql_db.get_table_count("vehicles"), 5)
        self.assertGreaterEqual(self.sql_db.get_table_count("charging_stations"), 5)
        self.assertGreaterEqual(self.sql_db.get_table_count("charging_sessions"), 20)
        self.assertGreaterEqual(self.mongo_db.count_telemetry(), 30)

    def test_validation_rules(self):
        """Test 2: Verify input validation logic and error messages."""
        # Email format
        valid_u, _ = validate_user_data("Valid User", "valid.user@test.com")
        self.assertTrue(valid_u)
        invalid_u, err = validate_user_data("Bad User", "not-an-email")
        self.assertFalse(invalid_u)
        self.assertIn("Invalid email format", err)

        # Capacity > 0
        valid_v, _ = validate_vehicle_data(1, "Test EV", 50.0, "LFP", 2023)
        self.assertTrue(valid_v)
        invalid_v, err_v = validate_vehicle_data(1, "Test EV", -10.0, "LFP", 2023)
        self.assertFalse(invalid_v)
        self.assertIn("greater than 0", err_v)

        # Session chronology and SOC
        t_start = "2026-10-24 10:00:00"
        t_end = "2026-10-24 09:00:00"  # End before start
        inv_session, err_s = validate_session_data(1, 1, t_start, t_end, 20.0, 300.0, 20.0, 80.0)
        self.assertFalse(inv_session)
        self.assertIn("strictly after", err_s)

        # SOC increase constraint
        inv_soc, err_soc = validate_session_data(1, 1, "2026-10-24 10:00:00", "2026-10-24 11:00:00", 20.0, 300.0, 80.0, 20.0)
        self.assertFalse(inv_soc)
        self.assertIn("cannot be less than Starting SOC", err_soc)

    def test_advanced_sql_queries(self):
        """Test 3: Execute all 10 Advanced SQL queries and verify non-empty results."""
        queries = self.sql_db.get_advanced_queries()
        self.assertEqual(len(queries), 10)

        for q_id in queries:
            df = self.sql_db.execute_advanced_query(q_id)
            self.assertIsNotNone(df, f"Query {q_id} returned None")
            self.assertGreater(len(df), 0, f"Query {q_id} returned 0 rows")

    def test_mongodb_aggregations(self):
        """Test 4: Execute all 8 MongoDB aggregation pipelines."""
        pipelines = self.mongo_db.get_aggregation_pipelines()
        self.assertEqual(len(pipelines), 8)

        for agg_id, meta in pipelines.items():
            res = self.mongo_db.run_aggregation(meta["pipeline"])
            self.assertIsNotNone(res, f"Pipeline {agg_id} returned None")
            self.assertIsInstance(res, list, f"Pipeline {agg_id} result is not a list")
            self.assertGreater(len(res), 0, f"Pipeline {agg_id} produced empty results")

    def test_battery_diagnostics_and_rules(self):
        """Test 5: Verify SOH classification and diagnostic alerts."""
        cat_exc = get_battery_health_category(94.5)
        self.assertEqual(cat_exc["status"], "Excellent")
        cat_good = get_battery_health_category(84.0)
        self.assertEqual(cat_good["status"], "Good")
        cat_mod = get_battery_health_category(76.5)
        self.assertEqual(cat_mod["status"], "Moderate")
        cat_poor = get_battery_health_category(68.0)
        self.assertEqual(cat_poor["status"], "Poor")

        # Diagnostics for vehicle 1
        diag = self.b_service.analyze_battery_diagnostics(1)
        self.assertIn("status", diag)
        self.assertIn("warnings", diag)
        self.assertIn("stats", diag)

    def test_helpers_and_calculations(self):
        """Test 6: Verify duration, SOC delta, and efficiency math."""
        dur_h, dur_s = calculate_charging_duration("2026-10-24 10:00:00", "2026-10-24 11:30:00")
        self.assertEqual(dur_h, 1.5)
        self.assertEqual(dur_s, "1h 30m")

        soc_gain = calculate_soc_increase(20.0, 85.5)
        self.assertEqual(soc_gain, 65.5)

        eff = calculate_charging_efficiency(30.0, 20.0, 80.0, 40.0)
        self.assertGreaterEqual(eff, 65.0)
        self.assertLessEqual(eff, 98.5)


if __name__ == "__main__":
    unittest.main()
