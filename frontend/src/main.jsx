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

async function loadSystemReadiness() {
  return apiGet('/api/runtime/readiness');
}

async function loadVerificationReport() {
  return apiGet('/api/runtime/verification-report');
}

async function recordVerificationSnapshot() {
  return apiRequest('/api/runtime/verification-report/record', {
    actor_id: 'command-center-verifier',
    evidence: { source: 'command-center-verification-report' },
  });
}

async function loadVerificationSnapshots() {
  const body = await apiGet('/api/runtime/verification-report/snapshots');
  return body.snapshots || [];
}

async function loadRuntimeDiagnostics() {
  return apiGet('/api/runtime/diagnostics');
}

async function loadUsageGuide() {
  return apiGet('/api/runtime/usage-guide');
}

async function loadCompletionReport() {
  return apiGet('/api/runtime/completion-report');
}

async function exportUsageGuide() {
  return apiRequest('/api/runtime/usage-guide/export', {});
}

async function exportRuntimeDiagnostics() {
  return apiRequest('/api/runtime/diagnostics/export', {});
}

async function loadMissions() {
  const body = await apiGet('/api/missions');
  return (body.missions || []).sort(
    (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
  );
}

async function loadDeliveryPackages() {
  const body = await apiGet('/api/artifacts/deliveries');
  return (body.delivery_packages || []).sort(
    (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
  );
}

async function loadQualityReviews() {
  const body = await apiGet('/api/artifacts/quality-reviews');
  return (body.quality_reviews || []).sort(
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

async function loadPluginTimeline(pluginId) {
  return apiGet(`/api/plugins/${pluginId}/timeline`);
}

async function loadPluginDashboard(pluginId) {
  return apiGet(`/api/plugins/${pluginId}/dashboard`);
}

async function updatePluginSettings(pluginId) {
  return apiRequest(`/api/plugins/${pluginId}/settings`, {
    actor_id: 'command-center-plugin-governance',
    reason: 'Updated Plugin-managed Business Unit settings from Command Center.',
    settings: { pipelineStages: ['new', 'qualified', 'proposal', 'won'] },
    evidence: { review: 'operator-updated-plugin-settings' },
  }, { method: 'PATCH' });
}

async function sendPluginChatRequest(pluginId) {
  return apiRequest(`/api/plugins/${pluginId}/chat`, {
    requested_by: 'command-center-user',
    user_request: 'Prepare a follow-up plan for a qualified CRM lead.',
    evidence: { source: 'command-center-plugin-chat' },
  });
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

async function generateArtifactFromMission(missionId) {
  return apiRequest(`/api/artifacts/from-mission/${missionId}`, {});
}

async function approveArtifact(artifactId) {
  return apiRequest(`/api/artifacts/${artifactId}/approve`, {
    approved_by: 'command-center-artifact-governance',
    evidence: { review: 'Approved from Command Center artifact panel' },
  });
}

async function rejectArtifact(artifactId) {
  return apiRequest(`/api/artifacts/${artifactId}/reject`, {
    rejected_by: 'command-center-artifact-governance',
    reason: 'Artifact needs revisions before client delivery.',
    evidence: { review: 'Rejected from Command Center artifact panel' },
  });
}

async function reviewArtifactQuality(artifactId) {
  return apiRequest(`/api/artifacts/${artifactId}/quality-review`, {
    reviewed_by: 'command-center-quality-governance',
    evidence: { quality: 'Reviewed from Command Center artifact panel' },
  });
}

async function packageArtifactDelivery(artifactId) {
  return apiRequest(`/api/artifacts/${artifactId}/package-delivery`, {
    packaged_by: 'command-center-delivery-governance',
    destination: 'client-review-channel',
    evidence: { delivery: 'Packaged from Command Center artifact panel' },
  });
}

async function confirmDeliveryPackage(deliveryId) {
  return apiRequest(`/api/artifacts/deliveries/${deliveryId}/confirm`, {
    delivered_by: 'command-center-delivery-governance',
    client_reference: 'client-confirmed-from-command-center',
    evidence: { delivery: 'Confirmed from Command Center delivery history' },
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

async function enablePlugin(pluginId) {
  return apiRequest(`/api/plugins/${pluginId}/enable`, {
    actor_id: 'command-center-plugin-governance',
    reason: 'Enabled Plugin-managed Business Unit from Command Center.',
    evidence: { review: 'operator-enabled-plugin' },
  });
}

async function validatePlugin(pluginId) {
  return apiRequest(`/api/plugins/${pluginId}/validate`, {
    actor_id: 'command-center-plugin-governance',
    reason: 'Validated Plugin-managed Business Unit from Command Center.',
    evidence: { review: 'operator-validated-plugin' },
  });
}

async function upgradePlugin(pluginId) {
  return apiRequest(`/api/plugins/${pluginId}`, {
    actor_id: 'command-center-plugin-governance',
    reason: 'Upgraded Plugin-managed Business Unit manifest from Command Center.',
    version: '0.2.0',
    permissions: ['crm.read', 'crm.write', 'crm.approve', 'crm.export'],
    workflows: ['lead-intake', 'pipeline-review', 'client-follow-up', 'crm-export'],
    tests: ['api', 'runtime', 'permissions', 'data-boundary', 'upgrade'],
    acceptance_criteria: [
      'Plugin registers through the runtime registry.',
      'Plugin declares data boundary after upgrade.',
      'Plugin requires revalidation after upgrade.',
    ],
    evidence: { upgrade: 'operator-upgraded-plugin' },
  }, { method: 'PATCH' });
}

async function disablePlugin(pluginId) {
  return apiRequest(`/api/plugins/${pluginId}/disable`, {
    actor_id: 'command-center-plugin-governance',
    reason: 'Disabled Plugin-managed Business Unit from Command Center.',
    evidence: { review: 'operator-disabled-plugin' },
  });
}

async function analyzePluginImpact(pluginId, intendedAction = 'disable') {
  return apiRequest(`/api/plugins/${pluginId}/impact-analysis`, {
    actor_id: 'command-center-plugin-governance',
    reason: 'Analyzed Plugin-managed Business Unit impact from Command Center.',
    intended_action: intendedAction,
    evidence: { review: 'operator-analyzed-plugin-impact' },
  });
}

async function approvePluginChange(pluginId, intendedAction = 'disable') {
  return apiRequest(`/api/plugins/${pluginId}/approve-change`, {
    actor_id: 'command-center-plugin-governance',
    reason: 'Approved Plugin-managed Business Unit change from Command Center.',
    intended_action: intendedAction,
    evidence: { approval: 'operator-approved-plugin-change' },
  });
}

async function rollbackPlugin(pluginId) {
  return apiRequest(`/api/plugins/${pluginId}/rollback`, {
    actor_id: 'command-center-plugin-governance',
    reason: 'Rolled back Plugin-managed Business Unit from Command Center.',
    evidence: { review: 'operator-rolled-back-plugin' },
  });
}

async function exportPluginDNA(pluginId) {
  return apiRequest(`/api/plugins/${pluginId}/export-dna`, {
    actor_id: 'command-center-plugin-governance',
    reason: 'Exported Plugin-managed Business Unit as DNA from Command Center.',
    evidence: { export: 'operator-exported-plugin-dna' },
  });
}

async function importPluginDNA(dnaPackage) {
  return apiRequest('/api/plugins/import-dna', {
    actor_id: 'command-center-plugin-governance',
    reason: 'Imported Plugin-managed Business Unit DNA from Command Center.',
    dna_package: dnaPackage,
    evidence: { import: 'operator-imported-plugin-dna' },
  });
}

async function softDeletePlugin(pluginId) {
  return apiRequest(`/api/plugins/${pluginId}/delete`, {
    actor_id: 'command-center-plugin-governance',
    reason: 'Soft-deleted Plugin-managed Business Unit from Command Center.',
    evidence: { review: 'operator-soft-deleted-plugin' },
  });
}

async function restorePlugin(pluginId) {
  return apiRequest(`/api/plugins/${pluginId}/restore`, {
    actor_id: 'command-center-plugin-governance',
    reason: 'Restored Plugin-managed Business Unit from Command Center.',
    evidence: { review: 'operator-restored-plugin' },
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

async function exportRuntimeObjectDNA(objectId) {
  return apiRequest(`/api/runtime-objects/${objectId}/export-dna`, {
    actor_id: 'command-center-runtime-governance',
    reason: 'Exported runtime object as DNA from Command Center.',
    evidence: { review: 'operator-exported-runtime-object-dna' },
  });
}

async function importRuntimeObjectDNA(dnaPackage) {
  return apiRequest('/api/runtime-objects/import-dna', {
    actor_id: 'command-center-runtime-governance',
    reason: 'Imported runtime object DNA from Command Center for governance review.',
    dna_package: dnaPackage,
    evidence: { review: 'operator-imported-runtime-object-dna' },
  });
}

async function validateRuntimeObject(objectId) {
  return apiRequest(`/api/runtime-objects/${objectId}/validate`, {
    actor_id: 'command-center-runtime-governance',
    reason: 'Validated runtime object from Command Center.',
    evidence: { review: 'operator-validated-runtime-object' },
  });
}

async function analyzeRuntimeObjectImpact(objectId, intendedAction) {
  return apiRequest(`/api/runtime-objects/${objectId}/impact-analysis`, {
    actor_id: 'command-center-runtime-governance',
    reason: `Analyzed impact before ${intendedAction} from Command Center.`,
    intended_action: intendedAction,
    evidence: { review: 'operator-analyzed-runtime-object-impact' },
  });
}

async function approveRuntimeObjectChange(objectId, intendedAction) {
  return apiRequest(`/api/runtime-objects/${objectId}/approve-change`, {
    actor_id: 'command-center-runtime-governance',
    reason: `Approved ${intendedAction} from Command Center.`,
    intended_action: intendedAction,
    evidence: { review: 'operator-approved-runtime-object-change' },
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
  const [dnaPackage, setDnaPackage] = useState(null);
  const [importedRuntimeObject, setImportedRuntimeObject] = useState(null);
  const [validationReport, setValidationReport] = useState(null);
  const [impactReport, setImpactReport] = useState(null);
  const [approvalReport, setApprovalReport] = useState(null);
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

  const handleDNAExport = async (objectId) => {
    setStatus('loading');
    setError('');
    try {
      const body = await exportRuntimeObjectDNA(objectId);
      setDnaPackage(body.dna_package);
      setImportedRuntimeObject(null);
      await refreshRuntimeObjects();
      onActionComplete();
    } catch (runtimeError) {
      setStatus('error');
      setError(runtimeError.message);
    }
  };

  const handleValidation = async (objectId) => {
    setStatus('loading');
    setError('');
    try {
      const body = await validateRuntimeObject(objectId);
      setValidationReport(body.validation_report);
      await refreshRuntimeObjects();
      onActionComplete();
    } catch (runtimeError) {
      setStatus('error');
      setError(runtimeError.message);
    }
  };

  const handleImpactAnalysis = async (objectId, intendedAction) => {
    setStatus('loading');
    setError('');
    try {
      const body = await analyzeRuntimeObjectImpact(objectId, intendedAction);
      setImpactReport(body.impact_report);
      await refreshRuntimeObjects();
      onActionComplete();
    } catch (runtimeError) {
      setStatus('error');
      setError(runtimeError.message);
    }
  };

  const handleChangeApproval = async (objectId, intendedAction) => {
    setStatus('loading');
    setError('');
    try {
      const body = await approveRuntimeObjectChange(objectId, intendedAction);
      setApprovalReport(body.approval_report);
      await refreshRuntimeObjects();
      onActionComplete();
    } catch (runtimeError) {
      setStatus('error');
      setError(runtimeError.message);
    }
  };

  const handleDNAImport = async () => {
    setStatus('loading');
    setError('');
    try {
      const body = await importRuntimeObjectDNA(dnaPackage);
      setImportedRuntimeObject(body.runtime_object);
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
      {dnaPackage && (
        <div className="mission-result">
          <strong>DNA Export Ready</strong>
          <p>{dnaPackage.dna_package_id}</p>
          <p>{dnaPackage.payload.schema}</p>
          <button onClick={handleDNAImport} disabled={status === 'loading'}>
            Import Last DNA
          </button>
        </div>
      )}
      {importedRuntimeObject && (
        <div className="mission-result">
          <strong>DNA Import Ready For Review</strong>
          <p>{importedRuntimeObject.name}</p>
          <p>{importedRuntimeObject.status} / v{importedRuntimeObject.version}</p>
        </div>
      )}
      {validationReport && (
        <div className="mission-result">
          <strong>{validationReport.passed ? 'Validation Passed' : 'Validation Failed'}</strong>
          <p>{validationReport.validation_id}</p>
          <p>
            {validationReport.checks.filter((check) => check.passed).length} / {validationReport.checks.length} checks passed
          </p>
        </div>
      )}
      {impactReport && (
        <div className="mission-result">
          <strong>Impact: {impactReport.risk_level}</strong>
          <p>{impactReport.impact_id}</p>
          <p>
            {impactReport.affected_capabilities.length} capabilities / {impactReport.affected_dependencies.length} dependencies
          </p>
        </div>
      )}
      {approvalReport && (
        <div className="mission-result">
          <strong>Change Approved</strong>
          <p>{approvalReport.approval_id}</p>
          <p>{approvalReport.intended_action}</p>
        </div>
      )}
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
                    <button
                      onClick={() => handleDNAExport(item.object_id)}
                      disabled={status === 'loading'}
                    >
                      Export DNA
                    </button>
                    <button
                      onClick={() => handleValidation(item.object_id)}
                      disabled={status === 'loading'}
                    >
                      Validate
                    </button>
                    <button
                      onClick={() => handleImpactAnalysis(item.object_id, item.status === 'enabled' ? 'disable' : 'enable')}
                      disabled={status === 'loading'}
                    >
                      Analyze Impact
                    </button>
                    <button
                      onClick={() => handleChangeApproval(item.object_id, item.status === 'enabled' ? 'disable' : 'enable')}
                      disabled={status === 'loading'}
                    >
                      Approve Change
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

function PluginHistoryPanel({ refreshVersion, onActionComplete }) {
  const [plugins, setPlugins] = useState([]);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');
  const [pluginValidationReport, setPluginValidationReport] = useState(null);
  const [pluginImpactReport, setPluginImpactReport] = useState(null);
  const [pluginApprovalReport, setPluginApprovalReport] = useState(null);
  const [pluginDnaPackage, setPluginDnaPackage] = useState(null);
  const [pluginDnaImport, setPluginDnaImport] = useState(null);
  const [pluginTimeline, setPluginTimeline] = useState(null);
  const [pluginSettings, setPluginSettings] = useState(null);
  const [pluginDashboard, setPluginDashboard] = useState(null);
  const [pluginChat, setPluginChat] = useState(null);

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

  const handlePluginStateChange = async (pluginId, nextState) => {
    setStatus('loading');
    setError('');
    try {
      if (nextState === 'enabled') {
        await enablePlugin(pluginId);
      } else if (nextState === 'upgraded') {
        await upgradePlugin(pluginId);
      } else if (nextState === 'rollback') {
        await rollbackPlugin(pluginId);
      } else if (nextState === 'deleted') {
        await softDeletePlugin(pluginId);
      } else if (nextState === 'restored') {
        await restorePlugin(pluginId);
      } else {
        await disablePlugin(pluginId);
      }
      await refreshPlugins();
      onActionComplete();
    } catch (pluginError) {
      setStatus('error');
      setError(pluginError.message);
    }
  };

  const handlePluginValidation = async (pluginId) => {
    setStatus('loading');
    setError('');
    try {
      const body = await validatePlugin(pluginId);
      setPluginValidationReport(body.validation_report);
      await refreshPlugins();
      onActionComplete();
    } catch (pluginError) {
      setStatus('error');
      setError(pluginError.message);
    }
  };

  const handlePluginImpactAnalysis = async (pluginId, intendedAction = 'disable') => {
    setStatus('loading');
    setError('');
    try {
      const body = await analyzePluginImpact(pluginId, intendedAction);
      setPluginImpactReport(body.impact_report);
      await refreshPlugins();
      onActionComplete();
    } catch (pluginError) {
      setStatus('error');
      setError(pluginError.message);
    }
  };

  const handlePluginApproval = async (pluginId, intendedAction = 'disable') => {
    setStatus('loading');
    setError('');
    try {
      const body = await approvePluginChange(pluginId, intendedAction);
      setPluginApprovalReport(body.approval_report);
      await refreshPlugins();
      onActionComplete();
    } catch (pluginError) {
      setStatus('error');
      setError(pluginError.message);
    }
  };

  const handlePluginDnaExport = async (pluginId) => {
    setStatus('loading');
    setError('');
    try {
      const body = await exportPluginDNA(pluginId);
      setPluginDnaPackage(body.dna_package);
      await refreshPlugins();
      onActionComplete();
    } catch (pluginError) {
      setStatus('error');
      setError(pluginError.message);
    }
  };

  const handlePluginDnaImport = async () => {
    if (!pluginDnaPackage) return;
    setStatus('loading');
    setError('');
    try {
      const body = await importPluginDNA(pluginDnaPackage);
      setPluginDnaImport(body.plugin);
      await refreshPlugins();
      onActionComplete();
    } catch (pluginError) {
      setStatus('error');
      setError(pluginError.message);
    }
  };

  const handlePluginTimeline = async (pluginId) => {
    setStatus('loading');
    setError('');
    try {
      const timeline = await loadPluginTimeline(pluginId);
      setPluginTimeline(timeline);
      setStatus('ready');
    } catch (pluginError) {
      setStatus('error');
      setError(pluginError.message);
    }
  };

  const handlePluginSettingsUpdate = async (pluginId) => {
    setStatus('loading');
    setError('');
    try {
      const settings = await updatePluginSettings(pluginId);
      setPluginSettings(settings);
      await refreshPlugins();
      onActionComplete();
    } catch (pluginError) {
      setStatus('error');
      setError(pluginError.message);
    }
  };

  const handlePluginDashboard = async (pluginId) => {
    setStatus('loading');
    setError('');
    try {
      const dashboard = await loadPluginDashboard(pluginId);
      setPluginDashboard(dashboard);
      setStatus('ready');
    } catch (pluginError) {
      setStatus('error');
      setError(pluginError.message);
    }
  };

  const handlePluginChatRequest = async (pluginId) => {
    setStatus('loading');
    setError('');
    try {
      const body = await sendPluginChatRequest(pluginId);
      setPluginChat(body.chat);
      await refreshPlugins();
      onActionComplete();
    } catch (pluginError) {
      setStatus('error');
      setError(pluginError.message);
    }
  };

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
      {pluginValidationReport && (
        <div className="mission-result">
          <strong>
            Plugin Validation {pluginValidationReport.passed ? 'Passed' : 'Failed'}
          </strong>
          <span>{pluginValidationReport.validation_id}</span>
          <p>{pluginValidationReport.checks.length} checks recorded before plugin activation.</p>
        </div>
      )}
      {pluginImpactReport && (
        <div className="mission-result">
          <strong>Plugin Impact Analysis Recorded</strong>
          <span>{pluginImpactReport.impact_id}</span>
          <p>{pluginImpactReport.risk_level} risk before {pluginImpactReport.intended_action}.</p>
        </div>
      )}
      {pluginApprovalReport && (
        <div className="mission-result">
          <strong>Plugin Change Approved</strong>
          <span>{pluginApprovalReport.approval_id}</span>
          <p>Approval linked to {pluginApprovalReport.impact_id}.</p>
        </div>
      )}
      {pluginDnaPackage && (
        <div className="mission-result">
          <strong>Plugin DNA Exported</strong>
          <span>{pluginDnaPackage.dna_package_id}</span>
          <p>{pluginDnaPackage.payload.plugin.name} v{pluginDnaPackage.version}</p>
          <button onClick={handlePluginDnaImport} disabled={status === 'loading'}>
            Import Last Plugin DNA
          </button>
        </div>
      )}
      {pluginDnaImport && (
        <div className="mission-result">
          <strong>Plugin DNA Imported</strong>
          <span>{pluginDnaImport.plugin_id}</span>
          <p>{pluginDnaImport.status} review state before validation.</p>
        </div>
      )}
      {pluginTimeline && (
        <div className="mission-result">
          <strong>Plugin Timeline</strong>
          <span>{pluginTimeline.plugin.plugin_id}</span>
          <p>
            {pluginTimeline.summary.audit_records} audit records and{' '}
            {pluginTimeline.summary.events} runtime events.
          </p>
        </div>
      )}
      {pluginSettings && (
        <div className="mission-result">
          <strong>Plugin Settings Updated</strong>
          <span>{pluginSettings.plugin_id}</span>
          <p>{(pluginSettings.settings_values.pipelineStages || []).join(' -> ')}</p>
        </div>
      )}
      {pluginDashboard && (
        <div className="mission-result">
          <strong>{pluginDashboard.name} Dashboard</strong>
          <span>{pluginDashboard.dashboard_route}</span>
          <p>
            {pluginDashboard.status} / {pluginDashboard.workflows.length} workflows /{' '}
            {pluginDashboard.activity.audit_records} audit records.
          </p>
        </div>
      )}
      {pluginChat && (
        <div className="mission-result">
          <strong>Plugin Chat Mission Created</strong>
          <span>{pluginChat.mission_id}</span>
          <p>
            {pluginChat.chief_agent_role} queued mission with {pluginChat.status} status.
          </p>
        </div>
      )}
      <div className="plugin-history">
        {plugins.length ? (
          plugins.map((plugin) => (
            <article key={plugin.plugin_id}>
              <strong>{plugin.name}</strong>
              <span>{plugin.status} / v{plugin.version}</span>
              <p>{plugin.chief_agent_role}</p>
              <p>{plugin.dashboard_route}</p>
              <time>{plugin.data_boundary}</time>
              {plugin.validation?.validation_id && (
                <small>Validation: {plugin.validation.validation_id}</small>
              )}
              {plugin.impact_analysis?.impact_id && (
                <small>Impact: {plugin.impact_analysis.impact_id}</small>
              )}
              {plugin.change_approval?.approval_id && (
                <small>Approval: {plugin.change_approval.approval_id}</small>
              )}
              {(plugin.rollback_stack || []).length > 0 && (
                <small>Rollback points: {plugin.rollback_stack.length}</small>
              )}
              <div className="mission-actions">
                <button
                  onClick={() => handlePluginValidation(plugin.plugin_id)}
                  disabled={status === 'loading'}
                >
                  Validate Plugin
                </button>
                <button
                  onClick={() => handlePluginStateChange(plugin.plugin_id, 'upgraded')}
                  disabled={status === 'loading' || plugin.status === 'deleted'}
                >
                  Upgrade Plugin
                </button>
                <button
                  onClick={() => handlePluginImpactAnalysis(plugin.plugin_id, 'disable')}
                  disabled={status === 'loading'}
                >
                  Analyze Disable Impact
                </button>
                <button
                  onClick={() => handlePluginImpactAnalysis(plugin.plugin_id, 'delete')}
                  disabled={status === 'loading'}
                >
                  Analyze Delete Impact
                </button>
                <button
                  onClick={() => handlePluginApproval(plugin.plugin_id, 'disable')}
                  disabled={status === 'loading'}
                >
                  Approve Disable
                </button>
                <button
                  onClick={() => handlePluginApproval(plugin.plugin_id, 'delete')}
                  disabled={status === 'loading'}
                >
                  Approve Delete
                </button>
                {(plugin.rollback_stack || []).length > 0 && (
                  <button
                    onClick={() => handlePluginStateChange(plugin.plugin_id, 'rollback')}
                    disabled={status === 'loading'}
                  >
                    Rollback Plugin
                  </button>
                )}
                <button
                  onClick={() => handlePluginDnaExport(plugin.plugin_id)}
                  disabled={status === 'loading' || plugin.status === 'deleted'}
                >
                  Export Plugin DNA
                </button>
                <button
                  onClick={() => handlePluginTimeline(plugin.plugin_id)}
                  disabled={status === 'loading'}
                >
                  Review Plugin Timeline
                </button>
                <button
                  onClick={() => handlePluginSettingsUpdate(plugin.plugin_id)}
                  disabled={status === 'loading' || plugin.status === 'deleted'}
                >
                  Update Plugin Settings
                </button>
                <button
                  onClick={() => handlePluginDashboard(plugin.plugin_id)}
                  disabled={status === 'loading'}
                >
                  Open Plugin Dashboard
                </button>
                <button
                  onClick={() => handlePluginChatRequest(plugin.plugin_id)}
                  disabled={status === 'loading' || plugin.status === 'deleted'}
                >
                  Send Plugin Chat Request
                </button>
                {plugin.status === 'deleted' ? (
                  <button
                    onClick={() => handlePluginStateChange(plugin.plugin_id, 'restored')}
                    disabled={status === 'loading'}
                  >
                    Restore Plugin
                  </button>
                ) : plugin.status === 'enabled' ? (
                  <button
                    onClick={() => handlePluginStateChange(plugin.plugin_id, 'disabled')}
                    disabled={status === 'loading'}
                  >
                    Disable Plugin
                  </button>
                ) : (
                  <button
                    onClick={() => handlePluginStateChange(plugin.plugin_id, 'enabled')}
                    disabled={status === 'loading'}
                  >
                    Enable Plugin
                  </button>
                )}
                {plugin.status !== 'deleted' && (
                  <button
                    onClick={() => handlePluginStateChange(plugin.plugin_id, 'deleted')}
                    disabled={status === 'loading'}
                  >
                    Soft Delete Plugin
                  </button>
                )}
              </div>
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
  const [deliveryPackages, setDeliveryPackages] = useState([]);
  const [qualityReviews, setQualityReviews] = useState([]);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');
  const [artifact, setArtifact] = useState(null);
  const [qualityReview, setQualityReview] = useState(null);
  const [deliveryPackage, setDeliveryPackage] = useState(null);

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

  const refreshDeliveryPackages = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setDeliveryPackages((await loadDeliveryPackages()).slice(0, 5));
      setStatus('ready');
    } catch (deliveryError) {
      setStatus('error');
      setError(deliveryError.message);
    }
  }, []);

  const refreshQualityReviews = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setQualityReviews((await loadQualityReviews()).slice(0, 5));
      setStatus('ready');
    } catch (qualityError) {
      setStatus('error');
      setError(qualityError.message);
    }
  }, []);

  useEffect(() => {
    refreshMissions();
    refreshDeliveryPackages();
    refreshQualityReviews();
  }, [refreshMissions, refreshDeliveryPackages, refreshQualityReviews, refreshVersion]);

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

  async function handleArtifactGeneration(missionId) {
    setStatus('loading');
    setError('');
    try {
      const body = await generateArtifactFromMission(missionId);
      setArtifact(body.artifact);
      setQualityReview(null);
      setDeliveryPackage(null);
      onActionComplete();
      setStatus('ready');
    } catch (artifactError) {
      setStatus('error');
      setError(artifactError.message);
    }
  }

  async function handleArtifactDecision(decision) {
    if (!artifact) return;
    setStatus('loading');
    setError('');
    try {
      const body = decision === 'approve'
        ? await approveArtifact(artifact.artifact_id)
        : await rejectArtifact(artifact.artifact_id);
      setArtifact(body.artifact);
      setQualityReview(null);
      onActionComplete();
      setStatus('ready');
    } catch (artifactError) {
      setStatus('error');
      setError(artifactError.message);
    }
  }

  async function handleQualityReview() {
    if (!artifact) return;
    setStatus('loading');
    setError('');
    try {
      const body = await reviewArtifactQuality(artifact.artifact_id);
      setQualityReview(body.quality_review);
      await refreshQualityReviews();
      onActionComplete();
      setStatus('ready');
    } catch (qualityError) {
      setStatus('error');
      setError(qualityError.message);
    }
  }

  async function handleDeliveryPackaging() {
    if (!artifact) return;
    setStatus('loading');
    setError('');
    try {
      const body = await packageArtifactDelivery(artifact.artifact_id);
      setDeliveryPackage(body.delivery_package);
      await refreshDeliveryPackages();
      onActionComplete();
      setStatus('ready');
    } catch (artifactError) {
      setStatus('error');
      setError(artifactError.message);
    }
  }

  async function handleDeliveryConfirmation(deliveryId) {
    setStatus('loading');
    setError('');
    try {
      const body = await confirmDeliveryPackage(deliveryId);
      setDeliveryPackage(body.delivery_package);
      await refreshDeliveryPackages();
      onActionComplete();
      setStatus('ready');
    } catch (deliveryError) {
      setStatus('error');
      setError(deliveryError.message);
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
      {artifact && (
        <div className="mission-result">
          <strong>{artifact.title}</strong>
          <span>{artifact.status}</span>
          <p>{artifact.content}</p>
          {artifact.status === 'awaiting_approval' && (
            <div className="mission-actions">
              <button onClick={() => handleArtifactDecision('approve')} disabled={status === 'loading'}>
                Approve Artifact
              </button>
              <button onClick={() => handleArtifactDecision('reject')} disabled={status === 'loading'}>
                Reject Artifact
              </button>
            </div>
          )}
          {artifact.status === 'approved' && (
            <div className="mission-actions">
              <button onClick={handleQualityReview} disabled={status === 'loading'}>
                Run Quality Review
              </button>
              <button
                onClick={handleDeliveryPackaging}
                disabled={status === 'loading' || !qualityReview?.passed}
              >
                Package Delivery
              </button>
            </div>
          )}
        </div>
      )}
      {qualityReview && (
        <div className="mission-result">
          <strong>{qualityReview.passed ? 'Quality Review Passed' : 'Quality Review Failed'}</strong>
          <span>{qualityReview.score}%</span>
          <p>{qualityReview.review_id}</p>
        </div>
      )}
      {deliveryPackage && (
        <div className="mission-result">
          <strong>Delivery Package Ready</strong>
          <span>{deliveryPackage.delivery_id}</span>
          <p>{deliveryPackage.destination} / {deliveryPackage.status}</p>
        </div>
      )}
      <div className="mission-actions">
        <button onClick={refreshDeliveryPackages} disabled={status === 'loading'}>
          Refresh Delivery Packages
        </button>
        <button onClick={refreshQualityReviews} disabled={status === 'loading'}>
          Refresh Quality Reviews
        </button>
      </div>
      <div className="mission-history">
        {qualityReviews.length ? (
          qualityReviews.map((item) => (
            <article key={item.review_id}>
              <strong>{item.passed ? 'passed' : 'failed'}</strong>
              <span>{item.score}%</span>
              <p>{item.plugin_id} / artifact {item.artifact_id}</p>
              <time>{new Date(item.created_at).toLocaleString()}</time>
            </article>
          ))
        ) : (
          <p>No quality reviews recorded yet.</p>
        )}
      </div>
      <div className="mission-history">
        {deliveryPackages.length ? (
          deliveryPackages.map((item) => (
            <article key={item.delivery_id}>
              <strong>{item.status}</strong>
              <span>{item.destination}</span>
              <p>{item.plugin_id} / artifact {item.artifact_id}</p>
              <time>{new Date(item.created_at).toLocaleString()}</time>
              {item.status === 'ready_for_client_delivery' && (
                <div className="mission-actions">
                  <button
                    onClick={() => handleDeliveryConfirmation(item.delivery_id)}
                    disabled={status === 'loading'}
                  >
                    Confirm Client Delivery
                  </button>
                </div>
              )}
            </article>
          ))
        ) : (
          <p>No delivery packages recorded yet.</p>
        )}
      </div>
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
                  <button
                    onClick={() => handleArtifactGeneration(item.mission_id)}
                    disabled={status === 'loading'}
                  >
                    Generate Artifact
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

function SystemReadinessPanel({ refreshVersion }) {
  const [readiness, setReadiness] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshReadiness = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setReadiness(await loadSystemReadiness());
      setStatus('ready');
    } catch (readinessError) {
      setStatus('error');
      setError(readinessError.message);
    }
  }, []);

  useEffect(() => {
    refreshReadiness();
  }, [refreshReadiness, refreshVersion]);

  const readyCount = readiness
    ? readiness.checks.filter((check) => check.status === 'ready').length
    : 0;

  return (
    <section className="panel mission-panel">
      <div>
        <h2>System Readiness</h2>
        <p>Verify executable layers before operating the Command Center.</p>
      </div>
      <button onClick={refreshReadiness} disabled={status === 'loading'}>
        {status === 'loading' ? 'Checking...' : 'Refresh Readiness'}
      </button>
      {error && <p className="error">{error}</p>}
      {readiness && (
        <>
          <div className="mission-result">
            <strong>{readiness.status}</strong>
            <span>{readyCount} / {readiness.checks.length} checks ready</span>
          </div>
          <div className="mission-history">
            {readiness.checks.map((check) => (
              <article key={check.name}>
                <strong>{check.name}</strong>
                <span>{check.status}</span>
                <p>{check.detail}</p>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function VerificationReportPanel({ refreshVersion }) {
  const [report, setReport] = useState(null);
  const [auditRecord, setAuditRecord] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshReport = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setReport(await loadVerificationReport());
      setSnapshots((await loadVerificationSnapshots()).slice(0, 5));
      setStatus('ready');
    } catch (reportError) {
      setStatus('error');
      setError(reportError.message);
    }
  }, []);

  useEffect(() => {
    refreshReport();
  }, [refreshReport, refreshVersion]);

  async function handleRecordSnapshot() {
    setStatus('loading');
    setError('');
    try {
      const body = await recordVerificationSnapshot();
      setAuditRecord(body.audit_record);
      await refreshReport();
      setStatus('ready');
    } catch (reportError) {
      setStatus('error');
      setError(reportError.message);
    }
  }

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Verification Report</h2>
        <p>Review the executable smoke contract used by project verification.</p>
      </div>
      <button onClick={refreshReport} disabled={status === 'loading'}>
        {status === 'loading' ? 'Checking...' : 'Refresh Verification Report'}
      </button>
      <button onClick={handleRecordSnapshot} disabled={status === 'loading' || !report}>
        Record Verification Snapshot
      </button>
      {error && <p className="error">{error}</p>}
      {auditRecord && (
        <div className="mission-result">
          <strong>Verification Snapshot Recorded</strong>
          <span>{auditRecord.audit_id}</span>
          <p>{auditRecord.decision} / {auditRecord.data_platform}</p>
        </div>
      )}
      {report && (
        <>
          <div className="mission-result">
            <strong>{report.status}</strong>
            <span>{report.ready_checks} / {report.total_checks} readiness checks</span>
            <p>{report.smoke_flow}</p>
          </div>
          <div className="status-grid">
            <div><strong>{report.summary.health}</strong><span>Health</span></div>
            <div><strong>{report.summary.runtime_objects}</strong><span>Runtime Objects</span></div>
            <div><strong>{report.summary.plugins}</strong><span>Plugins</span></div>
            <div><strong>{report.summary.missions}</strong><span>Missions</span></div>
            <div><strong>{report.summary.ai_routes}</strong><span>AI Routes</span></div>
            <div><strong>{report.summary.audit_records}</strong><span>Audit Records</span></div>
            <div><strong>{report.summary.runtime_events}</strong><span>Runtime Events</span></div>
          </div>
          <div className="mission-history">
            {snapshots.length ? (
              snapshots.map((snapshot) => (
                <article key={snapshot.audit_id}>
                  <strong>{snapshot.decision}</strong>
                  <span>{snapshot.evidence.verification_status}</span>
                  <p>{snapshot.audit_id}</p>
                  <time>{new Date(snapshot.created_at).toLocaleString()}</time>
                </article>
              ))
            ) : (
              <p>No verification snapshots recorded yet.</p>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function RuntimeDiagnosticsPanel({ refreshVersion }) {
  const [diagnostics, setDiagnostics] = useState(null);
  const [exportPackage, setExportPackage] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshDiagnostics = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setDiagnostics(await loadRuntimeDiagnostics());
      setStatus('ready');
    } catch (diagnosticsError) {
      setStatus('error');
      setError(diagnosticsError.message);
    }
  }, []);

  useEffect(() => {
    refreshDiagnostics();
  }, [refreshDiagnostics, refreshVersion]);

  async function handleDiagnosticsExport() {
    setStatus('loading');
    setError('');
    try {
      const body = await exportRuntimeDiagnostics();
      setExportPackage(body.export_package);
      setStatus('ready');
    } catch (diagnosticsError) {
      setStatus('error');
      setError(diagnosticsError.message);
    }
  }

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Runtime Diagnostics</h2>
        <p>Inspect recent audit and runtime activity tied to system verification.</p>
      </div>
      <button onClick={refreshDiagnostics} disabled={status === 'loading'}>
        {status === 'loading' ? 'Loading...' : 'Refresh Diagnostics'}
      </button>
      <button onClick={handleDiagnosticsExport} disabled={status === 'loading' || !diagnostics}>
        Export Diagnostics
      </button>
      {error && <p className="error">{error}</p>}
      {exportPackage && (
        <div className="mission-result">
          <strong>Diagnostics Export Ready</strong>
          <span>{exportPackage.export_id}</span>
          <p>{exportPackage.status} / {exportPackage.format}</p>
        </div>
      )}
      {diagnostics && (
        <>
          <div className="mission-result">
            <strong>{diagnostics.status}</strong>
            <span>{diagnostics.data_platform}</span>
            <p>{new Date(diagnostics.generated_at).toLocaleString()}</p>
          </div>
          <div className="mission-history">
            {diagnostics.recent_audit_records.length ? (
              diagnostics.recent_audit_records.map((record) => (
                <article key={record.audit_id}>
                  <strong>{record.decision}</strong>
                  <span>{record.action}</span>
                  <p>{record.target_type} / {record.target_id}</p>
                </article>
              ))
            ) : (
              <p>No recent audit records found.</p>
            )}
          </div>
          <div className="activity-feed">
            <h3>Diagnostic Runtime Events</h3>
            {diagnostics.recent_events.length ? (
              <ol>
                {diagnostics.recent_events.map((event) => (
                  <li key={event.event_id}>
                    <strong>{event.name}</strong>
                    <span>{event.source}</span>
                    <time>{new Date(event.created_at).toLocaleString()}</time>
                  </li>
                ))}
              </ol>
            ) : (
              <p>No recent runtime events found.</p>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function UsageGuidePanel({ refreshVersion }) {
  const [guide, setGuide] = useState(null);
  const [exportPackage, setExportPackage] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshGuide = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setGuide(await loadUsageGuide());
      setStatus('ready');
    } catch (guideError) {
      setStatus('error');
      setError(guideError.message);
    }
  }, []);

  useEffect(() => {
    refreshGuide();
  }, [refreshGuide, refreshVersion]);

  async function handleUsageGuideExport() {
    setStatus('loading');
    setError('');
    try {
      const body = await exportUsageGuide();
      setExportPackage(body.export_package);
      setStatus('ready');
    } catch (guideError) {
      setStatus('error');
      setError(guideError.message);
    }
  }

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Usage Guide</h2>
        <p>Trace each Command Center button from frontend action to backend result.</p>
      </div>
      <button onClick={refreshGuide} disabled={status === 'loading'}>
        {status === 'loading' ? 'Loading...' : 'Refresh Usage Guide'}
      </button>
      <button onClick={handleUsageGuideExport} disabled={status === 'loading' || !guide}>
        Export Usage Guide
      </button>
      {error && <p className="error">{error}</p>}
      {exportPackage && (
        <div className="mission-result">
          <strong>Usage Guide Export Ready</strong>
          <span>{exportPackage.export_id}</span>
          <p>{exportPackage.status} / {exportPackage.package_manifest.step_count} steps</p>
        </div>
      )}
      {guide && (
        <>
          <div className="mission-result">
            <strong>{guide.status}</strong>
            <span>{guide.data_platform}</span>
            <p>{guide.operating_rule}</p>
          </div>
          <div className="mission-history">
            {guide.steps.map((step) => (
              <article key={step.action}>
                <strong>{step.frontend_control}</strong>
                <span>{step.api_endpoint}</span>
                <p>{step.service_effect}</p>
                <p>{step.result}</p>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function CompletionReportPanel({ refreshVersion }) {
  const [report, setReport] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshReport = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setReport(await loadCompletionReport());
      setStatus('ready');
    } catch (completionError) {
      setStatus('error');
      setError(completionError.message);
    }
  }, []);

  useEffect(() => {
    refreshReport();
  }, [refreshReport, refreshVersion]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Completion Report</h2>
        <p>Review verified project readiness across frontend, backend, data, governance, and tests.</p>
      </div>
      <button onClick={refreshReport} disabled={status === 'loading'}>
        {status === 'loading' ? 'Loading...' : 'Refresh Completion Report'}
      </button>
      {error && <p className="error">{error}</p>}
      {report && (
        <>
          <div className="mission-result">
            <strong>{report.completion_percent}% complete</strong>
            <span>{report.status}</span>
            <p>{report.summary}</p>
          </div>
          <div className="mission-history">
            {report.areas.map((area) => (
              <article key={area.name}>
                <strong>{area.name}</strong>
                <span>{area.completion_percent}% / {area.status}</span>
                <p>{area.evidence}</p>
                <p>{area.next_step}</p>
              </article>
            ))}
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
        <SystemReadinessPanel refreshVersion={refreshVersion} />
        <VerificationReportPanel refreshVersion={refreshVersion} />
        <RuntimeDiagnosticsPanel refreshVersion={refreshVersion} />
        <UsageGuidePanel refreshVersion={refreshVersion} />
        <CompletionReportPanel refreshVersion={refreshVersion} />
        <MissionPanel onActionComplete={refreshCommandCenterSummary} />
        <MissionHistoryPanel
          refreshVersion={refreshVersion}
          onActionComplete={refreshCommandCenterSummary}
        />
        <AIResourcePanel onActionComplete={refreshCommandCenterSummary} />
        <AIRouteHistoryPanel refreshVersion={refreshVersion} />
        <PluginPanel onActionComplete={refreshCommandCenterSummary} />
        <PluginHistoryPanel
          refreshVersion={refreshVersion}
          onActionComplete={refreshCommandCenterSummary}
        />
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
