from __future__ import annotations

from typing import Protocol

from app.core.audit import (
    AuditRecord,
    GovernanceSLAEscalationRecord,
    ReviewerDecisionOutcomeRecord,
    ReviewerQueueAssignmentRecord,
)


class AuditRepository(Protocol):
    def save(self, record: AuditRecord) -> AuditRecord:
        pass

    def list(self) -> list[AuditRecord]:
        pass

    def save_reviewer_queue_assignment(
        self,
        record: ReviewerQueueAssignmentRecord,
    ) -> ReviewerQueueAssignmentRecord:
        pass

    def list_reviewer_queue_assignments(self) -> list[ReviewerQueueAssignmentRecord]:
        pass

    def save_governance_sla_escalation(
        self,
        record: GovernanceSLAEscalationRecord,
    ) -> GovernanceSLAEscalationRecord:
        pass

    def list_governance_sla_escalations(self) -> list[GovernanceSLAEscalationRecord]:
        pass

    def save_reviewer_decision_outcome(
        self,
        record: ReviewerDecisionOutcomeRecord,
    ) -> ReviewerDecisionOutcomeRecord:
        pass

    def list_reviewer_decision_outcomes(self) -> list[ReviewerDecisionOutcomeRecord]:
        pass


class InMemoryAuditRepository:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []
        self._queue_assignments: list[ReviewerQueueAssignmentRecord] = []
        self._sla_escalations: list[GovernanceSLAEscalationRecord] = []
        self._decision_outcomes: list[ReviewerDecisionOutcomeRecord] = []

    def save(self, record: AuditRecord) -> AuditRecord:
        self._records.append(record)
        return record

    def list(self) -> list[AuditRecord]:
        return list(self._records)

    def save_reviewer_queue_assignment(
        self,
        record: ReviewerQueueAssignmentRecord,
    ) -> ReviewerQueueAssignmentRecord:
        self._queue_assignments.append(record)
        return record

    def list_reviewer_queue_assignments(self) -> list[ReviewerQueueAssignmentRecord]:
        return list(self._queue_assignments)

    def save_governance_sla_escalation(
        self,
        record: GovernanceSLAEscalationRecord,
    ) -> GovernanceSLAEscalationRecord:
        self._sla_escalations.append(record)
        return record

    def list_governance_sla_escalations(self) -> list[GovernanceSLAEscalationRecord]:
        return list(self._sla_escalations)

    def save_reviewer_decision_outcome(
        self,
        record: ReviewerDecisionOutcomeRecord,
    ) -> ReviewerDecisionOutcomeRecord:
        self._decision_outcomes.append(record)
        return record

    def list_reviewer_decision_outcomes(self) -> list[ReviewerDecisionOutcomeRecord]:
        return list(self._decision_outcomes)


class PostgresAuditRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _ensure_governance_history_schema(self, cursor) -> None:
        cursor.execute(
            """
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
            )
            """
        )
        cursor.execute(
            """
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
            )
            """
        )
        cursor.execute(
            """
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
            )
            """
        )

    def save(self, record: AuditRecord) -> AuditRecord:
        import psycopg
        from psycopg.types.json import Jsonb

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO audit_log (
                        audit_id,
                        actor_id,
                        action,
                        target_type,
                        target_id,
                        decision,
                        evidence,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.audit_id,
                        record.actor_id,
                        record.action,
                        record.target_type,
                        record.target_id,
                        record.decision,
                        Jsonb(record.evidence),
                        record.created_at,
                    ),
                )
        return record

    def list(self) -> list[AuditRecord]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT audit_id, actor_id, action, target_type, target_id, decision, evidence, created_at
                    FROM audit_log
                    ORDER BY created_at ASC
                    """
                )
                rows = cursor.fetchall()
        return [
            AuditRecord(
                audit_id=str(row["audit_id"]),
                actor_id=row["actor_id"],
                action=row["action"],
                target_type=row["target_type"],
                target_id=row["target_id"],
                decision=row["decision"],
                evidence=dict(row["evidence"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def save_reviewer_queue_assignment(
        self,
        record: ReviewerQueueAssignmentRecord,
    ) -> ReviewerQueueAssignmentRecord:
        import psycopg

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                self._ensure_governance_history_schema(cursor)
                cursor.execute(
                    """
                    INSERT INTO reviewer_queue_assignments (
                        assignment_id,
                        audit_id,
                        assigned_by,
                        reviewer_id,
                        target_type,
                        target_id,
                        approval_role,
                        reviewer_queue,
                        status,
                        reason,
                        data_platform,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.assignment_id,
                        record.audit_id,
                        record.assigned_by,
                        record.reviewer_id,
                        record.target_type,
                        record.target_id,
                        record.approval_role,
                        record.reviewer_queue,
                        record.status,
                        record.reason,
                        record.data_platform,
                        record.created_at,
                    ),
                )
        return record

    def list_reviewer_queue_assignments(self) -> list[ReviewerQueueAssignmentRecord]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                self._ensure_governance_history_schema(cursor)
                cursor.execute(
                    """
                    SELECT
                        assignment_id,
                        audit_id,
                        assigned_by,
                        reviewer_id,
                        target_type,
                        target_id,
                        approval_role,
                        reviewer_queue,
                        status,
                        reason,
                        data_platform,
                        created_at
                    FROM reviewer_queue_assignments
                    ORDER BY created_at ASC
                    """
                )
                rows = cursor.fetchall()
        return [
            ReviewerQueueAssignmentRecord(
                assignment_id=str(row["assignment_id"]),
                audit_id=str(row["audit_id"]),
                assigned_by=row["assigned_by"],
                reviewer_id=row["reviewer_id"],
                target_type=row["target_type"],
                target_id=row["target_id"],
                approval_role=row["approval_role"],
                reviewer_queue=row["reviewer_queue"],
                status=row["status"],
                reason=row["reason"],
                data_platform=row["data_platform"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def save_governance_sla_escalation(
        self,
        record: GovernanceSLAEscalationRecord,
    ) -> GovernanceSLAEscalationRecord:
        import psycopg

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                self._ensure_governance_history_schema(cursor)
                cursor.execute(
                    """
                    INSERT INTO governance_sla_escalations (
                        escalation_id,
                        audit_id,
                        escalated_by,
                        reviewer_id,
                        target_type,
                        target_id,
                        escalation_level,
                        status,
                        reason,
                        data_platform,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.escalation_id,
                        record.audit_id,
                        record.escalated_by,
                        record.reviewer_id,
                        record.target_type,
                        record.target_id,
                        record.escalation_level,
                        record.status,
                        record.reason,
                        record.data_platform,
                        record.created_at,
                    ),
                )
        return record

    def list_governance_sla_escalations(self) -> list[GovernanceSLAEscalationRecord]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                self._ensure_governance_history_schema(cursor)
                cursor.execute(
                    """
                    SELECT
                        escalation_id,
                        audit_id,
                        escalated_by,
                        reviewer_id,
                        target_type,
                        target_id,
                        escalation_level,
                        status,
                        reason,
                        data_platform,
                        created_at
                    FROM governance_sla_escalations
                    ORDER BY created_at ASC
                    """
                )
                rows = cursor.fetchall()
        return [
            GovernanceSLAEscalationRecord(
                escalation_id=str(row["escalation_id"]),
                audit_id=str(row["audit_id"]),
                escalated_by=row["escalated_by"],
                reviewer_id=row["reviewer_id"],
                target_type=row["target_type"],
                target_id=row["target_id"],
                escalation_level=row["escalation_level"],
                status=row["status"],
                reason=row["reason"],
                data_platform=row["data_platform"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def save_reviewer_decision_outcome(
        self,
        record: ReviewerDecisionOutcomeRecord,
    ) -> ReviewerDecisionOutcomeRecord:
        import psycopg
        from psycopg.types.json import Jsonb

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                self._ensure_governance_history_schema(cursor)
                cursor.execute(
                    """
                    INSERT INTO reviewer_decision_outcomes (
                        decision_id,
                        audit_id,
                        assignment_id,
                        decided_by,
                        reviewer_id,
                        target_type,
                        target_id,
                        decision,
                        reason,
                        evidence,
                        data_platform,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.decision_id,
                        record.audit_id,
                        record.assignment_id,
                        record.decided_by,
                        record.reviewer_id,
                        record.target_type,
                        record.target_id,
                        record.decision,
                        record.reason,
                        Jsonb(record.evidence),
                        record.data_platform,
                        record.created_at,
                    ),
                )
        return record

    def list_reviewer_decision_outcomes(self) -> list[ReviewerDecisionOutcomeRecord]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                self._ensure_governance_history_schema(cursor)
                cursor.execute(
                    """
                    SELECT
                        decision_id,
                        audit_id,
                        assignment_id,
                        decided_by,
                        reviewer_id,
                        target_type,
                        target_id,
                        decision,
                        reason,
                        evidence,
                        data_platform,
                        created_at
                    FROM reviewer_decision_outcomes
                    ORDER BY created_at ASC
                    """
                )
                rows = cursor.fetchall()
        return [
            ReviewerDecisionOutcomeRecord(
                decision_id=str(row["decision_id"]),
                audit_id=str(row["audit_id"]),
                assignment_id=str(row["assignment_id"]) if row["assignment_id"] else None,
                decided_by=row["decided_by"],
                reviewer_id=row["reviewer_id"],
                target_type=row["target_type"],
                target_id=row["target_id"],
                decision=row["decision"],
                reason=row["reason"],
                evidence=dict(row["evidence"]),
                data_platform=row["data_platform"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
