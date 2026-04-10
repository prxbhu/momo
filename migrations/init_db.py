"""
Database initialization script
Run this to create all tables and indexes
"""

import logging
from pathlib import Path
import os
import psycopg2
import sqlparse

# ---- CONFIG ----
DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INIT_SQL_PATH = Path(__file__).parent.parent / "migrations" / "001_init.sql"


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def init_database():
    """Initialize database schema from init.sql"""
    logger.info("Starting database initialization...")

    conn = get_connection()
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        init_sql = INIT_SQL_PATH.read_text()

        statements = [
            stmt.strip()
            for stmt in sqlparse.split(init_sql)
            if stmt.strip()
        ]

        for stmt in statements:
            logger.debug(f"Executing SQL:\n{stmt[:120]}...")
            cursor.execute(stmt)

        conn.commit()
        logger.info("Database initialization completed successfully!")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error during initialization: {e}")
        raise

    finally:
        cursor.close()
        conn.close()


def drop_all_tables():
    """Drop all tables (use with caution!)"""
    logger.warning("Dropping all tables...")

    conn = get_connection()
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        cursor.execute("DROP SCHEMA IF EXISTS public CASCADE")
        cursor.execute("CREATE SCHEMA public")
        cursor.execute("GRANT ALL ON SCHEMA public TO postgres")
        cursor.execute("GRANT ALL ON SCHEMA public TO public")

        conn.commit()
        logger.info("All tables dropped")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error while dropping tables: {e}")
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--drop":
        drop_all_tables()

    init_database()