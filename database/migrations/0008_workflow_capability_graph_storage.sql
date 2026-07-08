CREATE TABLE IF NOT EXISTS workflow_records (
    workflow_id UUID PRIMARY KEY,
    plugin_id TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS capability_graph_records (
    capability_id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    capability_type TEXT NOT NULL,
    status TEXT NOT NULL,
    nodes JSONB NOT NULL DEFAULT '[]'::jsonb,
    edges JSONB NOT NULL DEFAULT '[]'::jsonb,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workflow_records_plugin_created
    ON workflow_records (plugin_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_capability_graph_records_type_created
    ON capability_graph_records (capability_type, created_at DESC);
