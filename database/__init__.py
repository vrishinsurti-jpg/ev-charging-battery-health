"""
Database package for EV Charging & Battery Health Intelligence Platform.
Provides dual-database architecture:
- SQLite for structured relational data
- MongoDB for semi-structured battery telemetry
"""
from database.sql_database import SQLDatabase, get_sql_db
from database.mongo_database import MongoDatabase, get_mongo_db

__all__ = ["SQLDatabase", "get_sql_db", "MongoDatabase", "get_mongo_db"]
