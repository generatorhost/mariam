CREATE TABLE IF NOT EXISTS audit_event_archive_records (
    archive_id UUID PRIMARY KEY,
    audit_id UUID REFERENCES audit_log (audit_id) ON DELETE SET NULL,
    event_id UUID REFERENCES runtime_events (event_id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    archive_reason TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS metrics_store_records (
    metric_id UUID PRIMARY KEY,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    metric_unit TEXT NOT NULL,
    source TEXT NOT NULL,
    dimensions JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_event_archive_records_target_created
    ON audit_event_archive_records (target_type, target_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_metrics_store_records_name_created
    ON metrics_store_records (metric_name, created_at DESC);
