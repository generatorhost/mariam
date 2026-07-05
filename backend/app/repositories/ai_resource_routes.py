from typing import Protocol

from app.core.ai_resources import PROVIDERS, ResourceRouteDecision


class AIResourceRouteRepository(Protocol):
    def save(self, decision: ResourceRouteDecision) -> ResourceRouteDecision:
        pass

    def list(self) -> list[ResourceRouteDecision]:
        pass


class InMemoryAIResourceRouteRepository:
    def __init__(self) -> None:
        self._routes: list[ResourceRouteDecision] = []

    def save(self, decision: ResourceRouteDecision) -> ResourceRouteDecision:
        self._routes.append(decision)
        return decision

    def list(self) -> list[ResourceRouteDecision]:
        return list(self._routes)


class PostgresAIResourceRouteRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def save(self, decision: ResourceRouteDecision) -> ResourceRouteDecision:
        import psycopg

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO ai_resource_routes (
                        route_id,
                        capability,
                        selected_provider_id,
                        policy,
                        reason,
                        requested_by,
                        data_platform,
                        fallback_provider_ids,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        decision.route_id,
                        decision.capability,
                        decision.selected_provider.provider_id,
                        decision.policy,
                        decision.reason,
                        decision.requested_by,
                        decision.data_platform,
                        decision.fallback_provider_ids,
                        decision.created_at,
                    ),
                )
        return decision

    def list(self) -> list[ResourceRouteDecision]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        route_id,
                        capability,
                        selected_provider_id,
                        policy,
                        reason,
                        requested_by,
                        data_platform,
                        fallback_provider_ids,
                        created_at
                    FROM ai_resource_routes
                    ORDER BY created_at DESC
                    """
                )
                rows = cursor.fetchall()
        return [self._row_to_decision(row) for row in rows]

    def _row_to_decision(self, row: dict) -> ResourceRouteDecision:
        provider = next(
            provider for provider in PROVIDERS if provider.provider_id == row["selected_provider_id"]
        )
        return ResourceRouteDecision(
            route_id=str(row["route_id"]),
            capability=row["capability"],
            selected_provider=provider,
            reason=row["reason"],
            policy=row["policy"],
            requested_by=row["requested_by"],
            data_platform=row["data_platform"],
            fallback_provider_ids=list(row["fallback_provider_ids"]),
            created_at=row["created_at"],
        )
