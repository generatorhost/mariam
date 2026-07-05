from app.core.events import InMemoryEventBus
from app.core.runtime_objects import RuntimeObject, RuntimeObjectRequest, create_runtime_object
from app.repositories.runtime_objects import RuntimeObjectRepository


class RuntimeObjectService:
    def __init__(
        self,
        event_bus: InMemoryEventBus,
        repository: RuntimeObjectRepository,
    ) -> None:
        self._event_bus = event_bus
        self._repository = repository

    def create(self, request: RuntimeObjectRequest) -> RuntimeObject:
        runtime_object = create_runtime_object(request)
        saved = self._repository.save(runtime_object)
        self._event_bus.publish(
            "runtime_object.registered",
            "runtime-object-service",
            {
                "object_id": saved.object_id,
                "object_type": saved.object_type,
                "name": saved.name,
                "status": saved.status,
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def list(self) -> list[RuntimeObject]:
        return self._repository.list()
