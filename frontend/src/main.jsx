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
