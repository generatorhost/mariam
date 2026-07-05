import React, { useState } from 'react';
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

async function startMission() {
  const response = await fetch('http://localhost:8000/api/missions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      plugin_id: 'crm',
      user_request: 'Create a follow-up plan for a qualified lead',
      requested_by: 'command-center',
    }),
  });
  if (!response.ok) {
    throw new Error(`Mission request failed with ${response.status}`);
  }
  return response.json();
}

async function routeAIResource() {
  const response = await fetch('http://localhost:8000/api/ai-resources/route', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      capability: 'chat',
      privacy_preference: 'local_first',
      requested_by: 'command-center',
    }),
  });
  if (!response.ok) {
    throw new Error(`AI resource routing failed with ${response.status}`);
  }
  return response.json();
}

async function registerCRMPlugin() {
  const response = await fetch('http://localhost:8000/api/plugins', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
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
    }),
  });
  if (!response.ok) {
    throw new Error(`Plugin registration failed with ${response.status}`);
  }
  return response.json();
}

async function registerRuntimeObject() {
  const response = await fetch('http://localhost:8000/api/runtime-objects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      object_type: 'provider',
      name: 'Ollama Provider',
      version: '0.1.0',
      manifest: { provider_type: 'model_runtime', local: true },
    }),
  });
  if (!response.ok) {
    throw new Error(`Runtime object registration failed with ${response.status}`);
  }
  return response.json();
}

async function recordAuditDecision() {
  const response = await fetch('http://localhost:8000/api/audit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      actor_id: 'governance-gate',
      action: 'artifact.approve',
      target_type: 'report',
      target_id: 'report-001',
      decision: 'approved',
      evidence: { data_platform: 'DB MARIAM' },
    }),
  });
  if (!response.ok) {
    throw new Error(`Audit record failed with ${response.status}`);
  }
  return response.json();
}

function MissionPanel() {
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
        </div>
      )}
    </section>
  );
}

function AIResourcePanel() {
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

function PluginPanel() {
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

function RuntimeObjectPanel() {
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

function AuditPanel() {
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
        <MissionPanel />
        <AIResourcePanel />
        <PluginPanel />
        <RuntimeObjectPanel />
        <AuditPanel />
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
