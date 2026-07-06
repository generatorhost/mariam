import React, { useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, Boxes, CheckCircle2, Database, ShieldCheck } from 'lucide-react';
import './styles.css';

const cards = [
  { title: 'Runtime Core', value: 'Healthy', icon: Activity },
  { title: 'Plugins / Apps', value: 'Manifest-driven', icon: Boxes },
  { title: 'DB MARIAM', value: 'Postgres / Redis / MinIO boundary', icon: Database },
  { title: 'Governance', value: 'Permission + audit gates', icon: ShieldCheck },
];

const terms = [
  'Mariam Living Enterprise OS Core',
  'Mariam Data Platform',
  'Plugin Business Unit',
  'DNA Managed Runtime Object',
  'Governance Gate',
];

const apiBaseUrl = import.meta.env.VITE_MARIAM_API_BASE_URL || 'http://localhost:8000';

async function apiRequest(path, body, options = {}) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: options.method || 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API request to ${path} failed with ${response.status}`);
  }
  return response.json();
}

async function apiGet(path) {
  const response = await fetch(`${apiBaseUrl}${path}`);
  if (!response.ok) {
    throw new Error(`API request to ${path} failed with ${response.status}`);
  }
  return response.json();
}

async function loadSystemStatus() {
  const summary = await apiGet('/api/runtime/summary');
  return {
    health: summary.health,
    runtimeObjects: summary.runtime_objects,
    plugins: summary.plugins,
    events: summary.runtime_events,
    auditRecords: summary.audit_records,
    missions: summary.missions,
    aiRoutes: summary.ai_routes,
    recentEvents: summary.recent_events || [],
  };
}

async function loadMissions() {
  const body = await apiGet('/api/missions');
  return (body.missions || []).sort(
    (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
  );
}

async function loadAuditRecords() {
  const body = await apiGet('/api/audit');
  return (body.audit_records || []).sort(
    (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
  );
}

async function loadAIRoutes() {
  const body = await apiGet('/api/ai-resources/routes');
  return (body.routes || []).sort(
    (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
  );
}

async function loadPlugins() {
  const body = await apiGet('/api/plugins');
  return body.plugins || [];
}

async function loadRuntimeObjects() {
  const body = await apiGet('/api/runtime-objects');
  return (body.runtime_objects || []).sort(
    (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
  );
}

async function startMission() {
  return apiRequest('/api/missions', {
    plugin_id: 'crm',
    user_request: 'Create a follow-up plan for a qualified lead',
    requested_by: 'command-center',
  });
}

async function approveMission(missionId) {
  return apiRequest(`/api/missions/${missionId}/approve`, {
    approved_by: 'command-center-governance',
    evidence: { review: 'Approved from Command Center mission panel' },
  });
}

async function rejectMission(missionId) {
  return apiRequest(`/api/missions/${missionId}/reject`, {
    rejected_by: 'command-center-governance',
    reason: 'Rejected from Command Center governance panel for revision.',
    evidence: { review: 'Rejected before delivery export' },
  });
}

async function routeAIResource() {
  return apiRequest('/api/ai-resources/route', {
    capability: 'chat',
    privacy_preference: 'local_first',
    requested_by: 'command-center',
  });
}

async function registerCRMPlugin() {
  return apiRequest('/api/plugins', {
    plugin_id: 'crm',
    name: 'CRM Workspace',
    version: '0.1.0',
    dashboard_route: '/plugins/crm',
    settings_schema: {
      type: 'object',
      properties: {
        pipelineStages: { type: 'array', items: { type: 'string' } },
      },
    },
    api_prefix: '/api/plugins/crm',
    data_boundary: 'private-plugin-tables',
    permissions: ['crm.read', 'crm.write', 'crm.approve'],
    produced_events: ['crm.lead.created', 'crm.pipeline.updated'],
    consumed_events: ['communication.message.received', 'opportunity.detected'],
    chief_agent_role: 'CRM Chief Agent',
    swarm_roles: ['Lead Qualifier', 'Pipeline Planner', 'Client Follow-up Reviewer'],
    workflows: ['lead-intake', 'pipeline-review', 'client-follow-up'],
    provider_dependencies: [],
    connector_dependencies: ['email', 'whatsapp'],
    runtime_dependencies: ['event_bus', 'audit_log', 'mariam_data_platform'],
    tests: ['api', 'runtime', 'permissions', 'data-boundary'],
    acceptance_criteria: [
      'Plugin registers through the runtime registry.',
      'Plugin declares dashboard, settings, permissions, workflows, and rollback.',
      'Plugin data is isolated from the core runtime tables.',
    ],
    rollback_plan:
      'Disable plugin routes and workers, keep CRM data read-only, and emit plugin.rollback.started.',
  });
}

async function registerRuntimeObject() {
  return apiRequest('/api/runtime-objects', {
    object_type: 'provider',
    name: 'Ollama Provider',
    version: '0.1.0',
    manifest: { provider_type: 'model_runtime', local: true },
  });
}

async function enableRuntimeObject(objectId) {
  return apiRequest(`/api/runtime-objects/${objectId}/enable`, {
    actor_id: 'command-center-runtime-governance',
    reason: 'Enabled from Command Center Runtime Object History.',
    evidence: { review: 'operator-enabled-runtime-object' },
  });
}

async function disableRuntimeObject(objectId) {
  return apiRequest(`/api/runtime-objects/${objectId}/disable`, {
    actor_id: 'command-center-runtime-governance',
    reason: 'Disabled from Command Center Runtime Object History.',
    evidence: { review: 'operator-disabled-runtime-object' },
  });
}

async function deleteRuntimeObject(objectId) {
  return apiRequest(`/api/runtime-objects/${objectId}/delete`, {
    actor_id: 'command-center-runtime-governance',
    reason: 'Soft deleted from Command Center Runtime Object History.',
    evidence: { review: 'operator-soft-deleted-runtime-object' },
  });
}

async function restoreRuntimeObject(objectId) {
  return apiRequest(`/api/runtime-objects/${objectId}/restore`, {
    actor_id: 'command-center-runtime-governance',
    reason: 'Restored from Command Center Runtime Object History for review.',
    evidence: { review: 'operator-restored-runtime-object' },
  });
}

async function upgradeRuntimeObject(objectId) {
  return apiRequest(`/api/runtime-objects/${objectId}`, {
    actor_id: 'command-center-runtime-governance',
    reason: 'Upgraded runtime object metadata from Command Center.',
    version: '0.2.0',
    manifest_updates: {
      benchmark: 'command-center-smoke-test-passed',
      compatibility_review: 'passed',
    },
    evidence: { review: 'operator-upgraded-runtime-object' },
  }, { method: 'PATCH' });
}

async function rollbackRuntimeObject(objectId) {
  return apiRequest(`/api/runtime-objects/${objectId}/rollback`, {
    actor_id: 'command-center-runtime-governance',
    reason: 'Rolled back runtime object from Command Center.',
    evidence: { review: 'operator-rolled-back-runtime-object' },
  });
}

async function recordAuditDecision() {
  return apiRequest('/api/audit', {
    actor_id: 'governance-gate',
    action: 'artifact.approve',
    target_type: 'report',
    target_id: 'report-001',
    decision: 'approved',
    evidence: { data_platform: 'DB MARIAM' },
  });
}

function RuntimeObjectHistoryPanel({ refreshVersion, onActionComplete }) {
  const [runtimeObjects, setRuntimeObjects] = useState([]);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshRuntimeObjects = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setRuntimeObjects((await loadRuntimeObjects()).slice(0, 5));
      setStatus('ready');
    } catch (runtimeError) {
      setStatus('error');
      setError(runtimeError.message);
    }
  }, []);

  useEffect(() => {
    refreshRuntimeObjects();
  }, [refreshRuntimeObjects, refreshVersion]);

  const handleStateChange = async (objectId, nextState) => {
    setStatus('loading');
    setError('');
    try {
      if (nextState === 'enabled') {
        await enableRuntimeObject(objectId);
      } else if (nextState === 'disabled') {
        await disableRuntimeObject(objectId);
      } else if (nextState === 'deleted') {
        await deleteRuntimeObject(objectId);
      } else if (nextState === 'upgraded') {
        await upgradeRuntimeObject(objectId);
      } else if (nextState === 'rollback') {
        await rollbackRuntimeObject(objectId);
      } else {
        await restoreRuntimeObject(objectId);
      }
      await refreshRuntimeObjects();
      onActionComplete();
    } catch (runtimeError) {
      setStatus('error');
      setError(runtimeError.message);
    }
  };

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Runtime Object History</h2>
        <p>Review governed runtime objects registered under DB MARIAM.</p>
      </div>
      <button onClick={refreshRuntimeObjects} disabled={status === 'loading'}>
        {status === 'loading' ? 'Loading...' : 'Refresh Runtime Objects'}
      </button>
      {error && <p className="error">{error}</p>}
      <div className="runtime-object-history">
        {runtimeObjects.length ? (
          runtimeObjects.map((item) => (
            <article key={item.object_id}>
              <strong>{item.name}</strong>
              <span>{item.object_type}</span>
              <p>
                {item.status} / v{item.version}
              </p>
              <time>{new Date(item.created_at).toLocaleString()}</time>
              <div className="mission-actions">
                {item.status === 'deleted' ? (
                  <button
                    onClick={() => handleStateChange(item.object_id, 'restored')}
                    disabled={status === 'loading'}
                  >
                    Restore
                  </button>
                ) : item.status === 'enabled' ? (
                  <button
                    onClick={() => handleStateChange(item.object_id, 'disabled')}
                    disabled={status === 'loading'}
                  >
                    Disable
                  </button>
                ) : (
                  <button
                    onClick={() => handleStateChange(item.object_id, 'enabled')}
                    disabled={status === 'loading'}
                  >
                    Enable
                  </button>
                )}
                {item.status !== 'deleted' && (
                  <>
                    <button
                      onClick={() => handleStateChange(item.object_id, 'upgraded')}
                      disabled={status === 'loading' || item.version === '0.2.0'}
                    >
                      Upgrade
                    </button>
                    {(item.manifest?._rollback_stack || []).length > 0 && (
                      <button
                        onClick={() => handleStateChange(item.object_id, 'rollback')}
                        disabled={status === 'loading'}
                      >
                        Rollback
                      </button>
                    )}
                    <button
                      onClick={() => handleStateChange(item.object_id, 'deleted')}
                      disabled={status === 'loading'}
                    >
                      Delete
                    </button>
                  </>
                )}
              </div>
            </article>
          ))
        ) : (
          <p>No runtime objects registered yet.</p>
        )}
      </div>
    </section>
  );
}

function PluginHistoryPanel({ refreshVersion }) {
  const [plugins, setPlugins] = useState([]);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshPlugins = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setPlugins((await loadPlugins()).slice(0, 5));
      setStatus('ready');
    } catch (pluginError) {
      setStatus('error');
      setError(pluginError.message);
    }
  }, []);

  useEffect(() => {
    refreshPlugins();
  }, [refreshPlugins, refreshVersion]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Plugin Registry History</h2>
        <p>Review registered Plugin-managed Business Units from the runtime registry.</p>
      </div>
      <button onClick={refreshPlugins} disabled={status === 'loading'}>
        {status === 'loading' ? 'Loading...' : 'Refresh Plugin Registry'}
      </button>
      {error && <p className="error">{error}</p>}
      <div className="plugin-history">
        {plugins.length ? (
          plugins.map((plugin) => (
            <article key={plugin.plugin_id}>
              <strong>{plugin.name}</strong>
              <span>v{plugin.version}</span>
              <p>{plugin.chief_agent_role}</p>
              <p>{plugin.dashboard_route}</p>
              <time>{plugin.data_boundary}</time>
            </article>
          ))
        ) : (
          <p>No plugins registered yet.</p>
        )}
      </div>
    </section>
  );
}

function AIRouteHistoryPanel({ refreshVersion }) {
  const [routes, setRoutes] = useState([]);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshRoutes = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setRoutes((await loadAIRoutes()).slice(0, 5));
      setStatus('ready');
    } catch (routeError) {
      setStatus('error');
      setError(routeError.message);
    }
  }, []);

  useEffect(() => {
    refreshRoutes();
  }, [refreshRoutes, refreshVersion]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>AI Route History</h2>
        <p>Review recent provider routing decisions from the AI Resource Manager.</p>
      </div>
      <button onClick={refreshRoutes} disabled={status === 'loading'}>
        {status === 'loading' ? 'Loading...' : 'Refresh AI Route History'}
      </button>
      {error && <p className="error">{error}</p>}
      <div className="route-history">
        {routes.length ? (
          routes.map((route) => (
            <article key={route.route_id}>
              <strong>{route.selected_provider.name}</strong>
              <span>{route.capability}</span>
              <p>{route.reason}</p>
              <time>{new Date(route.created_at).toLocaleString()}</time>
            </article>
          ))
        ) : (
          <p>No AI route decisions recorded yet.</p>
        )}
      </div>
    </section>
  );
}

function AuditHistoryPanel({ refreshVersion }) {
  const [records, setRecords] = useState([]);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshAuditRecords = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setRecords((await loadAuditRecords()).slice(0, 5));
      setStatus('ready');
    } catch (auditError) {
      setStatus('error');
      setError(auditError.message);
    }
  }, []);

  useEffect(() => {
    refreshAuditRecords();
  }, [refreshAuditRecords, refreshVersion]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Audit History</h2>
        <p>Review recent governance decisions recorded in DB MARIAM.</p>
      </div>
      <button onClick={refreshAuditRecords} disabled={status === 'loading'}>
        {status === 'loading' ? 'Loading...' : 'Refresh Audit History'}
      </button>
      {error && <p className="error">{error}</p>}
      <div className="audit-history">
        {records.length ? (
          records.map((record) => (
            <article key={record.audit_id}>
              <strong>{record.decision}</strong>
              <span>{record.action}</span>
              <p>
                {record.actor_id} on {record.target_type} {record.target_id}
              </p>
              <time>{new Date(record.created_at).toLocaleString()}</time>
            </article>
          ))
        ) : (
          <p>No audit records found yet.</p>
        )}
      </div>
    </section>
  );
}

function MissionHistoryPanel({ refreshVersion, onActionComplete }) {
  const [missions, setMissions] = useState([]);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshMissions = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setMissions((await loadMissions()).slice(0, 5));
      setStatus('ready');
    } catch (missionError) {
      setStatus('error');
      setError(missionError.message);
    }
  }, []);

  useEffect(() => {
    refreshMissions();
  }, [refreshMissions, refreshVersion]);

  async function handleHistoryDecision(missionId, decision) {
    setStatus('loading');
    setError('');
    try {
      if (decision === 'approve') {
        await approveMission(missionId);
      } else {
        await rejectMission(missionId);
      }
      await refreshMissions();
      onActionComplete();
    } catch (missionError) {
      setStatus('error');
      setError(missionError.message);
    }
  }

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Mission History</h2>
        <p>Review recent governed missions from the backend mission repository.</p>
      </div>
      <button onClick={refreshMissions} disabled={status === 'loading'}>
        {status === 'loading' ? 'Loading...' : 'Refresh Mission History'}
      </button>
      {error && <p className="error">{error}</p>}
      <div className="mission-history">
        {missions.length ? (
          missions.map((item) => (
            <article key={item.mission_id}>
              <strong>{item.status}</strong>
              <span>{item.chief_agent}</span>
              <p>{item.user_request}</p>
              <time>{new Date(item.created_at).toLocaleString()}</time>
              {item.status === 'awaiting_approval' && (
                <div className="mission-actions">
                  <button
                    onClick={() => handleHistoryDecision(item.mission_id, 'approve')}
                    disabled={status === 'loading'}
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => handleHistoryDecision(item.mission_id, 'reject')}
                    disabled={status === 'loading'}
                  >
                    Reject
                  </button>
                </div>
              )}
            </article>
          ))
        ) : (
          <p>No missions recorded yet.</p>
        )}
      </div>
    </section>
  );
}

function SystemStatusPanel({ refreshVersion }) {
  const [summary, setSummary] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshSummary = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setSummary(await loadSystemStatus());
      setStatus('ready');
    } catch (statusError) {
      setStatus('error');
      setError(statusError.message);
    }
  }, []);

  useEffect(() => {
    refreshSummary();
  }, [refreshSummary, refreshVersion]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>System Status</h2>
        <p>Refresh live command center counts from the backend runtime summary API.</p>
      </div>
      <button onClick={refreshSummary} disabled={status === 'loading'}>
        {status === 'loading' ? 'Refreshing...' : 'Refresh System Status'}
      </button>
      {error && <p className="error">{error}</p>}
      {summary && (
        <>
          <div className="status-grid">
            <div><strong>{summary.health}</strong><span>Health</span></div>
            <div><strong>{summary.runtimeObjects}</strong><span>Runtime Objects</span></div>
            <div><strong>{summary.plugins}</strong><span>Plugins</span></div>
            <div><strong>{summary.missions}</strong><span>Missions</span></div>
            <div><strong>{summary.aiRoutes}</strong><span>AI Routes</span></div>
            <div><strong>{summary.auditRecords}</strong><span>Audit Records</span></div>
            <div><strong>{summary.events}</strong><span>Runtime Events</span></div>
          </div>
          <div className="activity-feed">
            <h3>Recent Runtime Activity</h3>
            {summary.recentEvents.length ? (
              <ol>
                {summary.recentEvents.map((event) => (
                  <li key={event.event_id}>
                    <strong>{event.name}</strong>
                    <span>{event.source}</span>
                    <time>{new Date(event.created_at).toLocaleString()}</time>
                  </li>
                ))}
              </ol>
            ) : (
              <p>No runtime activity recorded yet.</p>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function MissionPanel({ onActionComplete }) {
  const [mission, setMission] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  async function handleStartMission() {
    setStatus('loading');
    setError('');
    try {
      const body = await startMission();
      setMission(body.mission);
      setStatus('ready');
      onActionComplete();
    } catch (missionError) {
      setStatus('error');
      setError(missionError.message);
    }
  }

  async function handleApproveMission() {
    if (!mission) {
      return;
    }
    setStatus('loading');
    setError('');
    try {
      const body = await approveMission(mission.mission_id);
      setMission(body.mission);
      setStatus('ready');
      onActionComplete();
    } catch (missionError) {
      setStatus('error');
      setError(missionError.message);
    }
  }

  async function handleRejectMission() {
    if (!mission) {
      return;
    }
    setStatus('loading');
    setError('');
    try {
      const body = await rejectMission(mission.mission_id);
      setMission(body.mission);
      setStatus('ready');
      onActionComplete();
    } catch (missionError) {
      setStatus('error');
      setError(missionError.message);
    }
  }

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Mission Flow</h2>
        <p>Press the button to create a governed CRM mission through the backend API.</p>
      </div>
      <button onClick={handleStartMission} disabled={status === 'loading'}>
        {status === 'loading' ? 'Starting...' : 'Start CRM Mission'}
      </button>
      {error && <p className="error">{error}</p>}
      {mission && (
        <div className="mission-result">
          <h3>{mission.chief_agent}</h3>
          <p>
            Mission <strong>{mission.mission_id}</strong> is <strong>{mission.status}</strong> in{' '}
            <strong>{mission.data_platform}</strong>.
          </p>
          <ol>
            {mission.steps.map((step) => (
              <li key={step.name}>
                <CheckCircle2 size={16} />
                <span>
                  <strong>{step.actor}</strong>: {step.result}
                </span>
              </li>
            ))}
          </ol>
          {mission.status === 'awaiting_approval' && (
            <div className="mission-actions">
              <button onClick={handleApproveMission} disabled={status === 'loading'}>
                {status === 'loading' ? 'Approving...' : 'Approve Mission'}
              </button>
              <button onClick={handleRejectMission} disabled={status === 'loading'}>
                {status === 'loading' ? 'Rejecting...' : 'Reject Mission'}
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function AIResourcePanel({ onActionComplete }) {
  const [decision, setDecision] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  async function handleRoute() {
    setStatus('loading');
    setError('');
    try {
      const body = await routeAIResource();
      setDecision(body.decision);
      setStatus('ready');
      onActionComplete();
    } catch (routeError) {
      setStatus('error');
      setError(routeError.message);
    }
  }

  return (
    <section className="panel mission-panel">
      <div>
        <h2>AI Resource Manager</h2>
        <p>Chief Agents request capabilities; the AI Resource Manager selects the provider.</p>
      </div>
      <button onClick={handleRoute} disabled={status === 'loading'}>
        {status === 'loading' ? 'Routing...' : 'Route AI Capability'}
      </button>
      {error && <p className="error">{error}</p>}
      {decision && (
        <div className="mission-result">
          <h3>{decision.selected_provider.name}</h3>
          <p>
            Route <strong>{decision.route_id}</strong> was recorded at{' '}
            <strong>{new Date(decision.created_at).toLocaleString()}</strong>.
          </p>
          <p>
            Requested by <strong>{decision.requested_by}</strong> under{' '}
            <strong>{decision.data_platform}</strong>.
          </p>
          <p>
            Capability <strong>{decision.capability}</strong> is routed to{' '}
            <strong>{decision.selected_provider.provider_type}</strong>.
          </p>
          <p>{decision.reason}</p>
          <p>
            Fallbacks:{' '}
            {decision.fallback_provider_ids.length
              ? decision.fallback_provider_ids.join(', ')
              : 'none'}
          </p>
        </div>
      )}
    </section>
  );
}

function PluginPanel({ onActionComplete }) {
  const [plugin, setPlugin] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  async function handleRegisterPlugin() {
    setStatus('loading');
    setError('');
    try {
      const body = await registerCRMPlugin();
      setPlugin(body.plugin);
      setStatus('ready');
      onActionComplete();
    } catch (pluginError) {
      setStatus('error');
      setError(pluginError.message);
    }
  }

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Plugin Registry</h2>
        <p>Register the CRM workspace as a Plugin-managed Business Unit.</p>
      </div>
      <button onClick={handleRegisterPlugin} disabled={status === 'loading'}>
        {status === 'loading' ? 'Registering...' : 'Register CRM Plugin'}
      </button>
      {error && <p className="error">{error}</p>}
      {plugin && (
        <div className="mission-result">
          <h3>{plugin.name}</h3>
          <p>
            Plugin <strong>{plugin.plugin_id}</strong> exposes{' '}
            <strong>{plugin.dashboard_route}</strong>.
          </p>
          <p>
            <strong>{plugin.chief_agent_role}</strong> owns a{' '}
            <strong>{plugin.data_boundary}</strong> boundary.
          </p>
        </div>
      )}
    </section>
  );
}

function RuntimeObjectPanel({ onActionComplete }) {
  const [runtimeObject, setRuntimeObject] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  async function handleRegister() {
    setStatus('loading');
    setError('');
    try {
      const body = await registerRuntimeObject();
      setRuntimeObject(body.runtime_object);
      setStatus('ready');
      onActionComplete();
    } catch (runtimeError) {
      setStatus('error');
      setError(runtimeError.message);
    }
  }

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Runtime Object Registry</h2>
        <p>Register a provider as a governed runtime object stored under DB MARIAM.</p>
      </div>
      <button onClick={handleRegister} disabled={status === 'loading'}>
        {status === 'loading' ? 'Registering...' : 'Register Runtime Object'}
      </button>
      {error && <p className="error">{error}</p>}
      {runtimeObject && (
        <div className="mission-result">
          <h3>{runtimeObject.name}</h3>
          <p>
            Object <strong>{runtimeObject.object_id}</strong> is{' '}
            <strong>{runtimeObject.status}</strong> as{' '}
            <strong>{runtimeObject.object_type}</strong>.
          </p>
          <p>
            Version <strong>{runtimeObject.version}</strong> is recorded in{' '}
            <strong>{runtimeObject.data_platform}</strong>.
          </p>
        </div>
      )}
    </section>
  );
}

function AuditPanel({ onActionComplete }) {
  const [auditRecord, setAuditRecord] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  async function handleAudit() {
    setStatus('loading');
    setError('');
    try {
      const body = await recordAuditDecision();
      setAuditRecord(body.audit_record);
      setStatus('ready');
      onActionComplete();
    } catch (auditError) {
      setStatus('error');
      setError(auditError.message);
    }
  }

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Governance Audit</h2>
        <p>Record a governed approval decision through the backend audit API.</p>
      </div>
      <button onClick={handleAudit} disabled={status === 'loading'}>
        {status === 'loading' ? 'Recording...' : 'Record Audit Decision'}
      </button>
      {error && <p className="error">{error}</p>}
      {auditRecord && (
        <div className="mission-result">
          <h3>{auditRecord.decision}</h3>
          <p>
            Audit <strong>{auditRecord.audit_id}</strong> recorded{' '}
            <strong>{auditRecord.action}</strong> for{' '}
            <strong>{auditRecord.target_type}</strong>.
          </p>
          <p>
            Actor <strong>{auditRecord.actor_id}</strong> wrote evidence to{' '}
            <strong>{auditRecord.data_platform}</strong>.
          </p>
        </div>
      )}
    </section>
  );
}

function App() {
  const [refreshVersion, setRefreshVersion] = useState(0);
  const refreshCommandCenterSummary = useCallback(() => {
    setRefreshVersion((current) => current + 1);
  }, []);

  return (
    <main className="shell">
      <aside className="sidebar">
        <strong>Mariam</strong>
        <span>Command Center</span>
      </aside>
      <section className="workspace">
        <header className="topbar">
          <div>
            <h1>Mariam AI Enterprise OS</h1>
            <p>Documentation-driven rebuild foundation</p>
          </div>
          <a href="https://github.com/generatorhost/Mariam-Architecture-Library">Architecture Library</a>
        </header>
        <section className="grid">
          {cards.map((card) => {
            const Icon = card.icon;
            return (
              <article className="card" key={card.title}>
                <Icon size={22} />
                <h2>{card.title}</h2>
                <p>{card.value}</p>
              </article>
            );
          })}
        </section>
        <SystemStatusPanel refreshVersion={refreshVersion} />
        <MissionPanel onActionComplete={refreshCommandCenterSummary} />
        <MissionHistoryPanel
          refreshVersion={refreshVersion}
          onActionComplete={refreshCommandCenterSummary}
        />
        <AIResourcePanel onActionComplete={refreshCommandCenterSummary} />
        <AIRouteHistoryPanel refreshVersion={refreshVersion} />
        <PluginPanel onActionComplete={refreshCommandCenterSummary} />
        <PluginHistoryPanel refreshVersion={refreshVersion} />
        <RuntimeObjectPanel onActionComplete={refreshCommandCenterSummary} />
        <RuntimeObjectHistoryPanel
          refreshVersion={refreshVersion}
          onActionComplete={refreshCommandCenterSummary}
        />
        <AuditPanel onActionComplete={refreshCommandCenterSummary} />
        <AuditHistoryPanel refreshVersion={refreshVersion} />
        <section className="panel">
          <h2>Plugin/App Rule</h2>
          <p>
            Every plugin or app must declare a manifest, dashboard, settings, Chief Agent,
            swarm roles, permissions, data boundary, workflows, tests, and rollback plan.
          </p>
        </section>
        <section className="panel">
          <h2>Official Terms</h2>
          <div className="terms">
            {terms.map((term) => (
              <span key={term}>{term}</span>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
