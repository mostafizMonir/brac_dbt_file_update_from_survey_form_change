import psycopg2

# Database configuration from app.py
DB_CONFIG = {
    'host': '202.4.127.189',
    'port': '5632',
    'database': 'monir_brac_mne_data',
    'user': 'postgres',
    'password': 'P0StGr35**'
}

try:
    # Connect to PostgreSQL
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Query to get the view definition
    query = """
    SELECT pg_get_viewdef('public.survey_view'::regclass, true);
    """

    cursor.execute(query)
    result = cursor.fetchone()

    if result:
        print("-- DDL for public.survey_view")
        print("CREATE OR REPLACE VIEW public.survey_view AS")
        print(result[0])
        print(";")
    else:
        print("View 'survey_view' not found in public schema")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")