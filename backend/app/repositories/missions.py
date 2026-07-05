from __future__ import annotations

from typing import Protocol
from uuid import uuid4

from app.core.missions import Mission, MissionStatus, MissionStep


class MissionRepository(Protocol):
    def save(self, mission: Mission) -> Mission:
        pass

    def get(self, mission_id: str) -> Mission | None:
        pass

    def update(self, mission: Mission) -> Mission:
        pass

    def list(self) -> list[Mission]:
        pass


class InMemoryMissionRepository:
    def __init__(self) -> None:
        self._missions: dict[str, Mission] = {}

    def save(self, mission: Mission) -> Mission:
        self._missions[mission.mission_id] = mission
        return mission

    def get(self, mission_id: str) -> Mission | None:
        return self._missions.get(mission_id)

    def update(self, mission: Mission) -> Mission:
        self._missions[mission.mission_id] = mission
        return mission

    def list(self) -> list[Mission]:
        return list(self._missions.values())


class PostgresMissionRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def save(self, mission: Mission) -> Mission:
        import psycopg

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO missions (
                        mission_id,
                        plugin_id,
                        requested_by,
                        user_request,
                        status,
                        chief_agent,
                        governance_gate,
                        data_platform,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        mission.mission_id,
                        mission.plugin_id,
                        mission.requested_by,
                        mission.user_request,
                        mission.status.value,
                        mission.chief_agent,
                        mission.governance_gate,
                        mission.data_platform,
                        mission.created_at,
                    ),
                )
                for step_order, step in enumerate(mission.steps, start=1):
                    cursor.execute(
                        """
                        INSERT INTO mission_steps (
                            step_id,
                            mission_id,
                            step_order,
                            name,
                            actor,
                            result,
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            str(uuid4()),
                            mission.mission_id,
                            step_order,
                            step.name,
                            step.actor,
                            step.result,
                            mission.created_at,
                        ),
                    )
        return mission

    def get(self, mission_id: str) -> Mission | None:
        return next((mission for mission in self.list() if mission.mission_id == mission_id), None)

    def update(self, mission: Mission) -> Mission:
        import psycopg

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE missions
                    SET status = %s
                    WHERE mission_id = %s
                    """,
                    (mission.status.value, mission.mission_id),
                )
        return mission

    def list(self) -> list[Mission]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        mission_id,
                        plugin_id,
                        requested_by,
                        user_request,
                        status,
                        chief_agent,
                        governance_gate,
                        data_platform,
                        created_at
                    FROM missions
                    ORDER BY created_at DESC
                    """
                )
                mission_rows = cursor.fetchall()
                cursor.execute(
                    """
                    SELECT mission_id, name, actor, result
                    FROM mission_steps
                    ORDER BY mission_id ASC, step_order ASC
                    """
                )
                step_rows = cursor.fetchall()
        steps_by_mission: dict[str, list[MissionStep]] = {}
        for row in step_rows:
            mission_id = str(row["mission_id"])
            steps_by_mission.setdefault(mission_id, []).append(
                MissionStep(name=row["name"], actor=row["actor"], result=row["result"])
            )
        return [self._row_to_mission(row, steps_by_mission) for row in mission_rows]

    def _row_to_mission(
        self,
        row: dict,
        steps_by_mission: dict[str, list[MissionStep]],
    ) -> Mission:
        mission_id = str(row["mission_id"])
        return Mission(
            mission_id=mission_id,
            plugin_id=row["plugin_id"],
            user_request=row["user_request"],
            requested_by=row["requested_by"],
            status=MissionStatus(row["status"]),
            chief_agent=row["chief_agent"],
            governance_gate=row["governance_gate"],
            data_platform=row["data_platform"],
            steps=steps_by_mission.get(mission_id, []),
            created_at=row["created_at"],
        )
