import psycopg2
import sys

# Database configuration from app.py
DB_CONFIG = {
    'host': '202.4.127.189',
    'port': '5632',
    'database': 'monir_brac_mne_data',
    'user': 'postgres',
    'password': 'P0StGr35**'
}

def get_survey_view_ddl():
    """Get the current DDL for survey_view"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Query to get the view definition
        query = """
        SELECT pg_get_viewdef('public.survey_view'::regclass, true);
        """

        cursor.execute(query)
        result = cursor.fetchone()

        if result:
            return result[0]
        else:
            print("View 'survey_view' not found in public schema")
            return None

    except Exception as e:
        print(f"Error getting view DDL: {e}")
        return None
    finally:
        if conn:
            cursor.close()
            conn.close()

def update_survey_view_with_form_id(survey_form_id):
    """Update the survey_view by adding survey_form_id to the existing array in WHERE clause"""
    try:
        # First get the current DDL
        current_ddl = get_survey_view_ddl()
        if not current_ddl:
            return False

        print("Current survey_view DDL:")
        print("-" * 80)
        print(current_ddl)
        print("-" * 80)

        # Check if the survey_form_id already exists in the array
        if f"'{survey_form_id}'" in current_ddl:
            print(f"\nSurvey form ID '{survey_form_id}' already exists in the view!")
            return True

        # Find the ARRAY line and add the new survey_form_id
        lines = current_ddl.split('\n')
        updated_lines = []

        for line in lines:
            if 'ARRAY[' in line:
                # Find the closing bracket position
                if line.strip().endswith(']);'):
                    # Add the new ID before the closing bracket
                    modified_line = line.replace(']);', f", '{survey_form_id}'::text]);")
                    updated_lines.append(modified_line)
                elif line.strip().endswith('])'):
                    # Add the new ID before the closing bracket
                    modified_line = line.replace('])', f", '{survey_form_id}'::text])")
                    updated_lines.append(modified_line)
                else:
                    # ARRAY might span multiple lines, just add the line as is
                    updated_lines.append(line)
            elif updated_lines and 'ARRAY[' in updated_lines[-1] and ']);' in line:
                # Handle multi-line ARRAY case - add before the last ID
                modified_line = line.replace(']);', f", '{survey_form_id}'::text]);")
                updated_lines.append(modified_line)
            elif updated_lines and any('ARRAY[' in l for l in updated_lines[-5:]) and line.strip().endswith("'::text]);"):
                # Another multi-line case - add as a new line before the closing
                updated_lines.append(line.replace(']);', ','))
                # Add the new survey form ID with proper indentation
                indent = len(line) - len(line.lstrip())
                updated_lines.append(' ' * indent + f"'{survey_form_id}'::text]);")
            else:
                updated_lines.append(line)

        updated_ddl = '\n'.join(updated_lines)

        print("\nUpdated survey_view DDL:")
        print("-" * 80)
        print(updated_ddl)
        print("-" * 80)

        # Now execute the updated DDL
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Drop and recreate the view with updated DDL
        drop_query = "DROP VIEW IF EXISTS public.survey_view CASCADE;"
        create_query = f"CREATE VIEW public.survey_view AS\n{updated_ddl};"

        print("\nExecuting DROP VIEW...")
        cursor.execute(drop_query)

        print("Executing CREATE VIEW with updated DDL...")
        cursor.execute(create_query)

        conn.commit()
        print("\nView successfully updated with survey_form_id in WHERE clause!")

        return True

    except Exception as e:
        print(f"Error updating view: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        survey_form_id = sys.argv[1]
        print(f"Updating survey_view with survey_form_id: {survey_form_id}")
        success = update_survey_view_with_form_id(survey_form_id)
        if success:
            print("Update completed successfully!")
        else:
            print("Update failed!")
    else:
        # Just get and display the current DDL
        ddl = get_survey_view_ddl()
        if ddl:
            print("Current survey_view DDL:")
            print("-" * 80)
            print("CREATE OR REPLACE VIEW public.survey_view AS")
            print(ddl)
            print(";")