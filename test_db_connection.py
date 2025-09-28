import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': '202.4.127.189',
    'port': '5632',
    'database': 'monir_brac_mne_data',
    'user': 'postgres',
    'password': 'P0StGr35**'
}

def test_connection():
    """Test database connection and basic query"""
    try:
        logger.info("Testing database connection...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SELECT version()")
        db_version = cursor.fetchone()
        logger.info(f"Connected to: {db_version[0]}")

        cursor.execute("SELECT COUNT(*) FROM survey_form")
        count = cursor.fetchone()
        logger.info(f"Number of survey forms: {count[0]}")

        cursor.execute("SELECT id, table_name FROM survey_form LIMIT 1")
        sample = cursor.fetchone()
        if sample:
            logger.info(f"Sample survey form - ID: {sample[0]}, Table: {sample[1]}")

        cursor.close()
        conn.close()
        logger.info("Database connection test successful!")
        return True

    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()