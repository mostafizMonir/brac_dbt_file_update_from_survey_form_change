# BRAC DBT Survey Form Updater


## back end branch : DataWarehouseSurveyForm , draftwurveyformservice.cs
## survey client branch : ware-house

This Flask API automatically updates DBT models based on survey form data from a PostgreSQL database.

## Features

- Fetches survey form configuration from PostgreSQL database
- Generates SQL queries dynamically based on survey form structure
- Manages Git repository (clone/pull from Bitbucket)
- Updates or creates DBT SQL model files
- Commits and pushes changes to remote repository
- Dockerized deployment

## Project Structure

```
.
├── app.py                              # Main Flask application
├── docker-compose.yml                  # Docker compose configuration
├── Dockerfile                          # Docker image definition
├── requirements.txt                    # Python dependencies
├── test_db_connection.py              # Database connection tester
├── .gitignore                         # Git ignore rules
├── context/
│   ├── instruction.txt                # Original requirements
│   └── survey_flat_table_gen_from_ans.txt  # SQL query template
└── brac_dbt/                          # Cloned repository (auto-created)
```

## Installation

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Git

### Setup

1. Clone this repository
2. Ensure the `context/` directory contains:
   - `survey_flat_table_gen_from_ans.txt` (SQL query template)

### Using Docker (Recommended)

```bash
# Build and start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Test database connection
python test_db_connection.py

# Run Flask app
python app.py
```

## API Usage

### Health Check

```bash
GET http://localhost:5000/health
```

### Process Survey Form

```bash
POST http://localhost:5000/process-survey/<survey_form_id>
```

Example:
```bash
curl -X POST http://localhost:5000/process-survey/61f011e4405549849bffe813d12ee511
```

Response:
```json
{
  "status": "success",
  "survey_form_id": "61f011e4405549849bffe813d12ee511",
  "table_name": "survey_table_name",
  "file_path": "./brac_dbt/brac_dbt_code/models/data_mart/survey_table_name.sql",
  "action": "updated",
  "timestamp": "2024-01-01T12:00:00"
}
```

## Workflow

1. **API receives survey_form_id**
2. **Query database** to get table_name from survey_form table
3. **Execute SQL template** with survey_form_id to generate query
4. **Execute generated query** to get final SQL
5. **Clone/pull Git repository** from Bitbucket
6. **Update or create** DBT model file in data_mart directory
7. **Commit and push** changes to remote repository

## Configuration

Environment variables (set in docker-compose.yml):

- `DB_HOST`: PostgreSQL host (default: 202.4.127.189)
- `DB_PORT`: PostgreSQL port (default: 5632)
- `DB_NAME`: Database name (default: monir_brac_mne_data)
- `DB_USER`: Database user (default: postgres)
- `DB_PASSWORD`: Database password

## Security Notes

- Database credentials should be stored in environment variables or secrets management system
- Consider using Git SSH keys or access tokens instead of HTTPS for repository access
- Add authentication to the Flask API endpoints

## Troubleshooting

### Test Database Connection
```bash
python test_db_connection.py
```

### Check Docker Logs
```bash
docker-compose logs flask-app
```

### Common Issues

1. **Database connection failed**: Check network connectivity and credentials
2. **Git push failed**: Ensure proper authentication for Bitbucket repository
3. **File not found**: Verify context directory structure and files exist