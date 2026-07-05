from app.core.events import InMemoryEventBus
from app.core.missions import Mission, MissionRequest, create_mission_plan
from app.repositories.missions import MissionRepository


class MissionService:
    def __init__(self, event_bus: InMemoryEventBus, repository: MissionRepository) -> None:
        self._event_bus = event_bus
        self._repository = repository

    def create(self, request: MissionRequest) -> Mission:
        mission = create_mission_plan(request)
        saved = self._repository.save(mission)
        self._event_bus.publish(
            "mission.created",
            "mission-service",
            {
                "mission_id": mission.mission_id,
                "plugin_id": mission.plugin_id,
                "status": mission.status,
                "data_platform": mission.data_platform,
            },
        )
        return saved

    def list(self) -> list[Mission]:
        return self._repository.list()
