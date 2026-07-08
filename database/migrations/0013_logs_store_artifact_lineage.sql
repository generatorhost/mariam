CREATE TABLE IF NOT EXISTS logs_store_records (
    log_id UUID PRIMARY KEY,
    source TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    correlation_id UUID NOT NULL,
    context JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS artifact_lineage_records (
    lineage_id UUID PRIMARY KEY,
    artifact_id UUID REFERENCES artifacts (artifact_id) ON DELETE SET NULL,
    mission_id UUID REFERENCES missions (mission_id) ON DELETE SET NULL,
    parent_artifact_id UUID REFERENCES artifacts (artifact_id) ON DELETE SET NULL,
    transformation TEXT NOT NULL,
    produced_by TEXT NOT NULL,
    lineage_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_logs_store_records_source_created
    ON logs_store_records (source, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_artifact_lineage_records_artifact_created
    ON artifact_lineage_records (artifact_id, created_at DESC);
