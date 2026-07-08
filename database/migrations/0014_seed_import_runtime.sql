CREATE TABLE IF NOT EXISTS seed_import_records (
    source_id TEXT PRIMARY KEY,
    source_path TEXT NOT NULL,
    source_name TEXT NOT NULL,
    status TEXT NOT NULL,
    record JSONB NOT NULL DEFAULT '{}'::jsonb,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_seed_import_records_status_imported
    ON seed_import_records (status, imported_at);

CREATE INDEX IF NOT EXISTS idx_seed_import_records_source_name
    ON seed_import_records (source_name);
