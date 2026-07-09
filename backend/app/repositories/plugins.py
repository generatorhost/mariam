from typing import Protocol

from app.core.plugin_manifest import PluginManifest


class PluginRepository(Protocol):
    def save(self, plugin: PluginManifest) -> PluginManifest:
        pass

    def get(self, plugin_id: str) -> PluginManifest | None:
        pass

    def update(self, plugin: PluginManifest) -> PluginManifest:
        pass

    def list(self) -> list[PluginManifest]:
        pass


class InMemoryPluginRepository:
    def __init__(self) -> None:
        self._plugins: dict[str, PluginManifest] = {}

    def save(self, plugin: PluginManifest) -> PluginManifest:
        self._plugins[plugin.plugin_id] = plugin
        return plugin

    def get(self, plugin_id: str) -> PluginManifest | None:
        return self._plugins.get(plugin_id)

    def update(self, plugin: PluginManifest) -> PluginManifest:
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

        plugin = plugin.model_copy(update={"status": plugin.status or "registered"})
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
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (plugin_id)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        version = EXCLUDED.version,
                        dashboard_route = EXCLUDED.dashboard_route,
                        api_prefix = EXCLUDED.api_prefix,
                        data_boundary = EXCLUDED.data_boundary,
                        manifest = EXCLUDED.manifest,
                        status = EXCLUDED.status
                    """,
                    (
                        plugin.plugin_id,
                        plugin.name,
                        plugin.version,
                        plugin.dashboard_route,
                        plugin.api_prefix,
                        plugin.data_boundary,
                        Jsonb(manifest),
                        plugin.status,
                    ),
                )
        return plugin

    def get(self, plugin_id: str) -> PluginManifest | None:
        return next((plugin for plugin in self.list() if plugin.plugin_id == plugin_id), None)

    def update(self, plugin: PluginManifest) -> PluginManifest:
        return self.save(plugin)

    def list(self) -> list[PluginManifest]:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT plugin_id, name, version, dashboard_route, api_prefix, data_boundary, manifest, status
                    FROM plugin_manifests
                    ORDER BY created_at ASC
                    """
                )
                rows = cursor.fetchall()
        return [self._row_to_manifest(dict(row)) for row in rows]

    def _row_to_manifest(self, row: dict) -> PluginManifest:
        manifest = dict(row.get("manifest") or {})
        plugin_id = str(manifest.get("plugin_id") or row["plugin_id"])
        name = str(manifest.get("name") or row["name"] or plugin_id.replace("-", " ").replace("_", " ").title())
        version = str(manifest.get("version") or row["version"] or "0.1.0")
        return PluginManifest.model_validate(
            {
                **manifest,
                "plugin_id": plugin_id,
                "name": name,
                "version": version,
                "status": row.get("status") or manifest.get("status") or "registered",
                "dashboard_route": manifest.get("dashboard_route") or row.get("dashboard_route") or f"/plugins/{plugin_id}",
                "settings_schema": manifest.get("settings_schema") or {},
                "settings_values": manifest.get("settings_values") or {},
                "api_prefix": manifest.get("api_prefix") or row.get("api_prefix") or f"/api/plugins/{plugin_id}",
                "data_boundary": manifest.get("data_boundary") or row.get("data_boundary") or plugin_id,
                "permissions": manifest.get("permissions") or [f"{plugin_id}.read"],
                "produced_events": manifest.get("produced_events") or [],
                "consumed_events": manifest.get("consumed_events") or [],
                "chief_agent_role": manifest.get("chief_agent_role") or f"{name} Chief Agent",
                "swarm_roles": manifest.get("swarm_roles") or [f"{name} Validator"],
                "workflows": manifest.get("workflows") or [],
                "provider_dependencies": manifest.get("provider_dependencies") or [],
                "connector_dependencies": manifest.get("connector_dependencies") or [],
                "runtime_dependencies": manifest.get("runtime_dependencies") or ["event_bus", "audit_log"],
                "tests": manifest.get("tests") or ["api", "runtime", "permissions"],
                "acceptance_criteria": manifest.get("acceptance_criteria")
                or ["Plugin manifest can be read from DB MARIAM without breaking runtime summary."],
                "rollback_plan": manifest.get("rollback_plan") or "Disable plugin and keep DB MARIAM audit evidence.",
            }
        )
