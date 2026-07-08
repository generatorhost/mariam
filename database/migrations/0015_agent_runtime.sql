CREATE TABLE IF NOT EXISTS agent_societies (
    society_id UUID PRIMARY KEY,
    plugin_id TEXT NOT NULL UNIQUE,
    business_unit_name TEXT NOT NULL,
    chief_node_id TEXT NOT NULL,
    nodes JSONB NOT NULL DEFAULT '[]'::jsonb,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_execution_plans (
    execution_id UUID PRIMARY KEY,
    plugin_id TEXT NOT NULL,
    user_request TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    chief_node_id TEXT NOT NULL,
    tasks JSONB NOT NULL DEFAULT '[]'::jsonb,
    communication_channels TEXT[] NOT NULL DEFAULT '{}',
    review_gates TEXT[] NOT NULL DEFAULT '{}',
    status TEXT NOT NULL,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
