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

CREATE INDEX IF NOT EXISTS idx_reviewer_queue_assignments_reviewer_created
    ON reviewer_queue_assignments (reviewer_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_governance_sla_escalations_reviewer_created
    ON governance_sla_escalations (reviewer_id, created_at DESC);
