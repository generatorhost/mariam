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

CREATE TABLE IF NOT EXISTS reviewer_queue_assignments (
    assignment_id UUID PRIMARY KEY,
    audit_id UUID REFERENCES audit_log (audit_id) ON DELETE CASCADE,
    assigned_by TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    approval_role TEXT NOT NULL,
    reviewer_queue TEXT NOT NULL,
    status TEXT NOT NULL,
    reason TEXT NOT NULL,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS governance_sla_escalations (
    escalation_id UUID PRIMARY KEY,
    audit_id UUID REFERENCES audit_log (audit_id) ON DELETE CASCADE,
    escalated_by TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    escalation_level TEXT NOT NULL,
    status TEXT NOT NULL,
    reason TEXT NOT NULL,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reviewer_decision_outcomes (
    decision_id UUID PRIMARY KEY,
    audit_id UUID REFERENCES audit_log (audit_id) ON DELETE CASCADE,
    assignment_id UUID REFERENCES reviewer_queue_assignments (assignment_id) ON DELETE SET NULL,
    decided_by TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    data_platform TEXT NOT NULL DEFAULT 'DB MARIAM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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

CREATE INDEX IF NOT EXISTS idx_runtime_objects_type_status
    ON runtime_objects (object_type, status);

CREATE INDEX IF NOT EXISTS idx_runtime_events_name_created
    ON runtime_events (name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_missions_plugin_status
    ON missions (plugin_id, status);

CREATE INDEX IF NOT EXISTS idx_artifacts_mission_status
    ON artifacts (mission_id, status);

CREATE INDEX IF NOT EXISTS idx_delivery_packages_plugin_status
    ON delivery_packages (plugin_id, status);

CREATE INDEX IF NOT EXISTS idx_artifact_quality_reviews_artifact_created
    ON artifact_quality_reviews (artifact_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ai_resource_routes_capability_created
    ON ai_resource_routes (capability, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_communication_records_channel_created
    ON communication_records (channel, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_document_records_type_created
    ON document_records (document_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_workflow_records_plugin_created
    ON workflow_records (plugin_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_capability_graph_records_type_created
    ON capability_graph_records (capability_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_vector_index_records_namespace_created
    ON vector_index_records (namespace, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_artifact_store_records_provider_created
    ON artifact_store_records (storage_provider, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_reviewer_queue_assignments_reviewer_created
    ON reviewer_queue_assignments (reviewer_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_governance_sla_escalations_reviewer_created
    ON governance_sla_escalations (reviewer_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_reviewer_decision_outcomes_reviewer_created
    ON reviewer_decision_outcomes (reviewer_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_reviewer_decision_outcomes_target_created
    ON reviewer_decision_outcomes (target_type, target_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_event_archive_records_target_created
    ON audit_event_archive_records (target_type, target_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_metrics_store_records_name_created
    ON metrics_store_records (metric_name, created_at DESC);
