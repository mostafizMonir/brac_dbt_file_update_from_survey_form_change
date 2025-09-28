-- Create warehouse_dbt_files_survey_form_mapping table
-- This table maps survey forms to their corresponding warehouse DBT file names

CREATE TABLE IF NOT EXISTS warehouse_dbt_files_survey_form_mapping (
    id VARCHAR PRIMARY KEY,
    survey_form_id VARCHAR NOT NULL,
    warehouse_dbt_file_name VARCHAR,  -- Can be NULL
    settings JSONB,  -- Using JSONB for flexible settings storage
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on survey_form_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_survey_form_id
ON warehouse_dbt_files_survey_form_mapping(survey_form_id);

-- Add comments for documentation
COMMENT ON TABLE warehouse_dbt_files_survey_form_mapping IS 'Maps survey forms to their corresponding warehouse DBT file names';
COMMENT ON COLUMN warehouse_dbt_files_survey_form_mapping.id IS 'Unique identifier for the mapping';
COMMENT ON COLUMN warehouse_dbt_files_survey_form_mapping.survey_form_id IS 'ID of the survey form';
COMMENT ON COLUMN warehouse_dbt_files_survey_form_mapping.warehouse_dbt_file_name IS 'Name of the DBT file in the warehouse (can be NULL)';
COMMENT ON COLUMN warehouse_dbt_files_survey_form_mapping.settings IS 'Additional configuration settings in JSON format';
COMMENT ON COLUMN warehouse_dbt_files_survey_form_mapping.created_at IS 'Timestamp when the record was created';
COMMENT ON COLUMN warehouse_dbt_files_survey_form_mapping.updated_at IS 'Timestamp when the record was last updated';

-- Example insert statement (commented out)
-- INSERT INTO warehouse_dbt_files_survey_form_mapping (id, survey_form_id, warehouse_dbt_file_name, settings)
-- VALUES ('unique_id_1', 'survey_form_id_1', 'warehouse_file_name', '{"key": "value"}'::jsonb);