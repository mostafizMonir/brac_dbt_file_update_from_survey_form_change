import os
import logging
import psycopg2
from flask import Flask
from flask_restx import Api, Resource, fields
from git import Repo
import traceback
from datetime import datetime
from update_survey_view import update_survey_view_with_form_id
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
api = Api(app,
          version='1.0',
          title='DBT Survey Form API',
          description='API for processing survey forms and updating DBT files',
          doc='/swagger'  # This sets the Swagger UI endpoint
         )

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '202.4.127.189'),
    'port': os.environ.get('DB_PORT', '5632'),
    'database': os.environ.get('DB_NAME', 'monir_brac_mne_data'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'P0StGr35**')
}

# Git configuration with authentication
# Get base repository URL from environment
BASE_REPO_URL = os.environ.get('GIT_REPO_URL', 'https://bitbucket.org/jantrik/brac_dbt.git')
BRANCH_NAME = os.environ.get('GIT_BRANCH', 'dev')
REPO_PATH = os.environ.get('REPO_PATH', './brac_dbt')

# Authentication credentials
BITBUCKET_USERNAME = os.environ.get('BITBUCKET_USERNAME', '')
BITBUCKET_API_TOKEN = os.environ.get('BITBUCKET_API_TOKEN', '')

# Construct URL with authentication if credentials are provided
if BITBUCKET_USERNAME and BITBUCKET_API_TOKEN and 'bitbucket.org' in BASE_REPO_URL:
    # Extract the repository path from the URL
    repo_parts = BASE_REPO_URL.replace('https://', '').replace('http://', '').split('/', 1)
    if len(repo_parts) > 1:
        repo_path = repo_parts[1]
        REPO_URL = f'https://{BITBUCKET_USERNAME}:{BITBUCKET_API_TOKEN}@bitbucket.org/{repo_path}'
    else:
        REPO_URL = BASE_REPO_URL
else:
    REPO_URL = BASE_REPO_URL

# Log the final repository URL (masking credentials for security)
if BITBUCKET_USERNAME and BITBUCKET_API_TOKEN in REPO_URL:
    masked_url = REPO_URL.replace(BITBUCKET_API_TOKEN, '***MASKED***')
    logger.info(f"Final Repository URL configured: {masked_url}")
    print(f"Final Repository URL: {masked_url}")
else:
    logger.info(f"Final Repository URL configured: {REPO_URL}")
    print(f"Final Repository URL: {REPO_URL}")

def get_db_connection():
    """Create and return a database connection"""
    return psycopg2.connect(**DB_CONFIG)

def get_survey_form_id_from_draft(draft_survey_form_id):
    """Get survey form ID from draft survey form ID"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT id FROM survey_form WHERE draft_survey_form_id = %s"
        cursor.execute(query, (draft_survey_form_id,))
        result = cursor.fetchone()

        if result:
            logger.info(f"Found survey_form_id: {result[0]} for draft_survey_form_id: {draft_survey_form_id}")
            return result[0]
        else:
            raise ValueError(f"No survey form found with draft_survey_form_id: {draft_survey_form_id}")

    except Exception as e:
        logger.error(f"Error getting survey form ID from draft: {e}")
        raise
    finally:
        if conn:
            conn.close()

def get_dbt_file_name_from_survey_form(survey_form_id):
    """Get DBT file name from warehouse_dbt_files_survey_form_mapping table,
    fallback to survey_form table if not found"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # First, try to get warehouse_dbt_file_name from mapping table
        mapping_query = """
            SELECT warehouse_dbt_file_name
            FROM warehouse_dbt_files_survey_form_mapping
            WHERE survey_form_id = %s
            AND warehouse_dbt_file_name IS NOT NULL
        """
        cursor.execute(mapping_query, (survey_form_id,))
        mapping_result = cursor.fetchone()

        if mapping_result and mapping_result[0]:
            logger.info(f"Found DBT file name in mapping table: {mapping_result[0]}")
            return mapping_result[0]

        # If not found in mapping table, fallback to survey_form table
        logger.info("DBT file name not found in mapping table, checking survey_form table")
        query = "SELECT table_name FROM survey_form WHERE id = %s"
        
        cursor.execute(query, (survey_form_id,))
        result = cursor.fetchone()

        if result:
            logger.info(f"Using table_name from survey_form table: {result[0]}")
            return result[0]
        else:
            raise ValueError(f"No survey form found with id: {survey_form_id}")

    except Exception as e:
        logger.error(f"Error getting DBT file name: {e}")
        raise
    finally:
        if conn:
            conn.close()

