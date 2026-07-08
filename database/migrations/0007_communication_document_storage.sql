CREATE TABLE IF NOT EXISTS communication_records (
    record_id UUID PRIMARY KEY,
    channel TEXT NOT NULL,
    direction TEXT NOT NULL,
    participant TEXT NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document_records (
    document_id UUID PRIMARY KEY,
    artifact_id UUID REFERENCES artifacts (artifact_id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    document_type TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    status TEXT NOT NULL,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_communication_records_channel_created
    ON communication_records (channel, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_document_records_type_created
    ON document_records (document_type, created_at DESC);
