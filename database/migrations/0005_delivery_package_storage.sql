CREATE TABLE IF NOT EXISTS delivery_packages (
    delivery_id UUID PRIMARY KEY,
    artifact_id UUID NOT NULL REFERENCES artifacts (artifact_id) ON DELETE CASCADE,
    mission_id UUID NOT NULL REFERENCES missions (mission_id) ON DELETE CASCADE,
    plugin_id TEXT NOT NULL,
    destination TEXT NOT NULL,
    status TEXT NOT NULL,
    package_manifest JSONB NOT NULL DEFAULT '{}'::jsonb,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_delivery_packages_plugin_status
    ON delivery_packages (plugin_id, status);