def execute_survey_query(survey_form_id):
    """Execute the survey flat table generation query"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        with open('context/survey_flat_table_gen_from_ans.txt', 'r') as f:
            template_query = f.read()

        template_query = template_query.replace("'61f011e4405549849bffe813d12ee511'", f"'{survey_form_id}'")

        logger.info(f"Executing first query for survey_form_id: {survey_form_id}")
        logger.info(f"query : {template_query}")
        cursor.execute(template_query)
        result = cursor.fetchone()

        if not result or not result[0]:
            raise ValueError("First query returned no results")

        generated_query = result[0]
        logger.info("Executing generated query")

        escaped_query = generated_query.replace("'", "''")
        generated_query_formatted = f"WITH final_query AS ({generated_query}) SELECT 'SELECT * FROM (' || CHR(10) || '{escaped_query}'|| CHR(10) || ') AS t' AS final_sql"
        cursor.execute(generated_query_formatted)
        final_result = cursor.fetchone()

        if final_result and final_result[0]:
            return generated_query
        else:
            return generated_query

    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise
    finally:
        if conn:
            conn.close()

def manage_git_repository():
    """Clone or pull the git repository"""
    import shutil
    try:
        # Log which repository we're working with
        if BITBUCKET_USERNAME and BITBUCKET_API_TOKEN in REPO_URL:
            masked_url = REPO_URL.replace(BITBUCKET_API_TOKEN, '***MASKED***')
            logger.info(f"Working with repository: {masked_url}")
        else:
            logger.info(f"Working with repository: {REPO_URL}")

        git_dir = os.path.join(REPO_PATH, '.git')

        if os.path.exists(REPO_PATH):
            # Check if it's a valid git repository
            if os.path.exists(git_dir):
                try:
                    repo = Repo(REPO_PATH)
                    logger.info("Repository exists, pulling latest changes")
                    origin = repo.remote('origin')
                    repo.git.checkout(BRANCH_NAME)
                    origin.pull()
                    return repo
                except Exception as e:
                    logger.warning(f"Invalid git repository at {REPO_PATH}: {e}")
                    logger.info("Removing corrupted repository directory")

            # Remove the entire directory if it exists but is corrupted or incomplete
            logger.info(f"Cleaning up existing directory: {REPO_PATH}")
            shutil.rmtree(REPO_PATH, ignore_errors=True)

        # Clone fresh repository
        logger.info(f"Cloning repository fresh to {REPO_PATH}")
        os.makedirs(REPO_PATH, exist_ok=True)
        repo = Repo.clone_from(REPO_URL, REPO_PATH, branch=BRANCH_NAME)
        logger.info("Repository cloned successfully")

        return repo
    except Exception as e:
        logger.error(f"Error managing repository: {e}")
        raise

def update_dbt_file(repo, table_name, sql_content):
    """Update or create DBT SQL file"""
    try:
        dbt_model_path = os.path.join(REPO_PATH, 'brac_dbt_code', 'models', 'data_mart')

        os.makedirs(dbt_model_path, exist_ok=True)

        file_path = os.path.join(dbt_model_path, f"{table_name}.sql")
        logger.info(f"na*********** file: {file_path}")

        file_exists = os.path.exists(file_path)

        with open(file_path, 'w') as f:
            f.write(sql_content)

        logger.info(f"{'Updated' if file_exists else 'Created'} file: {file_path}")

        return file_path, file_exists

    except Exception as e:
        logger.error(f"Error updating DBT file: {e}")
        raise

def commit_and_push(repo, file_path, survey_form_id, file_exists):
    """Commit changes if any, and always push to remote"""
    try:
        # Convert absolute path to relative path from repo root
        repo_root = os.path.abspath(repo.working_dir)
        abs_file_path = os.path.abspath(file_path)
        relative_path = os.path.relpath(abs_file_path, repo_root)

        # Normalize path separators for git (use forward slashes)
        relative_path = relative_path.replace(os.sep, '/')

        changes_committed = False

        # Check if there are actual changes to commit
        if repo.is_dirty(path=relative_path) or relative_path in repo.untracked_files:
            if file_exists:
                # File was modified - add the modified file to staging
                logger.info(f"File has changes. Adding modified file to staging: {relative_path}")
                repo.index.add([relative_path])
                action = "update"
            else:
                # New file - add the new file to staging
                logger.info(f"Adding new file to staging: {relative_path}")
                repo.index.add([relative_path])
                action = "new"

            commit_message = f"{action} survey form data with form id {survey_form_id}"

            # Commit the staged changes
            logger.info(f"Committing with message: {commit_message}")
            repo.index.commit(commit_message)
            logger.info(f"Successfully committed: {commit_message}")
            changes_committed = True
        else:
            logger.info(f"No changes detected in file: {relative_path}. Skipping commit.")

        # Always push to remote to ensure synchronization
        logger.info("Pushing to remote repository to ensure synchronization")
        if not BITBUCKET_API_TOKEN:
            logger.warning("BITBUCKET_API_TOKEN not configured. Push may fail due to authentication.")
        else:
            logger.info(f"Pushing as user: {BITBUCKET_USERNAME}")

        origin = repo.remote('origin')
        origin.push()

        logger.info("**********************end**************Successfully pushed to remote repository")
        return changes_committed

    except Exception as e:
        logger.error(f"Error committing and pushing: {e}")
        raise

health_model = api.model('Health', {
    'status': fields.String(description='Health status'),
    'timestamp': fields.String(description='Current timestamp')
})

@api.route('/health')
class HealthCheck(Resource):
    @api.doc('health_check')
    @api.marshal_with(health_model)
    def get(self):
        """Health check endpoint"""
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

survey_response_model = api.model('SurveyResponse', {
    'status': fields.String(description='Processing status'),
    'survey_form_id': fields.String(description='Survey form ID'),
    'dbt_file_name': fields.String(description='DBT file name'),
    'file_path': fields.String(description='DBT file path'),
    'action': fields.String(description='Action taken (created/updated)'),
    'changes_committed': fields.Boolean(description='Whether changes were committed'),
    'message': fields.String(description='Status message'),
    'timestamp': fields.String(description='Processing timestamp')
})

error_model = api.model('ErrorResponse', {
    'status': fields.String(description='Error status'),
    'survey_form_id': fields.String(description='Survey form ID'),
    'error': fields.String(description='Error message'),
    'timestamp': fields.String(description='Error timestamp')
})

@api.route('/process-survey/<string:draft_survey_form_id>')
@api.param('draft_survey_form_id', 'The draft survey form ID to process')
class ProcessSurvey(Resource):
    @api.doc('process_survey',
             responses={
                 200: ('Success', survey_response_model),
                 500: ('Error', error_model)
             })
    @api.marshal_with(survey_response_model, code=200)
    @api.marshal_with(error_model, code=500)
    def post(self, draft_survey_form_id):
        """Process a survey form and update DBT files"""
        try:
            logger.info(f"*********************START****************************Processing survey form: {draft_survey_form_id}")
            survey_form_id = get_survey_form_id_from_draft(draft_survey_form_id)
            dbt_file_name = get_dbt_file_name_from_survey_form(survey_form_id)
            logger.info(f"Found DBT file name: {dbt_file_name}")

            sql_content = execute_survey_query(survey_form_id)
            logger.info("Generated SQL content")

            repo = manage_git_repository()

            # Use the actual DBT file name from database
            # For testing, you can override with: dbt_file_name = 'test_monir_survey_query_gen'
            #dbt_file_name = 'test_monir_survey_query_gen'

            file_path, file_exists = update_dbt_file(repo, dbt_file_name, sql_content)

            # If this is a new file, update the survey_view to include this survey_form_id
            if not file_exists:
                logger.info(f"New file created, updating survey_view with survey_form_id: {survey_form_id}")
                try:
                    update_result = update_survey_view_with_form_id(survey_form_id)
                    if update_result:
                        logger.info(f"Successfully updated survey_view with survey_form_id: {survey_form_id}")
                    else:
                        logger.warning(f"Failed to update survey_view with survey_form_id: {survey_form_id}")
                except Exception as e:
                    logger.error(f"Error updating survey_view: {e}")
                    # Continue with the process even if view update fails

            changes_committed = commit_and_push(repo, file_path, survey_form_id, file_exists)

            return {
                "status": "success",
                "survey_form_id": survey_form_id,
                "dbt_file_name": dbt_file_name,
                "file_path": file_path,
                "action": "updated" if file_exists else "created",
                "changes_committed": changes_committed,
                "message": "Changes committed and pushed" if changes_committed else "No changes to commit, repository synced",
                "timestamp": datetime.now().isoformat()
            }, 200

        except Exception as e:
            logger.error(f"Error processing survey form: {e}")
            logger.error(traceback.format_exc())

            api.abort(500,
                     status="error",
                     survey_form_id=survey_form_id,
                     error=str(e),
                     timestamp=datetime.now().isoformat())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)