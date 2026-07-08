CREATE TABLE IF NOT EXISTS vector_index_records (
    vector_id UUID PRIMARY KEY,
    artifact_id UUID REFERENCES artifacts (artifact_id) ON DELETE SET NULL,
    namespace TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    status TEXT NOT NULL,
    vector_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS artifact_store_records (
    store_id UUID PRIMARY KEY,
    artifact_id UUID REFERENCES artifacts (artifact_id) ON DELETE SET NULL,
    storage_provider TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    checksum TEXT NOT NULL,
    content_type TEXT NOT NULL,
    status TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_vector_index_records_namespace_created
    ON vector_index_records (namespace, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_artifact_store_records_provider_created
    ON artifact_store_records (storage_provider, created_at DESC);
