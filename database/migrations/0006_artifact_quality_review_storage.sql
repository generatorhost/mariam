CREATE TABLE IF NOT EXISTS artifact_quality_reviews (
    review_id UUID PRIMARY KEY,
    artifact_id UUID NOT NULL REFERENCES artifacts (artifact_id) ON DELETE CASCADE,
    mission_id UUID NOT NULL REFERENCES missions (mission_id) ON DELETE CASCADE,
    plugin_id TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    score INTEGER NOT NULL,
    checks JSONB NOT NULL DEFAULT '[]'::jsonb,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_artifact_quality_reviews_artifact_created
    ON artifact_quality_reviews (artifact_id, created_at DESC);
