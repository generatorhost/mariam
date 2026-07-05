from typing import Protocol

from app.core.plugin_manifest import PluginManifest


class PluginRepository(Protocol):
    def save(self, plugin: PluginManifest) -> PluginManifest:
        pass

    def list(self) -> list[PluginManifest]:
        pass


class InMemoryPluginRepository:
    def __init__(self) -> None:
        self._plugins: dict[str, PluginManifest] = {}

    def save(self, plugin: PluginManifest) -> PluginManifest:
        self._plugins[plugin.plugin_id] = plugin
        return plugin

    def list(self) -> list[PluginManifest]:
        return list(self._plugins.values())


class PostgresPluginRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def save(self, plugin: PluginManifest) -> PluginManifest:
        import psycopg
        from psycopg.types.json import Jsonb

        manifest = plugin.model_dump()
        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO plugin_manifests (
                        plugin_id,
                        name,
                        version,
                        dashboard_route,
                        api_prefix,
                        data_boundary,
                        manifest,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'registered')
                    ON CONFLICT (plugin_id)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        version = EXCLUDED.version,
                        dashboard_route = EXCLUDED.dashboard_route,
                        api_prefix = EXCLUDED.api_prefix,
                        data_boundary = EXCLUDED.data_boundary,
                        manifest = EXCLUDED.manifest,
                        status = 'registered'
                    """,
                    (
                        plugin.plugin_id,
                        plugin.name,
                        plugin.version,
                        plugin.dashboard_route,
                        plugin.api_prefix,
                        plugin.data_boundary,
                        Jsonb(manifest),
                    ),
                )
        return plugin

    def list(self) -> list[PluginManifest]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT manifest
                    FROM plugin_manifests
                    WHERE status = 'registered'
                    ORDER BY created_at ASC
                    """
                )
                rows = cursor.fetchall()
        return [PluginManifest.model_validate(dict(row["manifest"])) for row in rows]
