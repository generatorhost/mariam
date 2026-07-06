CREATE TABLE IF NOT EXISTS runtime_objects (
    id UUID PRIMARY KEY,
    object_type TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    version TEXT NOT NULL,
    manifest JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS plugin_manifests (
    plugin_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    dashboard_route TEXT NOT NULL,
    api_prefix TEXT NOT NULL,
    data_boundary TEXT NOT NULL,
    manifest JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'registered',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS runtime_events (
    event_id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    source TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS missions (
    mission_id UUID PRIMARY KEY,
    plugin_id TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    user_request TEXT NOT NULL,
    status TEXT NOT NULL,
    chief_agent TEXT NOT NULL,
    governance_gate TEXT NOT NULL,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mission_steps (
    step_id UUID PRIMARY KEY,
    mission_id UUID NOT NULL REFERENCES missions (mission_id) ON DELETE CASCADE,
    step_order INTEGER NOT NULL,
    name TEXT NOT NULL,
    actor TEXT NOT NULL,
    result TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id UUID PRIMARY KEY,
    mission_id UUID NOT NULL REFERENCES missions (mission_id) ON DELETE CASCADE,
    plugin_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_resource_routes (
    route_id UUID PRIMARY KEY,
    capability TEXT NOT NULL,
    selected_provider_id TEXT NOT NULL,
    policy TEXT NOT NULL,
    reason TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    fallback_provider_ids TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id UUID PRIMARY KEY,
    actor_id TEXT NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_runtime_objects_type_status
    ON runtime_objects (object_type, status);

CREATE INDEX IF NOT EXISTS idx_runtime_events_name_created
    ON runtime_events (name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_missions_plugin_status
    ON missions (plugin_id, status);

CREATE INDEX IF NOT EXISTS idx_artifacts_mission_status
    ON artifacts (mission_id, status);

CREATE INDEX IF NOT EXISTS idx_ai_resource_routes_capability_created
    ON ai_resource_routes (capability, created_at DESC);
