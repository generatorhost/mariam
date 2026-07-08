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

CREATE INDEX IF NOT EXISTS idx_reviewer_decision_outcomes_reviewer_created
    ON reviewer_decision_outcomes (reviewer_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_reviewer_decision_outcomes_target_created
    ON reviewer_decision_outcomes (target_type, target_id, created_at DESC);
