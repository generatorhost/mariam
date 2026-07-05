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

