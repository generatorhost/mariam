from typing import Protocol

from app.core.artifacts import Artifact, ArtifactStatus, DeliveryPackage


class ArtifactRepository(Protocol):
    def save(self, artifact: Artifact) -> Artifact:
        pass

    def get(self, artifact_id: str) -> Artifact | None:
        pass

    def update(self, artifact: Artifact) -> Artifact:
        pass

    def list(self) -> list[Artifact]:
        pass


class DeliveryPackageRepository(Protocol):
    def save(self, delivery_package: DeliveryPackage) -> DeliveryPackage:
        pass

    def list(self) -> list[DeliveryPackage]:
        pass


class InMemoryArtifactRepository:
    def __init__(self) -> None:
        self._artifacts: dict[str, Artifact] = {}

    def save(self, artifact: Artifact) -> Artifact:
        self._artifacts[artifact.artifact_id] = artifact
        return artifact

    def get(self, artifact_id: str) -> Artifact | None:
        return self._artifacts.get(artifact_id)

    def update(self, artifact: Artifact) -> Artifact:
        self._artifacts[artifact.artifact_id] = artifact
        return artifact

    def list(self) -> list[Artifact]:
        return list(self._artifacts.values())


class InMemoryDeliveryPackageRepository:
    def __init__(self) -> None:
        self._delivery_packages: dict[str, DeliveryPackage] = {}

    def save(self, delivery_package: DeliveryPackage) -> DeliveryPackage:
        self._delivery_packages[delivery_package.delivery_id] = delivery_package
        return delivery_package

    def list(self) -> list[DeliveryPackage]:
        return list(self._delivery_packages.values())


class PostgresArtifactRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def save(self, artifact: Artifact) -> Artifact:
        import psycopg

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO artifacts (
                        artifact_id,
                        mission_id,
                        plugin_id,
                        title,
                        content,
                        status,
                        data_platform,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (artifact_id)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        content = EXCLUDED.content,
                        status = EXCLUDED.status,
                        data_platform = EXCLUDED.data_platform
                    """,
                    (
                        artifact.artifact_id,
                        artifact.mission_id,
                        artifact.plugin_id,
                        artifact.title,
                        artifact.content,
                        artifact.status.value,
                        artifact.data_platform,
                        artifact.created_at,
                    ),
                )
        return artifact

    def get(self, artifact_id: str) -> Artifact | None:
        return next((artifact for artifact in self.list() if artifact.artifact_id == artifact_id), None)

    def update(self, artifact: Artifact) -> Artifact:
        return self.save(artifact)

    def list(self) -> list[Artifact]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT artifact_id, mission_id, plugin_id, title, content, status, data_platform, created_at
                    FROM artifacts
                    ORDER BY created_at DESC
                    """
                )
                rows = cursor.fetchall()
        return [
            Artifact(
                artifact_id=str(row["artifact_id"]),
                mission_id=str(row["mission_id"]),
                plugin_id=row["plugin_id"],
                title=row["title"],
                content=row["content"],
                status=ArtifactStatus(row["status"]),
                data_platform=row["data_platform"],
                created_at=row["created_at"],
            )
            for row in rows
        ]


class PostgresDeliveryPackageRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def save(self, delivery_package: DeliveryPackage) -> DeliveryPackage:
        import psycopg
        from psycopg.types.json import Jsonb

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO delivery_packages (
                        delivery_id,
                        artifact_id,
                        mission_id,
                        plugin_id,
                        destination,
                        status,
                        package_manifest,
                        data_platform,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        delivery_package.delivery_id,
                        delivery_package.artifact_id,
                        delivery_package.mission_id,
                        delivery_package.plugin_id,
                        delivery_package.destination,
                        delivery_package.status,
                        Jsonb(delivery_package.package_manifest),
                        delivery_package.data_platform,
                        delivery_package.created_at,
                    ),
                )
        return delivery_package

    def list(self) -> list[DeliveryPackage]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        delivery_id,
                        artifact_id,
                        mission_id,
                        plugin_id,
                        destination,
                        status,
                        package_manifest,
                        data_platform,
                        created_at
                    FROM delivery_packages
                    ORDER BY created_at DESC
                    """
                )
                rows = cursor.fetchall()
        return [
            DeliveryPackage(
                delivery_id=str(row["delivery_id"]),
                artifact_id=str(row["artifact_id"]),
                mission_id=str(row["mission_id"]),
                plugin_id=row["plugin_id"],
                destination=row["destination"],
                status=row["status"],
                package_manifest=dict(row["package_manifest"]),
                data_platform=row["data_platform"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
