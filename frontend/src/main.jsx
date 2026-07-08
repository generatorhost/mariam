import React, { useCallback, useEffect, useMemo, useState } from 'react';
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

const commandCenterNav = [
  { label: 'Status', href: '#status' },
  { label: 'DB MARIAM', href: '#data-platform' },
  { label: 'Verification', href: '#verification' },
  { label: 'Roadmap', href: '#roadmap' },
  { label: 'Missions', href: '#missions' },
  { label: 'Plugins', href: '#plugins' },
  { label: 'Governance', href: '#governance' },
];

const pluginWorkspaceApps = [
  {
    name: 'CRM Workspace',
    status: 'Ready for governance',
    chief: 'CRM Chief Agent',
    route: '/plugins/crm',
    settings: '/plugins/crm/settings',
    dataBoundary: 'plugin_crm',
    swarm: ['Lead Analyst', 'Pipeline Reviewer', 'Client Follow-up Agent'],
    workflows: ['Lead follow-up', 'Client report', 'Delivery approval'],
  },
];

const responsiveStates = [
  {
    mode: 'Mobile',
    layout: 'Single column',
    focus: 'Chat, apps, tasks, approvals',
  },
  {
    mode: 'Tablet',
    layout: 'Stacked panels',
    focus: 'Command Center, plugin workspaces, governance queues',
  },
  {
    mode: 'Desktop',
    layout: 'Sidebar navigation + wide workspace',
    focus: 'Operational dashboards, DB MARIAM readiness, delivery evidence',
  },
];

const apiBaseUrl = import.meta.env.VITE_MARIAM_API_BASE_URL || 'http://localhost:8000';
const commandCenterPreferenceStorageKey = 'mariam.commandCenter.preferences.v1';

function readCommandCenterPreferences() {
  try {
    const rawPreferences = window.localStorage.getItem(commandCenterPreferenceStorageKey);
    return rawPreferences ? JSON.parse(rawPreferences) : {};
  } catch {
    return {};
  }
}

function writeCommandCenterPreference(key, value) {
  try {
    const preferences = readCommandCenterPreferences();
    window.localStorage.setItem(
      commandCenterPreferenceStorageKey,
      JSON.stringify({ ...preferences, [key]: value }),
    );
  } catch {
    // Preferences are an enhancement; unavailable storage must not block operations.
  }
}

function readCommandCenterPreference(key, fallback) {
  const preferences = readCommandCenterPreferences();
  return typeof preferences[key] === 'string' ? preferences[key] : fallback;
}

async function buildApiError(response, path, actionLabel = 'Command Center action') {
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  const structuredError = payload?.error || {};
  const detail = structuredError.message || payload?.detail || response.statusText;
  const error = new Error(`${actionLabel} failed on ${path} with HTTP ${response.status}: ${detail}`);
  error.statusCode = response.status;
  error.path = structuredError.path || path;
  error.requestId = structuredError.request_id || 'unavailable';
  error.dataPlatform = structuredError.data_platform || 'DB MARIAM';
  error.retryAction = actionLabel;
  error.traceability = structuredError.traceability || {};
  return error;
}

async function apiRequest(path, body, options = {}) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: options.method || 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw await buildApiError(response, path, options.actionLabel);
  }
  return response.json();
}

async function apiGet(path, options = {}) {
  const response = await fetch(`${apiBaseUrl}${path}`);
  if (!response.ok) {
    throw await buildApiError(response, path, options.actionLabel);
  }
  return response.json();
}

function createPanelError(error, retryLabel, retryAction) {
  return {
    message: error.message,
    statusCode: error.statusCode || 'network',
    path: error.path || 'unknown endpoint',
    requestId: error.requestId || 'unavailable',
    dataPlatform: error.dataPlatform || 'DB MARIAM',
    retryLabel,
    retryAction,
  };
}

function ErrorBanner({ error }) {
  if (!error) {
    return null;
  }
  return (
    <div className="error-banner" role="alert" data-testid="command-center-error-banner">
      <div>
        <strong>{error.retryLabel || 'Command Center action failed'}</strong>
        <p>{error.message}</p>
        <span>
          Endpoint: {error.path} · Status: {error.statusCode} · Request: {error.requestId} ·{' '}
          {error.dataPlatform}
        </span>
      </div>
      {error.retryAction && (
        <button type="button" onClick={error.retryAction}>
          Retry
        </button>
      )}
    </div>
  );
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

async function loadAuthSession() {
  const body = await apiGet('/api/auth/session');
  return body.session;
}

async function loadRequestActorContext() {
  const response = await fetch(`${apiBaseUrl}/api/auth/request-context`, {
    headers: {
      'x-mariam-request-id': `command-center-${Date.now()}`,
      'x-mariam-actor-id': 'command-center-operator',
    },
  });
  if (!response.ok) {
    throw new Error(`API request to /api/auth/request-context failed with ${response.status}`);
  }
  const body = await response.json();
  return body.request_context;
}

async function checkGovernancePermission() {
  const body = await apiRequest('/api/auth/permissions/check', {
    actor_id: 'command-center-operator',
    permission: 'governance.assign_approval',
  });
  return body.permission_check;
}

async function enforceGovernancePermission() {
  const body = await apiRequest('/api/auth/permissions/enforce', {
    actor_id: 'command-center-operator',
    permission: 'governance.assign_approval',
    target_type: 'artifact',
    target_id: 'command-center-artifact-review',
    reason: 'Enforce permission before assigning governance approval.',
    evidence: { source: 'command-center-session-panel' },
  });
  return body.permission_enforcement;
}

async function enforceHumanIdentity() {
  const body = await apiRequest('/api/auth/human-identity/enforce', {
    actor_id: 'command-center-operator',
    claimed_user_id: 'command-center-operator',
    target_type: 'artifact',
    target_id: 'command-center-artifact-review',
    reason: 'Verify human operator identity before governance approval.',
    evidence: { source: 'command-center-session-panel' },
  });
  return body.human_identity;
}

async function loadSystemReadiness() {
  return apiGet('/api/runtime/readiness');
}

async function loadDataPlatformReadiness() {
  return apiGet('/api/runtime/data-platform/readiness');
}

async function exportDataPlatformReadiness() {
  return apiRequest('/api/runtime/data-platform/readiness/export', {});
}

async function loadMigrationRunnerStatus() {
  return apiGet('/api/runtime/data-platform/migration-runner');
}

async function exportMigrationRunnerStatus() {
  return apiRequest('/api/runtime/data-platform/migration-runner/export', {});
}

async function loadSeedDataStatus() {
  return apiGet('/api/runtime/data-platform/seed-data');
}

async function loadBackupReadiness() {
  return apiGet('/api/runtime/data-platform/backup-readiness');
}

async function loadPluginSchemaIsolation() {
  return apiGet('/api/runtime/data-platform/plugin-schema-isolation');
}

async function loadDockerPersistence() {
  return apiGet('/api/runtime/data-platform/docker-persistence');
}

async function loadLiveDbSmoke() {
  return apiGet('/api/runtime/data-platform/live-db-smoke');
}

async function loadDockerContainerExecution() {
  return apiGet('/api/runtime/data-platform/docker-container-execution');
}

async function runLiveDatabaseWriteSmoke() {
  return apiRequest('/api/runtime/data-platform/live-write-smoke', {});
}

async function runLiveRepositoryWriteSmoke() {
  return apiRequest('/api/runtime/data-platform/live-repository-write-smoke', {});
}

async function loadAuditEventArchiveRecords() {
  return apiGet('/api/runtime/data-platform/audit-event-archive');
}

async function exportAuditEventArchiveRecords() {
  return apiRequest('/api/runtime/data-platform/audit-event-archive/export', {});
}

async function loadMetricsStoreRecords() {
  return apiGet('/api/runtime/data-platform/metrics-store');
}

async function exportMetricsStoreRecords() {
  return apiRequest('/api/runtime/data-platform/metrics-store/export', {});
}

async function loadFrontendRegressionSnapshot() {
  return apiGet('/api/runtime/frontend/regression-snapshot');
}

async function loadFrontendVisualContract() {
  return apiGet('/api/runtime/frontend/visual-contract');
}

async function loadFrontendBrowserScreenshotPlan() {
  return apiGet('/api/runtime/frontend/browser-screenshot-plan');
}

async function loadFrontendBrowserScreenshotCapture() {
  return apiGet('/api/runtime/frontend/browser-screenshot-capture');
}

async function loadVerificationReport() {
  return apiGet('/api/runtime/verification-report');
}

async function loadVerificationAutomation() {
  return apiGet('/api/runtime/verification-automation');
}

async function exportVerificationFailureSummary() {
  return apiRequest('/api/runtime/verification-automation/failure-summary/export', {});
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

async function loadImplementationRoadmap() {
  return apiGet('/api/runtime/implementation-roadmap');
}

async function exportImplementationRoadmap() {
  return apiRequest('/api/runtime/implementation-roadmap/export', {});
}

async function exportCompletionReport() {
  return apiRequest('/api/runtime/completion-report/export', {});
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

async function loadDeliveryEvidenceReport() {
  return apiGet('/api/runtime/delivery-evidence-report');
}

async function exportDeliveryGovernanceEvidence() {
  return apiRequest('/api/runtime/delivery-evidence-report/export', {});
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

async function loadPluginWorkspace(pluginId) {
  return apiGet(`/api/plugins/${pluginId}/workspace`);
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

async function requestArtifactRevision(artifactId) {
  return apiRequest(`/api/artifacts/${artifactId}/request-revision`, {
    requested_by: 'command-center-artifact-governance',
    revision_request: 'Add traceability evidence and keep delivery blocked until governance approval.',
    evidence: { revision_loop: 'Requested from Command Center artifact panel' },
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

async function assignApproval() {
  return apiRequest('/api/audit/approval-assignments', {
    assigned_by: 'command-center-governance',
    assignee_id: 'quality-reviewer-01',
    target_type: 'artifact',
    target_id: 'command-center-artifact-review',
    approval_role: 'quality-reviewer',
    reason: 'Assign quality review before client delivery.',
    evidence: { assignment_source: 'command-center' },
  });
}

async function routeGovernanceNotification() {
  return apiRequest('/api/audit/notifications/route', {
    routed_by: 'command-center-governance',
    recipient_id: 'quality-reviewer-01',
    channel: 'command-center',
    subject: 'Artifact review assigned',
    message: 'Please review the assigned artifact before client delivery.',
    target_type: 'artifact',
    target_id: 'command-center-artifact-review',
    evidence: { notification_source: 'command-center' },
  });
}

async function loadReviewerWorkload() {
  const body = await apiGet('/api/audit/reviewer-workload');
  return body.workload_report;
}

async function loadGovernanceSLA() {
  const body = await apiGet('/api/audit/governance-sla');
  return body.sla_report;
}

async function loadGovernanceHistory() {
  const body = await apiGet('/api/audit/governance-assignment-history');
  return body.history_report;
}

async function recordReviewerDecision(assignmentId = null) {
  return apiRequest('/api/audit/reviewer-decisions', {
    decided_by: 'quality-reviewer-01',
    reviewer_id: 'quality-reviewer-01',
    target_type: 'artifact',
    target_id: 'command-center-artifact-review',
    assignment_id: assignmentId,
    decision: 'approved',
    reason: 'Reviewer approved the Command Center artifact after governance checks.',
    evidence: { decision_source: 'command-center-governance-panel' },
  });
}

async function exportGovernanceDecisionEvidence() {
  return apiRequest('/api/audit/governance-decision-evidence/export', {});
}

async function escalateReviewerWorkload() {
  return apiRequest('/api/audit/escalations', {
    escalated_by: 'command-center-governance',
    reviewer_id: 'quality-reviewer-01',
    target_type: 'artifact',
    target_id: 'command-center-artifact-review',
    reason: 'Escalate reviewer workload for governance lead attention.',
    escalation_level: 'governance-lead-review',
    evidence: { escalation_source: 'command-center' },
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
  const [deliveryEvidenceReport, setDeliveryEvidenceReport] = useState(null);
  const [deliveryEvidenceExport, setDeliveryEvidenceExport] = useState(null);
  const [slaStateFilter, setSlaStateFilter] = useState(() => (
    readCommandCenterPreference('deliverySlaStateFilter', 'all')
  ));
  const [reviewerQueueFilter, setReviewerQueueFilter] = useState(() => (
    readCommandCenterPreference('deliveryReviewerQueueFilter', 'all')
  ));

  useEffect(() => {
    writeCommandCenterPreference('deliverySlaStateFilter', slaStateFilter);
  }, [slaStateFilter]);

  useEffect(() => {
    writeCommandCenterPreference('deliveryReviewerQueueFilter', reviewerQueueFilter);
  }, [reviewerQueueFilter]);

  useEffect(() => {
    const stateOptions = deliveryEvidenceReport?.sla_filters?.sla_state_options || ['all'];
    const queueOptions = deliveryEvidenceReport?.sla_filters?.reviewer_queue_options || ['all'];
    if (!stateOptions.includes(slaStateFilter)) {
      setSlaStateFilter('all');
    }
    if (!queueOptions.includes(reviewerQueueFilter)) {
      setReviewerQueueFilter('all');
    }
  }, [deliveryEvidenceReport, reviewerQueueFilter, slaStateFilter]);

  const filteredSlaDrilldownItems = useMemo(() => {
    const items = deliveryEvidenceReport?.sla_drilldown_items || [];
    return items.filter((item) => (
      (slaStateFilter === 'all' || item.sla_state === slaStateFilter)
      && (reviewerQueueFilter === 'all' || item.reviewer_queue === reviewerQueueFilter)
    ));
  }, [deliveryEvidenceReport, reviewerQueueFilter, slaStateFilter]);

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

  const refreshDeliveryEvidenceReport = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setDeliveryEvidenceReport(await loadDeliveryEvidenceReport());
      setStatus('ready');
    } catch (evidenceError) {
      setStatus('error');
      setError(evidenceError.message);
    }
  }, []);

  const handleDeliveryEvidenceExport = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      const body = await exportDeliveryGovernanceEvidence();
      setDeliveryEvidenceExport(body.export_package);
      setDeliveryEvidenceReport(body.export_package.delivery_evidence_report);
      setStatus('ready');
    } catch (exportError) {
      setStatus('error');
      setError(exportError.message);
    }
  }, []);

  useEffect(() => {
    refreshMissions();
    refreshDeliveryPackages();
    refreshQualityReviews();
    refreshDeliveryEvidenceReport();
  }, [refreshMissions, refreshDeliveryPackages, refreshQualityReviews, refreshDeliveryEvidenceReport, refreshVersion]);

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

  async function handleArtifactRevision() {
    if (!artifact) return;
    setStatus('loading');
    setError('');
    try {
      const body = await requestArtifactRevision(artifact.artifact_id);
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
      await refreshDeliveryEvidenceReport();
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
      await refreshDeliveryEvidenceReport();
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
          {artifact.status === 'rejected' && (
            <div className="mission-actions">
              <button onClick={handleArtifactRevision} disabled={status === 'loading'}>
                Request Changes
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
        <button onClick={refreshDeliveryEvidenceReport} disabled={status === 'loading'}>
          Refresh Delivery Evidence
        </button>
        <button onClick={handleDeliveryEvidenceExport} disabled={status === 'loading'}>
          {status === 'loading' ? 'Exporting...' : 'Export Delivery Governance Evidence'}
        </button>
      </div>
      {deliveryEvidenceReport && (
        <div className="mission-result">
          <strong>{deliveryEvidenceReport.title}</strong>
          <span>{deliveryEvidenceReport.status}</span>
          <p>
            Signed {deliveryEvidenceReport.signed_bundle_count} / Confirmed {deliveryEvidenceReport.confirmed_delivery_count} / Invalid {deliveryEvidenceReport.invalid_signature_count}
          </p>
          <p>
            SLA {deliveryEvidenceReport.sla_status} / {deliveryEvidenceReport.escalation_required_count} escalations / review after {deliveryEvidenceReport.sla_minutes} minutes
          </p>
          {deliveryEvidenceReport.sla_items?.length ? (
            <div className="mission-history compact-history">
              {deliveryEvidenceReport.sla_items.slice(0, 3).map((item) => (
                <article key={item.delivery_id}>
                  <strong>{item.sla_state}</strong>
                  <span>{item.age_minutes} minutes old</span>
                  <p>{item.plugin_id} / {item.governance_action}</p>
                </article>
              ))}
            </div>
          ) : null}
          {deliveryEvidenceReport.sla_drilldown_summary && (
            <>
              <div className="status-grid">
                <div><strong>{deliveryEvidenceReport.sla_drilldown_summary.signed_item_count}</strong><span>Signed SLA Rows</span></div>
                <div><strong>{deliveryEvidenceReport.sla_drilldown_summary.state_counts?.confirmed ?? 0}</strong><span>Confirmed</span></div>
                <div><strong>{deliveryEvidenceReport.sla_drilldown_summary.state_counts?.review_due ?? 0}</strong><span>Review Due</span></div>
                <div><strong>{deliveryEvidenceReport.sla_drilldown_summary.state_counts?.escalation_required ?? 0}</strong><span>Escalations</span></div>
              </div>
              <div className="filter-grid" aria-label="Delivery SLA dashboard filters">
                <label>
                  SLA State
                  <select
                    value={slaStateFilter}
                    onChange={(event) => {
                      setSlaStateFilter(event.target.value);
                    }}
                    aria-label="Filter delivery SLA by state"
                  >
                    {(deliveryEvidenceReport.sla_filters?.sla_state_options || ['all']).map((option) => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Reviewer Queue
                  <select
                    value={reviewerQueueFilter}
                    onChange={(event) => {
                      setReviewerQueueFilter(event.target.value);
                    }}
                    aria-label="Filter delivery SLA by reviewer queue"
                  >
                    {(deliveryEvidenceReport.sla_filters?.reviewer_queue_options || ['all']).map((option) => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                </label>
                <div>
                  <strong>{filteredSlaDrilldownItems.length}</strong>
                  <span>Filtered Rows</span>
                </div>
              </div>
              <div className="mission-history compact-history">
                {filteredSlaDrilldownItems.length ? (
                  filteredSlaDrilldownItems.slice(0, 5).map((item) => (
                    <article key={`drilldown-${item.delivery_id}`}>
                      <strong>{item.sla_state}</strong>
                      <span>{item.reviewer_queue}</span>
                      <p>{item.plugin_id} / {item.governance_action} / {item.age_minutes} minutes</p>
                    </article>
                  ))
                ) : (
                  <p>{deliveryEvidenceReport.sla_drilldown_summary.empty_state}</p>
                )}
              </div>
            </>
          )}
          {deliveryEvidenceExport && (
            <div className="mission-result compact-result">
              <strong>Delivery Governance Evidence Export Ready</strong>
              <span>{deliveryEvidenceExport.export_id}</span>
              <p>
                {deliveryEvidenceExport.package_manifest.delivery_count} deliveries / {deliveryEvidenceExport.package_manifest.sla_drilldown_count} SLA rows / {deliveryEvidenceExport.status}
              </p>
            </div>
          )}
        </div>
      )}
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

function AuthSessionPanel({ refreshVersion }) {
  const [session, setSession] = useState(null);
  const [requestContext, setRequestContext] = useState(null);
  const [permissionCheck, setPermissionCheck] = useState(null);
  const [permissionEnforcement, setPermissionEnforcement] = useState(null);
  const [humanIdentity, setHumanIdentity] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshSession = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      const [loadedSession, loadedRequestContext, loadedPermissionCheck] = await Promise.all([
        loadAuthSession(),
        loadRequestActorContext(),
        checkGovernancePermission(),
      ]);
      setSession(loadedSession);
      setRequestContext(loadedRequestContext);
      setPermissionCheck(loadedPermissionCheck);
      setStatus('ready');
    } catch (sessionError) {
      setStatus('error');
      setError(sessionError.message);
    }
  }, []);

  useEffect(() => {
    refreshSession();
  }, [refreshSession, refreshVersion]);

  async function handlePermissionEnforcement() {
    setStatus('loading');
    setError('');
    try {
      setPermissionEnforcement(await enforceGovernancePermission());
      setStatus('ready');
    } catch (sessionError) {
      setStatus('error');
      setError(sessionError.message);
    }
  }

  async function handleRequestContextRefresh() {
    setStatus('loading');
    setError('');
    try {
      setRequestContext(await loadRequestActorContext());
      setStatus('ready');
    } catch (sessionError) {
      setStatus('error');
      setError(sessionError.message);
    }
  }

  async function handleHumanIdentityEnforcement() {
    setStatus('loading');
    setError('');
    try {
      setHumanIdentity(await enforceHumanIdentity());
      setStatus('ready');
    } catch (sessionError) {
      setStatus('error');
      setError(sessionError.message);
    }
  }

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Session & Permissions</h2>
        <p>Verify the current operator role and permission contract before governed actions.</p>
      </div>
      <button onClick={refreshSession} disabled={status === 'loading'}>
        {status === 'loading' ? 'Checking...' : 'Refresh Session'}
      </button>
      <button onClick={handleRequestContextRefresh} disabled={status === 'loading'}>
        {status === 'loading' ? 'Reading...' : 'Refresh Actor Context'}
      </button>
      <button onClick={handlePermissionEnforcement} disabled={status === 'loading'}>
        {status === 'loading' ? 'Enforcing...' : 'Enforce Permission Gate'}
      </button>
      <button onClick={handleHumanIdentityEnforcement} disabled={status === 'loading'}>
        {status === 'loading' ? 'Verifying...' : 'Enforce Human Identity'}
      </button>
      {error && <p className="error">{error}</p>}
      {session && permissionCheck && (
        <>
          <div className="mission-result">
            <strong>{session.display_name}</strong>
            <span>{session.data_platform}</span>
            <p>
              {session.roles.join(', ')} / governance.assign_approval:{' '}
              {String(permissionCheck.allowed)}
            </p>
          </div>
          {requestContext && (
            <div className="mission-result">
              <strong>Request Actor Context</strong>
              <span>{requestContext.propagation_mode}</span>
              <p>
                Request <strong>{requestContext.request_id}</strong> runs as{' '}
                <strong>{requestContext.actor_id}</strong>.
              </p>
              <p>
                Actor matches session: <strong>{String(requestContext.actor_matches_session)}</strong>
              </p>
              <p>{requestContext.headers_used.join(', ') || 'session-default'}</p>
            </div>
          )}
          <div className="terms">
            {session.permissions.map((permission) => (
              <span key={permission}>{permission}</span>
            ))}
          </div>
        </>
      )}
      {permissionEnforcement && (
        <div className="mission-result">
          <strong>Permission Gate Granted</strong>
          <span>{permissionEnforcement.enforcement}</span>
          <p>
            <strong>{permissionEnforcement.permission}</strong> granted for{' '}
            <strong>{permissionEnforcement.target_type}</strong>:{' '}
            <strong>{permissionEnforcement.target_id}</strong>.
          </p>
          <p>{permissionEnforcement.data_platform}</p>
        </div>
      )}
      {humanIdentity && (
        <div className="mission-result">
          <strong>Human Identity Verified</strong>
          <span>{humanIdentity.enforcement}</span>
          <p>
            <strong>{humanIdentity.display_name}</strong> verified for{' '}
            <strong>{humanIdentity.target_type}</strong>:{' '}
            <strong>{humanIdentity.target_id}</strong>.
          </p>
          <p>{humanIdentity.data_platform}</p>
        </div>
      )}
    </section>
  );
}

function DataPlatformReadinessPanel({ refreshVersion }) {
  const [readiness, setReadiness] = useState(null);
  const [exportPackage, setExportPackage] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshReadiness = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setReadiness(await loadDataPlatformReadiness());
      setStatus('ready');
    } catch (readinessError) {
      setStatus('error');
      setError(readinessError.message);
    }
  }, []);

  useEffect(() => {
    refreshReadiness();
  }, [refreshReadiness, refreshVersion]);

  async function handleDataPlatformExport() {
    setStatus('loading');
    setError('');
    try {
      const body = await exportDataPlatformReadiness();
      setExportPackage(body.export_package);
      setStatus('ready');
    } catch (readinessError) {
      setStatus('error');
      setError(readinessError.message);
    }
  }

  return (
    <section className="panel mission-panel">
      <div>
        <h2>DB MARIAM Readiness</h2>
        <p>Verify database name, migrations, store modes, and expected tables.</p>
      </div>
      <button onClick={refreshReadiness} disabled={status === 'loading'}>
        {status === 'loading' ? 'Checking...' : 'Refresh DB MARIAM Readiness'}
      </button>
      <button onClick={handleDataPlatformExport} disabled={status === 'loading' || !readiness}>
        Export DB Readiness
      </button>
      {error && <p className="error">{error}</p>}
      {exportPackage && (
        <div className="mission-result">
          <strong>DB Readiness Export Ready</strong>
          <span>{exportPackage.export_id}</span>
          <p>
            {exportPackage.status} / {exportPackage.package_manifest.expected_table_count} tables
          </p>
        </div>
      )}
      {readiness && (
        <>
          <div className="mission-result">
            <strong>{readiness.status}</strong>
            <span>{readiness.database_name}</span>
            <p>{readiness.database_url}</p>
          </div>
          <div className="status-grid">
            <div><strong>{readiness.migrations_found.length}</strong><span>Migrations</span></div>
            <div><strong>{readiness.expected_tables.length}</strong><span>Expected Tables</span></div>
            <div><strong>{readiness.store_modes.mission_store}</strong><span>Mission Store</span></div>
            <div><strong>{readiness.store_modes.audit_store}</strong><span>Audit Store</span></div>
          </div>
          <div className="mission-history">
            {readiness.checks.slice(0, 8).map((check) => (
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

function MigrationRunnerPanel({ refreshVersion }) {
  const [runnerStatus, setRunnerStatus] = useState(null);
  const [exportPackage, setExportPackage] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshRunnerStatus = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setRunnerStatus(await loadMigrationRunnerStatus());
      setStatus('ready');
    } catch (runnerError) {
      setStatus('error');
      setError(runnerError.message);
    }
  }, []);

  useEffect(() => {
    refreshRunnerStatus();
  }, [refreshRunnerStatus, refreshVersion]);

  async function handleMigrationRunnerExport() {
    setStatus('loading');
    setError('');
    try {
      const body = await exportMigrationRunnerStatus();
      setExportPackage(body.export_package);
      setStatus('ready');
    } catch (runnerError) {
      setStatus('error');
      setError(runnerError.message);
    }
  }

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Migration Runner</h2>
        <p>Verify ordered DB MARIAM migration files before applying database changes.</p>
      </div>
      <button onClick={refreshRunnerStatus} disabled={status === 'loading'}>
        {status === 'loading' ? 'Checking...' : 'Refresh Migration Runner'}
      </button>
      <button onClick={handleMigrationRunnerExport} disabled={status === 'loading' || !runnerStatus}>
        Export Migration Runner
      </button>
      {error && <p className="error">{error}</p>}
      {exportPackage && (
        <div className="mission-result">
          <strong>Migration Runner Export Ready</strong>
          <span>{exportPackage.export_id}</span>
          <p>{exportPackage.status} / {exportPackage.package_manifest.migration_count} migrations</p>
        </div>
      )}
      {runnerStatus && (
        <>
          <div className="mission-result">
            <strong>{runnerStatus.status}</strong>
            <span>{runnerStatus.data_platform}</span>
            <p>{runnerStatus.migration_count} migrations ordered for review</p>
          </div>
          <div className="status-grid">
            <div><strong>{runnerStatus.table_definitions}</strong><span>Tables</span></div>
            <div><strong>{runnerStatus.index_definitions}</strong><span>Indexes</span></div>
            <div><strong>{runnerStatus.ordered_migrations.length}</strong><span>Files</span></div>
          </div>
          <div className="mission-history">
            {runnerStatus.checks.map((check) => (
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

function SeedDataPanel({ refreshVersion }) {
  const [seedStatus, setSeedStatus] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshSeedStatus = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setSeedStatus(await loadSeedDataStatus());
      setStatus('ready');
    } catch (seedError) {
      setStatus('error');
      setError(seedError.message);
    }
  }, []);

  useEffect(() => {
    refreshSeedStatus();
  }, [refreshSeedStatus, refreshVersion]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Seed Data</h2>
        <p>Verify initial non-secret DB MARIAM seed metadata before first-run setup.</p>
      </div>
      <button onClick={refreshSeedStatus} disabled={status === 'loading'}>
        {status === 'loading' ? 'Checking...' : 'Refresh Seed Data'}
      </button>
      {error && <p className="error">{error}</p>}
      {seedStatus && (
        <>
          <div className="mission-result">
            <strong>{seedStatus.status}</strong>
            <span>{seedStatus.seed_id}</span>
            <p>{seedStatus.item_count} seed items / secrets: {String(seedStatus.contains_secrets)}</p>
          </div>
          <div className="mission-history">
            {seedStatus.checks.map((check) => (
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

function BackupReadinessPanel({ refreshVersion }) {
  const [backupStatus, setBackupStatus] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshBackupReadiness = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setBackupStatus(await loadBackupReadiness());
      setStatus('ready');
    } catch (backupError) {
      setStatus('error');
      setError(backupError.message);
    }
  }, []);

  useEffect(() => {
    refreshBackupReadiness();
  }, [refreshBackupReadiness, refreshVersion]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Backup Readiness</h2>
        <p>Verify DB MARIAM backup policy, restore approval, encryption, and audit gates.</p>
      </div>
      <button onClick={refreshBackupReadiness} disabled={status === 'loading'}>
        {status === 'loading' ? 'Checking...' : 'Refresh Backup Readiness'}
      </button>
      {error && <p className="error">{error}</p>}
      {backupStatus && (
        <>
          <div className="mission-result">
            <strong>{backupStatus.status}</strong>
            <span>{backupStatus.policy_id}</span>
            <p>{backupStatus.scope_count} storage areas / secrets: {String(backupStatus.contains_secrets)}</p>
          </div>
          <div className="mission-history">
            {backupStatus.checks.map((check) => (
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

function PluginSchemaIsolationPanel({ refreshVersion }) {
  const [schemaStatus, setSchemaStatus] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshSchemaIsolation = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setSchemaStatus(await loadPluginSchemaIsolation());
      setStatus('ready');
    } catch (schemaError) {
      setStatus('error');
      setError(schemaError.message);
    }
  }, []);

  useEffect(() => {
    refreshSchemaIsolation();
  }, [refreshSchemaIsolation, refreshVersion]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Plugin Schema Isolation</h2>
        <p>Verify shared DB MARIAM tables and private Plugin-managed Business Unit boundaries.</p>
      </div>
      <button onClick={refreshSchemaIsolation} disabled={status === 'loading'}>
        {status === 'loading' ? 'Checking...' : 'Refresh Schema Isolation'}
      </button>
      {error && <p className="error">{error}</p>}
      {schemaStatus && (
        <>
          <div className="mission-result">
            <strong>{schemaStatus.status}</strong>
            <span>{schemaStatus.manifest_id}</span>
            <p>
              {schemaStatus.plugin_schema_count} plugin schemas / {schemaStatus.private_table_count} private
              tables / secrets: {String(schemaStatus.contains_secrets)}
            </p>
          </div>
          <div className="status-grid">
            <div><strong>{schemaStatus.plugin_schema_count}</strong><span>Plugin Schemas</span></div>
            <div><strong>{schemaStatus.shared_table_count}</strong><span>Shared Tables</span></div>
            <div><strong>{schemaStatus.private_table_count}</strong><span>Private Tables</span></div>
          </div>
          <div className="mission-history">
            {schemaStatus.checks.map((check) => (
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

function DockerPersistencePanel({ refreshVersion }) {
  const [dockerStatus, setDockerStatus] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshDockerPersistence = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setDockerStatus(await loadDockerPersistence());
      setStatus('ready');
    } catch (dockerError) {
      setStatus('error');
      setError(dockerError.message);
    }
  }, []);

  useEffect(() => {
    refreshDockerPersistence();
  }, [refreshDockerPersistence, refreshVersion]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Docker Persistence</h2>
        <p>Verify local Docker uses DB MARIAM Postgres stores and read-only migration startup.</p>
      </div>
      <button onClick={refreshDockerPersistence} disabled={status === 'loading'}>
        {status === 'loading' ? 'Checking...' : 'Refresh Docker Persistence'}
      </button>
      {error && <p className="error">{error}</p>}
      {dockerStatus && (
        <>
          <div className="mission-result">
            <strong>{dockerStatus.status}</strong>
            <span>{dockerStatus.data_platform}</span>
            <p>{dockerStatus.postgres_store_count} Postgres stores / {dockerStatus.database_url_masked}</p>
          </div>
          <div className="mission-history">
            {dockerStatus.checks.map((check) => (
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

function LiveDbSmokePanel({ refreshVersion }) {
  const [smokeStatus, setSmokeStatus] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshLiveDbSmoke = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setSmokeStatus(await loadLiveDbSmoke());
      setStatus('ready');
    } catch (smokeError) {
      setStatus('error');
      setError(smokeError.message);
    }
  }, []);

  useEffect(() => {
    refreshLiveDbSmoke();
  }, [refreshLiveDbSmoke, refreshVersion]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Live DB Smoke</h2>
        <p>Verify Docker and Compose readiness before running the DB MARIAM Postgres smoke command.</p>
      </div>
      <button onClick={refreshLiveDbSmoke} disabled={status === 'loading'}>
        {status === 'loading' ? 'Checking...' : 'Refresh Live DB Smoke'}
      </button>
      {error && <p className="error">{error}</p>}
      {smokeStatus && (
        <>
          <div className="mission-result">
            <strong>{smokeStatus.status}</strong>
            <span>{smokeStatus.data_platform}</span>
            <p>{smokeStatus.smoke_command}</p>
          </div>
          <div className="status-grid">
            <div><strong>{String(smokeStatus.docker_available)}</strong><span>Docker</span></div>
            <div><strong>{String(smokeStatus.compose_config_valid)}</strong><span>Compose Config</span></div>
          </div>
          <div className="mission-history">
            {smokeStatus.checks.map((check) => (
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

function DockerContainerExecutionPanel({ refreshVersion }) {
  const [executionStatus, setExecutionStatus] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshDockerExecution = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setExecutionStatus(await loadDockerContainerExecution());
      setStatus('ready');
    } catch (executionError) {
      setStatus('error');
      setError(executionError.message);
    }
  }, []);

  useEffect(() => {
    refreshDockerExecution();
  }, [refreshDockerExecution, refreshVersion]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Docker Container Execution</h2>
        <p>Verify the DB MARIAM postgres container is running and accepting connections.</p>
      </div>
      <button onClick={refreshDockerExecution} disabled={status === 'loading'}>
        {status === 'loading' ? 'Checking...' : 'Refresh Docker Execution'}
      </button>
      {error && <p className="error">{error}</p>}
      {executionStatus && (
        <>
          <div className="mission-result">
            <strong>{executionStatus.status}</strong>
            <span>{executionStatus.data_platform}</span>
            <p>
              Postgres running: <strong>{String(executionStatus.postgres_running)}</strong> /
              pg_isready: <strong>{String(executionStatus.pg_isready)}</strong>
            </p>
            <p>{executionStatus.services.join(', ')}</p>
          </div>
          <div className="terms">
            {executionStatus.execution_commands.map((command) => (
              <span key={command}>{command}</span>
            ))}
          </div>
          <div className="mission-history">
            {executionStatus.checks.map((check) => (
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

function LiveDatabaseWriteSmokePanel({ refreshVersion }) {
  const [writeStatus, setWriteStatus] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState(null);

  const runWriteSmoke = useCallback(async () => {
    setStatus('loading');
    setError(null);
    try {
      setWriteStatus(await runLiveDatabaseWriteSmoke());
      setStatus('ready');
    } catch (writeError) {
      setStatus('error');
      setError(createPanelError(writeError, 'Run DB MARIAM Write Smoke', runWriteSmoke));
    }
  }, []);

  useEffect(() => {
    runWriteSmoke();
  }, [runWriteSmoke, refreshVersion]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>DB MARIAM Live Write Smoke</h2>
        <p>Write and read a smoke audit record and runtime event against the live Postgres database.</p>
      </div>
      <button onClick={runWriteSmoke} disabled={status === 'loading'}>
        {status === 'loading' ? 'Writing...' : 'Run DB MARIAM Write Smoke'}
      </button>
      <ErrorBanner error={error} />
      {writeStatus && (
        <>
          <div className="mission-result">
            <strong>{writeStatus.status}</strong>
            <span>{writeStatus.data_platform}</span>
            <p>
              Audit: <strong>{writeStatus.audit_id}</strong>
            </p>
            <p>
              Event: <strong>{writeStatus.event_id}</strong>
            </p>
          </div>
          <div className="status-grid">
            <div><strong>{String(writeStatus.audit_written)}</strong><span>Audit Written</span></div>
            <div><strong>{String(writeStatus.event_written)}</strong><span>Event Written</span></div>
          </div>
          <div className="mission-history">
            {writeStatus.checks.map((check) => (
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

function LiveRepositoryWriteSmokePanel({ refreshVersion }) {
  const [writeStatus, setWriteStatus] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState(null);

  const runRepositoryWriteSmoke = useCallback(async () => {
    setStatus('loading');
    setError(null);
    try {
      setWriteStatus(await runLiveRepositoryWriteSmoke());
      setStatus('ready');
    } catch (writeError) {
      setStatus('error');
      setError(createPanelError(writeError, 'Run Repository Write Smoke', runRepositoryWriteSmoke));
    }
  }, []);

  useEffect(() => {
    runRepositoryWriteSmoke();
  }, [runRepositoryWriteSmoke, refreshVersion]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>DB MARIAM Repository Write Smoke</h2>
        <p>Write and read mission, artifact, and delivery package records against the live Postgres database.</p>
      </div>
      <button onClick={runRepositoryWriteSmoke} disabled={status === 'loading'}>
        {status === 'loading' ? 'Writing...' : 'Run Repository Write Smoke'}
      </button>
      <ErrorBanner error={error} />
      {writeStatus && (
        <>
          <div className="mission-result">
            <strong>{writeStatus.status}</strong>
            <span>{writeStatus.data_platform}</span>
            <p>Mission: <strong>{writeStatus.mission_id}</strong></p>
            <p>Artifact: <strong>{writeStatus.artifact_id}</strong></p>
            <p>Delivery: <strong>{writeStatus.delivery_id}</strong></p>
          </div>
          <div className="status-grid">
            <div><strong>{String(writeStatus.mission_written)}</strong><span>Mission Written</span></div>
            <div><strong>{String(writeStatus.artifact_written)}</strong><span>Artifact Written</span></div>
            <div><strong>{String(writeStatus.delivery_written)}</strong><span>Delivery Written</span></div>
          </div>
          <div className="mission-history">
            {writeStatus.checks.map((check) => (
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

function DataPlatformEvidenceStorePanel({
  title,
  description,
  refreshLabel,
  loadRecords,
  exportRecords,
  recordKey,
  renderRecord,
  exportSummaryLabel,
  refreshVersion,
}) {
  const [storeStatus, setStoreStatus] = useState(null);
  const [exportPackage, setExportPackage] = useState(null);
  const [status, setStatus] = useState('idle');
  const [exportStatus, setExportStatus] = useState('idle');
  const [error, setError] = useState('');
  const [exportError, setExportError] = useState('');

  const refreshStore = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setStoreStatus(await loadRecords());
      setStatus('ready');
    } catch (storeError) {
      setStatus('error');
      setError(storeError.message);
    }
  }, [loadRecords]);

  const exportStore = useCallback(async () => {
    setExportStatus('loading');
    setExportError('');
    try {
      const body = await exportRecords();
      setExportPackage(body.export_package);
      setExportStatus('ready');
    } catch (storeExportError) {
      setExportStatus('error');
      setExportError(storeExportError.message);
    }
  }, [exportRecords]);

  useEffect(() => {
    refreshStore();
  }, [refreshStore, refreshVersion]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <button onClick={refreshStore} disabled={status === 'loading'}>
        {status === 'loading' ? 'Checking...' : refreshLabel}
      </button>
      <button onClick={exportStore} disabled={exportStatus === 'loading'}>
        {exportStatus === 'loading' ? 'Exporting...' : exportSummaryLabel}
      </button>
      {error && <p className="error">{error}</p>}
      {exportError && <p className="error">{exportError}</p>}
      {storeStatus && (
        <>
          <div className="mission-result">
            <strong>{storeStatus.status}</strong>
            <span>{storeStatus.data_platform}</span>
            <p>{storeStatus.record_count} recent records available for governance review.</p>
          </div>
          <div className="mission-history">
            {storeStatus.records.slice(0, 5).map((record) => (
              <article key={record[recordKey]}>
                {renderRecord(record)}
              </article>
            ))}
          </div>
          <div className="mission-history">
            {storeStatus.checks.map((check) => (
              <article key={check.name}>
                <strong>{check.name}</strong>
                <span>{check.status}</span>
                <p>{check.detail}</p>
              </article>
            ))}
          </div>
          {exportPackage && (
            <div className="mission-result">
              <strong>{exportPackage.export_id}</strong>
              <span>{exportPackage.status}</span>
              <p>
                {exportPackage.package_manifest.record_count} records / {exportPackage.data_platform}
              </p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function AuditEventArchivePanel({ refreshVersion }) {
  return (
    <DataPlatformEvidenceStorePanel
      title="DB MARIAM Audit Event Archive"
      description="Read recent governed audit/event archive records from DB MARIAM."
      refreshLabel="Refresh Audit Event Archive"
      loadRecords={loadAuditEventArchiveRecords}
      exportRecords={exportAuditEventArchiveRecords}
      recordKey="archive_id"
      exportSummaryLabel="Export Audit Event Archive Evidence"
      refreshVersion={refreshVersion}
      renderRecord={(record) => (
        <>
          <strong>{record.action}</strong>
          <span>{record.decision}</span>
          <p>{record.archive_reason}</p>
          <time>{new Date(record.created_at).toLocaleString()}</time>
        </>
      )}
    />
  );
}

function MetricsStorePanel({ refreshVersion }) {
  return (
    <DataPlatformEvidenceStorePanel
      title="DB MARIAM Metrics Store"
      description="Read recent operational metric records from DB MARIAM."
      refreshLabel="Refresh Metrics Store"
      loadRecords={loadMetricsStoreRecords}
      exportRecords={exportMetricsStoreRecords}
      recordKey="metric_id"
      exportSummaryLabel="Export Metrics Store Evidence"
      refreshVersion={refreshVersion}
      renderRecord={(record) => (
        <>
          <strong>{record.metric_name}</strong>
          <span>{record.status}</span>
          <p>
            {record.metric_value} {record.metric_unit} from {record.source}
          </p>
          <time>{new Date(record.created_at).toLocaleString()}</time>
        </>
      )}
    />
  );
}

function FrontendRegressionSnapshotPanel({ refreshVersion }) {
  const [snapshot, setSnapshot] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshFrontendRegression = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setSnapshot(await loadFrontendRegressionSnapshot());
      setStatus('ready');
    } catch (snapshotError) {
      setStatus('error');
      setError(snapshotError.message);
    }
  }, []);

  useEffect(() => {
    refreshFrontendRegression();
  }, [refreshFrontendRegression, refreshVersion]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Frontend Regression Snapshot</h2>
        <p>Verify critical Command Center controls, responsive states, and DB MARIAM visibility from the React source.</p>
      </div>
      <button onClick={refreshFrontendRegression} disabled={status === 'loading'}>
        {status === 'loading' ? 'Checking...' : 'Refresh Frontend Regression'}
      </button>
      {error && <p className="error">{error}</p>}
      {snapshot && (
        <>
          <div className="mission-result">
            <strong>{snapshot.status}</strong>
            <span>{snapshot.data_platform}</span>
            <p>{snapshot.artifact_path}</p>
          </div>
          <div className="status-grid">
            <div><strong>{snapshot.controls_checked.length}</strong><span>Controls Checked</span></div>
            <div><strong>{snapshot.missing_controls.length}</strong><span>Missing Controls</span></div>
            <div><strong>{snapshot.viewport_contracts.length}</strong><span>Viewport Contracts</span></div>
            <div><strong>{snapshot.missing_viewports.length}</strong><span>Missing Viewports</span></div>
            <div><strong>{snapshot.keyboard_traversal_targets?.length ?? 0}</strong><span>Keyboard Targets</span></div>
            <div><strong>{snapshot.missing_keyboard_traversal_targets?.length ?? 0}</strong><span>Missing Keyboard</span></div>
          </div>
          <div className="terms">
            {snapshot.controls_checked.map((control) => (
              <span key={control}>{control}</span>
            ))}
          </div>
          {snapshot.keyboard_traversal_targets?.length ? (
            <div className="terms">
              {snapshot.keyboard_traversal_targets.map((target) => (
                <span key={target}>{target}</span>
              ))}
            </div>
          ) : null}
          <div className="mission-history">
            {snapshot.checks.map((check) => (
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

function FrontendVisualContractPanel({ refreshVersion }) {
  const [contract, setContract] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshVisualContract = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setContract(await loadFrontendVisualContract());
      setStatus('ready');
    } catch (contractError) {
      setStatus('error');
      setError(contractError.message);
    }
  }, []);

  useEffect(() => {
    refreshVisualContract();
  }, [refreshVisualContract, refreshVersion]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Frontend Visual Contract</h2>
        <p>Verify design tokens, layout contracts, breakpoints, and screenshot targets for the Command Center.</p>
      </div>
      <button onClick={refreshVisualContract} disabled={status === 'loading'}>
        {status === 'loading' ? 'Checking...' : 'Refresh Visual Contract'}
      </button>
      {error && <p className="error">{error}</p>}
      {contract && (
        <>
          <div className="mission-result">
            <strong>{contract.status}</strong>
            <span>{contract.data_platform}</span>
            <p>{contract.artifact_path}</p>
          </div>
          <div className="status-grid">
            <div><strong>{contract.design_tokens_checked.length}</strong><span>Design Tokens</span></div>
            <div><strong>{contract.layout_contracts_checked.length}</strong><span>Layout Contracts</span></div>
            <div><strong>{contract.breakpoint_contracts_checked.length}</strong><span>Breakpoints</span></div>
            <div><strong>{contract.screenshot_targets.length}</strong><span>Screenshot Targets</span></div>
          </div>
          <div className="terms">
            {contract.screenshot_targets.map((target) => (
              <span key={target}>{target}</span>
            ))}
          </div>
          <div className="mission-history">
            {contract.checks.map((check) => (
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

function FrontendBrowserScreenshotPlanPanel({ refreshVersion }) {
  const [plan, setPlan] = useState(null);
  const [captureReport, setCaptureReport] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshScreenshotPlan = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setPlan(await loadFrontendBrowserScreenshotPlan());
      setStatus('ready');
    } catch (planError) {
      setStatus('error');
      setError(planError.message);
    }
  }, []);

  const refreshScreenshotCapture = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setCaptureReport(await loadFrontendBrowserScreenshotCapture());
      setStatus('ready');
    } catch (captureError) {
      setStatus('error');
      setError(captureError.message);
    }
  }, []);

  useEffect(() => {
    refreshScreenshotPlan();
    refreshScreenshotCapture();
  }, [refreshScreenshotPlan, refreshScreenshotCapture, refreshVersion]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Browser Screenshot Artifact Plan</h2>
        <p>Define desktop, tablet, and mobile screenshot artifacts for critical Command Center sections.</p>
      </div>
      <button onClick={refreshScreenshotPlan} disabled={status === 'loading'}>
        {status === 'loading' ? 'Planning...' : 'Refresh Screenshot Plan'}
      </button>
      <button onClick={refreshScreenshotCapture} disabled={status === 'loading'}>
        {status === 'loading' ? 'Checking...' : 'Refresh Screenshot Capture'}
      </button>
      {error && <p className="error">{error}</p>}
      {plan && (
        <>
          <div className="mission-result">
            <strong>{plan.status}</strong>
            <span>{plan.data_platform}</span>
            <p>{plan.artifact_path}</p>
          </div>
          <div className="status-grid">
            <div><strong>{plan.viewport_targets.length}</strong><span>Viewports</span></div>
            <div><strong>{plan.critical_sections.length}</strong><span>Critical Sections</span></div>
            <div><strong>{plan.screenshot_artifacts.length}</strong><span>Screenshot Artifacts</span></div>
            <div><strong>{plan.required_browser_checks.length}</strong><span>Browser Checks</span></div>
          </div>
          <div className="terms">
            {plan.viewport_targets.map((target) => (
              <span key={target.name}>{target.name}: {target.width}x{target.height}</span>
            ))}
          </div>
          <div className="terms">
            {plan.screenshot_artifacts.map((artifact) => (
              <span key={artifact}>{artifact}</span>
            ))}
          </div>
          <div className="mission-history">
            {plan.checks.map((check) => (
              <article key={check.name}>
                <strong>{check.name}</strong>
                <span>{check.status}</span>
                <p>{check.detail}</p>
              </article>
            ))}
          </div>
        </>
      )}
      {captureReport && (
        <>
          <div className="mission-result">
            <strong>{captureReport.title}</strong>
            <span>{captureReport.status}</span>
            <p>{captureReport.artifact_path}</p>
          </div>
          <div className="status-grid">
            <div><strong>{captureReport.artifact_count}</strong><span>Captured</span></div>
            <div><strong>{captureReport.artifacts.filter((artifact) => artifact.exists).length}</strong><span>Files Found</span></div>
            <div><strong>{captureReport.artifacts.filter((artifact) => artifact.png_signature).length}</strong><span>PNG Valid</span></div>
            <div><strong>{captureReport.checks.filter((check) => check.status === 'ready').length}</strong><span>Ready Checks</span></div>
          </div>
          <div className="mission-history">
            {captureReport.artifacts.map((artifact) => (
              <article key={artifact.relative_path}>
                <strong>{artifact.viewport}</strong>
                <span>{artifact.png_signature ? 'png-valid' : 'missing'}</span>
                <p>{artifact.relative_path} / {artifact.bytes} bytes</p>
              </article>
            ))}
          </div>
          {captureReport.thumbnail_previews?.length ? (
            <div className="screenshot-thumbnails">
              {captureReport.thumbnail_previews.map((preview) => (
                <figure key={preview.relative_path}>
                  {preview.available ? (
                    <img src={preview.data_url} alt={preview.label} />
                  ) : (
                    <div className="thumbnail-missing">Missing preview</div>
                  )}
                  <figcaption>{preview.viewport} thumbnail</figcaption>
                </figure>
              ))}
            </div>
          ) : null}
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

function VerificationAutomationPanel({ refreshVersion }) {
  const [contract, setContract] = useState(null);
  const [failureSummaryExport, setFailureSummaryExport] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshAutomation = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setContract(await loadVerificationAutomation());
      setStatus('ready');
    } catch (automationError) {
      setStatus('error');
      setError(automationError.message);
    }
  }, []);

  useEffect(() => {
    refreshAutomation();
  }, [refreshAutomation, refreshVersion]);

  const handleFailureSummaryExport = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      const body = await exportVerificationFailureSummary();
      setFailureSummaryExport(body.export_package);
      setContract(await loadVerificationAutomation());
      setStatus('ready');
    } catch (exportError) {
      setStatus('error');
      setError(exportError.message);
    }
  }, []);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Verification Automation Contract</h2>
        <p>Review local verification coverage, CI status, commands, endpoints, and generated evidence.</p>
      </div>
      <button onClick={refreshAutomation} disabled={status === 'loading'}>
        {status === 'loading' ? 'Checking...' : 'Refresh Verification Automation'}
      </button>
      <button onClick={handleFailureSummaryExport} disabled={status === 'loading'}>
        {status === 'loading' ? 'Exporting...' : 'Export Failure Summary'}
      </button>
      {error && <p className="error">{error}</p>}
      {contract && (
        <>
          <div className="mission-result">
            <strong>{contract.status}</strong>
            <span>{contract.data_platform}</span>
            <p>{contract.artifact_path}</p>
          </div>
          <div className="status-grid">
            <div><strong>{contract.local_automation_status}</strong><span>Local Automation</span></div>
            <div><strong>{contract.ci_status}</strong><span>CI Status</span></div>
            <div><strong>{contract.required_commands.length}</strong><span>Commands</span></div>
            <div><strong>{contract.required_endpoints.length}</strong><span>Endpoints</span></div>
            <div><strong>{contract.persisted_verification_run_count}</strong><span>Persisted Runs</span></div>
          </div>
          <div className="mission-result">
            <strong>Persisted local verification runs</strong>
            <span>{contract.persisted_run_log_path}</span>
            <p>Local CLI executions are written to a DB MARIAM verification artifact.</p>
          </div>
          {contract.ci_artifact_retention && (
            <div className="mission-result">
              <strong>{contract.ci_artifact_retention.artifact_name}</strong>
              <span>{contract.ci_artifact_retention.retention_days} days retention</span>
              <p>{contract.ci_artifact_retention.run_artifacts_url}</p>
            </div>
          )}
          {contract.ci_badge && (
            <div className="mission-result">
              <strong>{contract.ci_badge.label} CI badge</strong>
              <span>{contract.ci_badge.branch}</span>
              <p>{contract.ci_badge.badge_url}</p>
            </div>
          )}
          {contract.latest_run_status && (
            <div className="mission-result">
              <strong>Latest CI run polling</strong>
              <span>
                {contract.latest_run_status.polling_status} / {contract.latest_run_status.ingestion_status}
              </span>
              <p>{contract.latest_run_status.api_url}</p>
            </div>
          )}
          {contract.ci_run_ingestion && (
            <div className="mission-result">
              <strong>Latest CI run result ingestion</strong>
              <span>{contract.ci_run_ingestion.ingestion_status}</span>
              <p>
                {contract.ci_run_ingestion.latest_run?.name} /{' '}
                {contract.ci_run_ingestion.latest_run?.status} /{' '}
                {contract.ci_run_ingestion.latest_run?.conclusion}
              </p>
            </div>
          )}
          {contract.local_history_comparison && (
            <div className="mission-result">
              <strong>Local verification history comparison</strong>
              <span>{contract.local_history_comparison.status}</span>
              <p>
                Snapshots {contract.local_history_comparison.snapshot_count} / ready checks delta{' '}
                {contract.local_history_comparison.ready_checks_delta}
              </p>
            </div>
          )}
          {failureSummaryExport && (
            <div className="mission-result">
              <strong>Verification Failure Summary Export Ready</strong>
              <span>
                {failureSummaryExport.status} / {failureSummaryExport.package_manifest.failed_run_count} failed runs
              </span>
              <p>
                {failureSummaryExport.export_id} / latest:{' '}
                {failureSummaryExport.package_manifest.latest_run_status}
              </p>
            </div>
          )}
          <div className="terms">
            {contract.required_commands.map((command) => (
              <span key={command}>{command}</span>
            ))}
          </div>
          <div className="mission-history">
            {contract.checks.map((check) => (
              <article key={check.name}>
                <strong>{check.name}</strong>
                <span>{check.status}</span>
                <p>{check.detail}</p>
              </article>
            ))}
          </div>
          <div className="mission-history">
            {contract.persisted_verification_runs.length ? (
              contract.persisted_verification_runs.slice(0, 5).map((run) => (
                <article key={run.run_id}>
                  <strong>{run.status}</strong>
                  <span>{run.command}</span>
                  <p>{run.run_id} / {run.updated_at}</p>
                </article>
              ))
            ) : (
              <p>No local verification CLI runs persisted yet.</p>
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
  const [exportPackage, setExportPackage] = useState(null);
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

  async function handleCompletionReportExport() {
    setStatus('loading');
    setError('');
    try {
      const body = await exportCompletionReport();
      setExportPackage(body.export_package);
      setStatus('ready');
    } catch (completionError) {
      setStatus('error');
      setError(completionError.message);
    }
  }

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Completion Report</h2>
        <p>Review verified project readiness across frontend, backend, data, governance, and tests.</p>
      </div>
      <button onClick={refreshReport} disabled={status === 'loading'}>
        {status === 'loading' ? 'Loading...' : 'Refresh Completion Report'}
      </button>
      <button onClick={handleCompletionReportExport} disabled={status === 'loading' || !report}>
        Export Completion Report
      </button>
      {error && <p className="error">{error}</p>}
      {exportPackage && (
        <div className="mission-result">
          <strong>Completion Report Export Ready</strong>
          <span>{exportPackage.export_id}</span>
          <p>
            {exportPackage.status} / {exportPackage.package_manifest.completion_percent}% complete
          </p>
        </div>
      )}
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

function ImplementationRoadmapPanel({ refreshVersion }) {
  const [roadmap, setRoadmap] = useState(null);
  const [exportPackage, setExportPackage] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const refreshRoadmap = useCallback(async () => {
    setStatus('loading');
    setError('');
    try {
      setRoadmap(await loadImplementationRoadmap());
      setStatus('ready');
    } catch (roadmapError) {
      setStatus('error');
      setError(roadmapError.message);
    }
  }, []);

  useEffect(() => {
    refreshRoadmap();
  }, [refreshRoadmap, refreshVersion]);

  async function handleRoadmapExport() {
    setStatus('loading');
    setError('');
    try {
      const body = await exportImplementationRoadmap();
      setExportPackage(body.export_package);
      setStatus('ready');
    } catch (roadmapError) {
      setStatus('error');
      setError(roadmapError.message);
    }
  }

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Implementation Roadmap</h2>
        <p>Prioritize the next verified build steps from the completion report.</p>
      </div>
      <button onClick={refreshRoadmap} disabled={status === 'loading'}>
        {status === 'loading' ? 'Loading...' : 'Refresh Roadmap'}
      </button>
      <button onClick={handleRoadmapExport} disabled={status === 'loading' || !roadmap}>
        Export Roadmap
      </button>
      {error && <p className="error">{error}</p>}
      {exportPackage && (
        <div className="mission-result">
          <strong>Roadmap Export Ready</strong>
          <span>{exportPackage.export_id}</span>
          <p>{exportPackage.status} / {exportPackage.package_manifest.item_count} items</p>
        </div>
      )}
      {roadmap && (
        <>
          <div className="mission-result">
            <strong>{roadmap.status}</strong>
            <span>{roadmap.data_platform}</span>
            <p>{roadmap.operating_rule}</p>
          </div>
          <div className="mission-history">
            {roadmap.items.map((item) => (
              <article key={item.area}>
                <strong>{item.area}</strong>
                <span>{item.priority} / {item.current_completion_percent}%</span>
                <p>{item.next_step}</p>
                <p>{item.acceptance_signal}</p>
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

function PluginWorkspacePanel({ onActionComplete }) {
  const [workspace, setWorkspace] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  async function handleOpenLiveWorkspace() {
    setStatus('loading');
    setError('');
    try {
      let plugins = await loadPlugins();
      if (!plugins.some((plugin) => plugin.plugin_id === 'crm')) {
        const body = await registerCRMPlugin();
        plugins = [body.plugin, ...plugins];
        onActionComplete();
      }
      const plugin = plugins.find((item) => item.plugin_id === 'crm') || plugins[0];
      setWorkspace(await loadPluginWorkspace(plugin.plugin_id));
      setStatus('ready');
    } catch (workspaceError) {
      setStatus('error');
      setError(workspaceError.message);
    }
  }

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Plugin Workspaces</h2>
        <p>Open Plugin-managed Business Units as simple app cards with dashboard, settings, Chief, swarm, and data boundaries.</p>
      </div>
      <button onClick={handleOpenLiveWorkspace} disabled={status === 'loading'}>
        {status === 'loading' ? 'Opening...' : 'Open Live Plugin Workspace'}
      </button>
      {error && <p className="error">{error}</p>}
      {workspace && (
        <div className="mission-result">
          <h3>{workspace.title}</h3>
          <p>
            <strong>{workspace.chief_agent.role}</strong> operates at{' '}
            <strong>{workspace.dashboard.dashboard_route}</strong> with{' '}
            <strong>{workspace.swarm.length}</strong> swarm roles.
          </p>
          <p>
            Data boundary: <strong>{workspace.data_boundary.boundary}</strong> on{' '}
            <strong>{workspace.data_boundary.platform}</strong>.
          </p>
          <div className="app-meta">
            {workspace.workspace_actions.map((action) => (
              <span key={action.label}>{action.label}: {action.api}</span>
            ))}
          </div>
          <p>
            Private tables:{' '}
            <strong>{workspace.data_boundary.private_tables.join(', ')}</strong>
          </p>
        </div>
      )}
      <div className="app-grid">
        {pluginWorkspaceApps.map((plugin) => (
          <article className="app-card" key={plugin.name}>
            <div>
              <strong>{plugin.name}</strong>
              <span>{plugin.status}</span>
            </div>
            <p>{plugin.chief} owns the {plugin.dataBoundary} private schema boundary.</p>
            <div className="app-meta">
              <span>Dashboard: {plugin.route}</span>
              <span>Settings: {plugin.settings}</span>
              <span>Swarm: {plugin.swarm.join(', ')}</span>
              <span>Workflows: {plugin.workflows.join(', ')}</span>
            </div>
            <div className="mission-actions">
              <a href="#missions">Open</a>
              <a href="#data-platform">Data Boundary</a>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ResponsiveStatePanel() {
  return (
    <section className="panel mission-panel">
      <div>
        <h2>Responsive States</h2>
        <p>Keep the Command Center simple across mobile, tablet, and desktop without exposing internal complexity.</p>
      </div>
      <div className="app-grid responsive-state-grid">
        {responsiveStates.map((state) => (
          <article className="app-card" key={state.mode}>
            <div>
              <strong>{state.mode}</strong>
              <span>{state.layout}</span>
            </div>
            <p>{state.focus}</p>
          </article>
        ))}
      </div>
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
  const [assignmentRecord, setAssignmentRecord] = useState(null);
  const [notificationRecord, setNotificationRecord] = useState(null);
  const [workloadReport, setWorkloadReport] = useState(null);
  const [slaReport, setSlaReport] = useState(null);
  const [governanceHistory, setGovernanceHistory] = useState(null);
  const [reviewerDecisionRecord, setReviewerDecisionRecord] = useState(null);
  const [decisionEvidenceExport, setDecisionEvidenceExport] = useState(null);
  const [decisionReviewerFilter, setDecisionReviewerFilter] = useState(() => (
    readCommandCenterPreference('governanceDecisionReviewerFilter', 'all')
  ));
  const [decisionOutcomeFilter, setDecisionOutcomeFilter] = useState(() => (
    readCommandCenterPreference('governanceDecisionOutcomeFilter', 'all')
  ));
  const [escalationRecord, setEscalationRecord] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState(null);

  useEffect(() => {
    writeCommandCenterPreference('governanceDecisionReviewerFilter', decisionReviewerFilter);
  }, [decisionReviewerFilter]);

  useEffect(() => {
    writeCommandCenterPreference('governanceDecisionOutcomeFilter', decisionOutcomeFilter);
  }, [decisionOutcomeFilter]);

  const decisionReviewerOptions = useMemo(() => {
    const reviewers = governanceHistory?.decisions?.map((decision) => decision.reviewer_id) || [];
    return ['all', ...Array.from(new Set(reviewers)).sort()];
  }, [governanceHistory]);

  const decisionOutcomeOptions = useMemo(() => {
    const outcomes = governanceHistory?.decisions?.map((decision) => decision.decision) || [];
    return ['all', ...Array.from(new Set(outcomes)).sort()];
  }, [governanceHistory]);

  useEffect(() => {
    if (!decisionReviewerOptions.includes(decisionReviewerFilter)) {
      setDecisionReviewerFilter('all');
    }
    if (!decisionOutcomeOptions.includes(decisionOutcomeFilter)) {
      setDecisionOutcomeFilter('all');
    }
  }, [decisionOutcomeFilter, decisionOutcomeOptions, decisionReviewerFilter, decisionReviewerOptions]);

  const filteredReviewerDecisions = useMemo(() => (
    (governanceHistory?.decisions || []).filter((decision) => (
      (decisionReviewerFilter === 'all' || decision.reviewer_id === decisionReviewerFilter)
      && (decisionOutcomeFilter === 'all' || decision.decision === decisionOutcomeFilter)
    ))
  ), [decisionOutcomeFilter, decisionReviewerFilter, governanceHistory]);

  const refreshReviewerWorkload = useCallback(async () => {
    setStatus('loading');
    setError(null);
    try {
      setWorkloadReport(await loadReviewerWorkload());
      setSlaReport(await loadGovernanceSLA());
      setGovernanceHistory(await loadGovernanceHistory());
      setStatus('ready');
    } catch (auditError) {
      setStatus('error');
      setError(createPanelError(auditError, 'Refresh Reviewer Workload', refreshReviewerWorkload));
    }
  }, []);

  useEffect(() => {
    refreshReviewerWorkload();
  }, [refreshReviewerWorkload]);

  const refreshGovernanceSLA = useCallback(async () => {
    setStatus('loading');
    setError(null);
    try {
      setSlaReport(await loadGovernanceSLA());
      setGovernanceHistory(await loadGovernanceHistory());
      setStatus('ready');
    } catch (auditError) {
      setStatus('error');
      setError(createPanelError(auditError, 'Refresh Governance SLA', refreshGovernanceSLA));
    }
  }, []);

  const handleAudit = useCallback(async () => {
    setStatus('loading');
    setError(null);
    try {
      const body = await recordAuditDecision();
      setAuditRecord(body.audit_record);
      setStatus('ready');
      onActionComplete();
    } catch (auditError) {
      setStatus('error');
      setError(createPanelError(auditError, 'Record Audit Decision', handleAudit));
    }
  }, [onActionComplete]);

  const handleApprovalAssignment = useCallback(async () => {
    setStatus('loading');
    setError(null);
    try {
      const body = await assignApproval();
      setAssignmentRecord(body.audit_record);
      setWorkloadReport(await loadReviewerWorkload());
      setSlaReport(await loadGovernanceSLA());
      setGovernanceHistory(await loadGovernanceHistory());
      setStatus('ready');
      onActionComplete();
    } catch (auditError) {
      setStatus('error');
      setError(createPanelError(auditError, 'Assign Approval', handleApprovalAssignment));
    }
  }, [onActionComplete]);

  const handleNotificationRouting = useCallback(async () => {
    setStatus('loading');
    setError(null);
    try {
      const body = await routeGovernanceNotification();
      setNotificationRecord(body.audit_record);
      setWorkloadReport(await loadReviewerWorkload());
      setSlaReport(await loadGovernanceSLA());
      setGovernanceHistory(await loadGovernanceHistory());
      setStatus('ready');
      onActionComplete();
    } catch (auditError) {
      setStatus('error');
      setError(createPanelError(auditError, 'Route Notification', handleNotificationRouting));
    }
  }, [onActionComplete]);

  const handleReviewerEscalation = useCallback(async () => {
    setStatus('loading');
    setError(null);
    try {
      const body = await escalateReviewerWorkload();
      setEscalationRecord(body.audit_record);
      setWorkloadReport(await loadReviewerWorkload());
      setSlaReport(await loadGovernanceSLA());
      setGovernanceHistory(await loadGovernanceHistory());
      setStatus('ready');
      onActionComplete();
    } catch (auditError) {
      setStatus('error');
      setError(createPanelError(auditError, 'Escalate Reviewer Workload', handleReviewerEscalation));
    }
  }, [onActionComplete]);

  const handleReviewerDecision = useCallback(async () => {
    setStatus('loading');
    setError(null);
    try {
      const latestAssignmentId = governanceHistory?.assignments?.[0]?.assignment_id || null;
      const body = await recordReviewerDecision(latestAssignmentId);
      setReviewerDecisionRecord(body.audit_record);
      setWorkloadReport(await loadReviewerWorkload());
      setSlaReport(await loadGovernanceSLA());
      setGovernanceHistory(await loadGovernanceHistory());
      setStatus('ready');
      onActionComplete();
    } catch (auditError) {
      setStatus('error');
      setError(createPanelError(auditError, 'Record Reviewer Decision', handleReviewerDecision));
    }
  }, [governanceHistory, onActionComplete]);

  const handleDecisionEvidenceExport = useCallback(async () => {
    setStatus('loading');
    setError(null);
    try {
      const body = await exportGovernanceDecisionEvidence();
      setDecisionEvidenceExport(body.export_package);
      setStatus('ready');
      onActionComplete();
    } catch (auditError) {
      setStatus('error');
      setError(createPanelError(
        auditError,
        'Export Reviewer Decision Evidence',
        handleDecisionEvidenceExport,
      ));
    }
  }, [onActionComplete]);

  return (
    <section className="panel mission-panel">
      <div>
        <h2>Governance Audit</h2>
        <p>Record a governed approval decision through the backend audit API.</p>
      </div>
      <button onClick={handleAudit} disabled={status === 'loading'}>
        {status === 'loading' ? 'Recording...' : 'Record Audit Decision'}
      </button>
      <button onClick={handleApprovalAssignment} disabled={status === 'loading'}>
        {status === 'loading' ? 'Assigning...' : 'Assign Approval'}
      </button>
      <button onClick={handleNotificationRouting} disabled={status === 'loading'}>
        {status === 'loading' ? 'Routing...' : 'Route Notification'}
      </button>
      <button onClick={handleReviewerDecision} disabled={status === 'loading'}>
        {status === 'loading' ? 'Recording...' : 'Record Reviewer Decision'}
      </button>
      <button onClick={handleDecisionEvidenceExport} disabled={status === 'loading' || !governanceHistory}>
        {status === 'loading' ? 'Exporting...' : 'Export Reviewer Decision Evidence'}
      </button>
      <button onClick={refreshReviewerWorkload} disabled={status === 'loading'}>
        {status === 'loading' ? 'Refreshing...' : 'Refresh Reviewer Workload'}
      </button>
      <button onClick={refreshGovernanceSLA} disabled={status === 'loading'}>
        {status === 'loading' ? 'Refreshing...' : 'Refresh Governance SLA'}
      </button>
      <button onClick={handleReviewerEscalation} disabled={status === 'loading'}>
        {status === 'loading' ? 'Escalating...' : 'Escalate Reviewer Workload'}
      </button>
      <ErrorBanner error={error} />
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
      {assignmentRecord && (
        <div className="mission-result">
          <h3>Approval Assigned</h3>
          <p>
            <strong>{assignmentRecord.evidence.approval_role}</strong> assigned to{' '}
            <strong>{assignmentRecord.evidence.assignee_id}</strong>.
          </p>
          <p>
            Audit <strong>{assignmentRecord.audit_id}</strong> recorded in{' '}
            <strong>{assignmentRecord.data_platform}</strong>.
          </p>
        </div>
      )}
      {notificationRecord && (
        <div className="mission-result">
          <h3>Notification Routed</h3>
          <p>
            <strong>{notificationRecord.evidence.subject}</strong> routed to{' '}
            <strong>{notificationRecord.evidence.recipient_id}</strong> through{' '}
            <strong>{notificationRecord.evidence.channel}</strong>.
          </p>
          <p>
            Audit <strong>{notificationRecord.audit_id}</strong> recorded in{' '}
            <strong>{notificationRecord.data_platform}</strong>.
          </p>
        </div>
      )}
      {reviewerDecisionRecord && (
        <div className="mission-result">
          <h3>Reviewer Decision Recorded</h3>
          <p>
            <strong>{reviewerDecisionRecord.evidence.reviewer_id}</strong> recorded{' '}
            <strong>{reviewerDecisionRecord.decision}</strong> for{' '}
            <strong>{reviewerDecisionRecord.target_type}</strong>.
          </p>
          <p>
            Audit <strong>{reviewerDecisionRecord.audit_id}</strong> recorded in{' '}
            <strong>{reviewerDecisionRecord.data_platform}</strong>.
          </p>
        </div>
      )}
      {decisionEvidenceExport && (
        <div className="mission-result">
          <h3>Reviewer Decision Evidence Export Ready</h3>
          <p>
            <strong>{decisionEvidenceExport.export_id}</strong> is{' '}
            <strong>{decisionEvidenceExport.status}</strong> with{' '}
            <strong>{decisionEvidenceExport.package_manifest.decision_count}</strong> decisions.
          </p>
          <p>
            Review required before external delivery:{' '}
            <strong>
              {String(decisionEvidenceExport.package_manifest.requires_governance_review_before_external_delivery)}
            </strong>
          </p>
        </div>
      )}
      {workloadReport && (
        <>
          <div className="mission-result">
            <h3>Reviewer Workload</h3>
            <p>
              <strong>{workloadReport.status}</strong> /{' '}
              <strong>{workloadReport.reviewer_count}</strong> reviewers in{' '}
              <strong>{workloadReport.data_platform}</strong>.
            </p>
            <p>
              Overloaded:{' '}
              <strong>
                {workloadReport.overloaded_reviewers.length
                  ? workloadReport.overloaded_reviewers.join(', ')
                  : 'none'}
              </strong>
            </p>
          </div>
          <div className="mission-history">
            {workloadReport.items.map((item) => (
              <article key={item.reviewer_id}>
                <strong>{item.reviewer_id}</strong>
                <span>{item.status}</span>
                <p>
                  Assigned {item.assigned_count}, routed {item.routed_notifications},
                  escalated {item.escalation_count}
                </p>
              </article>
            ))}
          </div>
        </>
      )}
      {escalationRecord && (
        <div className="mission-result">
          <h3>Reviewer Workload Escalated</h3>
          <p>
            <strong>{escalationRecord.evidence.reviewer_id}</strong> escalated to{' '}
            <strong>{escalationRecord.evidence.escalation_level}</strong>.
          </p>
          <p>
            Audit <strong>{escalationRecord.audit_id}</strong> recorded in{' '}
            <strong>{escalationRecord.data_platform}</strong>.
          </p>
        </div>
      )}
      {governanceHistory && (
        <>
          <div className="mission-result">
            <h3>Reviewer Decision Outcomes</h3>
            <p>
              <strong>{governanceHistory.decision_count}</strong> decisions /{' '}
              <strong>{governanceHistory.assignment_count}</strong> assignments /{' '}
              <strong>{governanceHistory.escalation_count}</strong> escalations in{' '}
              <strong>{governanceHistory.data_platform}</strong>.
            </p>
          </div>
          <div className="filter-grid" aria-label="Governance reviewer decision filters">
            <label>
              Reviewer
              <select
                value={decisionReviewerFilter}
                onChange={(event) => {
                  setDecisionReviewerFilter(event.target.value);
                }}
                aria-label="Filter reviewer decisions by reviewer"
              >
                {decisionReviewerOptions.map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            </label>
            <label>
              Decision
              <select
                value={decisionOutcomeFilter}
                onChange={(event) => {
                  setDecisionOutcomeFilter(event.target.value);
                }}
                aria-label="Filter reviewer decisions by outcome"
              >
                {decisionOutcomeOptions.map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            </label>
            <div>
              <strong>{filteredReviewerDecisions.length}</strong>
              <span>Filtered Decisions</span>
            </div>
          </div>
          <div className="mission-history compact-history">
            {filteredReviewerDecisions.length ? (
              filteredReviewerDecisions.slice(0, 6).map((decision) => (
                <article key={decision.decision_id}>
                  <strong>{decision.decision}</strong>
                  <span>{decision.reviewer_id}</span>
                  <p>
                    {decision.target_type}:{decision.target_id} / {decision.reason}
                  </p>
                </article>
              ))
            ) : (
              <p>No reviewer decisions match the selected filters.</p>
            )}
          </div>
        </>
      )}
      {slaReport && (
        <>
          <div className="mission-result">
            <h3>Governance SLA</h3>
            <p>
              <strong>{slaReport.status}</strong> / SLA{' '}
              <strong>{slaReport.sla_minutes}</strong> minutes / escalation after{' '}
              <strong>{slaReport.escalation_after_minutes}</strong> minutes.
            </p>
            <p>
              Due soon: <strong>{slaReport.due_soon_count}</strong> / overdue:{' '}
              <strong>{slaReport.overdue_count}</strong> / escalation required:{' '}
              <strong>{slaReport.escalation_required_count}</strong>.
            </p>
          </div>
          <div className="mission-history">
            {slaReport.items.map((item, index) => (
              <article key={`${item.target_type}-${item.target_id}-${item.reviewer_id}-${item.status}-${index}`}>
                <strong>{item.reviewer_id}</strong>
                <span>{item.status}</span>
                <p>
                  {item.target_type}:{item.target_id} age {item.age_minutes} minutes,
                  escalation required: {String(item.escalation_required)}
                </p>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function CommandCenterNavigation({ activeSection, onNavigate }) {
  return (
    <nav className="sidebar-nav" aria-label="Command Center sections">
      {commandCenterNav.map((item) => (
        <a
          aria-current={activeSection === item.href.slice(1) ? 'page' : undefined}
          data-active={activeSection === item.href.slice(1) ? 'true' : undefined}
          key={item.href}
          href={item.href}
          onClick={() => onNavigate(item.href.slice(1))}
        >
          {item.label}
        </a>
      ))}
    </nav>
  );
}

function App() {
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [activeSection, setActiveSection] = useState(() => {
    const savedSection = readCommandCenterPreference('activeSection', 'status');
    const sectionIds = commandCenterNav.map((item) => item.href.slice(1));
    return sectionIds.includes(savedSection) ? savedSection : 'status';
  });
  const persistActiveSection = useCallback((sectionId) => {
    setActiveSection(sectionId);
    writeCommandCenterPreference('activeSection', sectionId);
  }, []);
  const refreshCommandCenterSummary = useCallback(() => {
    setRefreshVersion((current) => current + 1);
  }, []);

  useEffect(() => {
    const sectionIds = commandCenterNav.map((item) => item.href.slice(1));
    let restoringSavedSection = true;
    const updateActiveSection = () => {
      const hashSection = window.location.hash.replace('#', '');
      if (sectionIds.includes(hashSection)) {
        restoringSavedSection = false;
        persistActiveSection(hashSection);
        return;
      }
      const savedSection = readCommandCenterPreference('activeSection', 'status');
      if (restoringSavedSection && sectionIds.includes(savedSection) && savedSection !== 'status') {
        window.history.replaceState(null, '', `#${savedSection}`);
        document.getElementById(savedSection)?.scrollIntoView({ block: 'start' });
        persistActiveSection(savedSection);
        restoringSavedSection = false;
        return;
      }
      restoringSavedSection = false;
      const nextActiveSection = sectionIds.reduce((current, sectionId) => {
        const section = document.getElementById(sectionId);
        if (!section) {
          return current;
        }
        const top = section.getBoundingClientRect().top;
        return top <= 140 ? sectionId : current;
      }, sectionIds[0]);
      persistActiveSection(nextActiveSection);
    };
    window.requestAnimationFrame(updateActiveSection);
    window.addEventListener('hashchange', updateActiveSection);
    window.addEventListener('scroll', updateActiveSection, { passive: true });
    return () => {
      window.removeEventListener('hashchange', updateActiveSection);
      window.removeEventListener('scroll', updateActiveSection);
    };
  }, [persistActiveSection]);

  return (
    <main className="shell">
      <a className="skip-link" href="#workspace">
        Skip to Command Center workspace
      </a>
      <aside className="sidebar">
        <div className="brand-block">
          <strong>Mariam</strong>
          <span>Command Center</span>
        </div>
        <CommandCenterNavigation
          activeSection={activeSection}
          onNavigate={persistActiveSection}
        />
      </aside>
      <section className="workspace" id="workspace" tabIndex="-1">
        <header className="topbar">
          <div>
            <h1>Mariam AI Enterprise OS</h1>
            <p>Documentation-driven rebuild foundation</p>
          </div>
          <a href="https://github.com/generatorhost/Mariam-Architecture-Library">Architecture Library</a>
        </header>
        <section className="grid" id="status" tabIndex="-1">
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
        <section id="runtime-status" className="workspace-section" tabIndex="-1">
          <SystemStatusPanel refreshVersion={refreshVersion} />
          <AuthSessionPanel refreshVersion={refreshVersion} />
          <SystemReadinessPanel refreshVersion={refreshVersion} />
        </section>
        <section id="data-platform" className="workspace-section" tabIndex="-1">
          <DataPlatformReadinessPanel refreshVersion={refreshVersion} />
          <MigrationRunnerPanel refreshVersion={refreshVersion} />
          <SeedDataPanel refreshVersion={refreshVersion} />
          <BackupReadinessPanel refreshVersion={refreshVersion} />
          <PluginSchemaIsolationPanel refreshVersion={refreshVersion} />
          <DockerPersistencePanel refreshVersion={refreshVersion} />
          <LiveDbSmokePanel refreshVersion={refreshVersion} />
          <DockerContainerExecutionPanel refreshVersion={refreshVersion} />
          <LiveDatabaseWriteSmokePanel refreshVersion={refreshVersion} />
          <LiveRepositoryWriteSmokePanel refreshVersion={refreshVersion} />
          <AuditEventArchivePanel refreshVersion={refreshVersion} />
          <MetricsStorePanel refreshVersion={refreshVersion} />
        </section>
        <section id="verification" className="workspace-section" tabIndex="-1">
          <FrontendRegressionSnapshotPanel refreshVersion={refreshVersion} />
          <FrontendVisualContractPanel refreshVersion={refreshVersion} />
          <FrontendBrowserScreenshotPlanPanel refreshVersion={refreshVersion} />
          <VerificationReportPanel refreshVersion={refreshVersion} />
          <VerificationAutomationPanel refreshVersion={refreshVersion} />
          <RuntimeDiagnosticsPanel refreshVersion={refreshVersion} />
          <UsageGuidePanel refreshVersion={refreshVersion} />
          <CompletionReportPanel refreshVersion={refreshVersion} />
        </section>
        <section id="roadmap" className="workspace-section" tabIndex="-1">
          <ImplementationRoadmapPanel refreshVersion={refreshVersion} />
        </section>
        <section id="missions" className="workspace-section" tabIndex="-1">
          <MissionPanel onActionComplete={refreshCommandCenterSummary} />
          <MissionHistoryPanel
            refreshVersion={refreshVersion}
            onActionComplete={refreshCommandCenterSummary}
          />
        </section>
        <AIResourcePanel onActionComplete={refreshCommandCenterSummary} />
        <AIRouteHistoryPanel refreshVersion={refreshVersion} />
        <section id="plugins" className="workspace-section" tabIndex="-1">
          <PluginWorkspacePanel onActionComplete={refreshCommandCenterSummary} />
          <ResponsiveStatePanel />
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
        </section>
        <section id="governance" className="workspace-section" tabIndex="-1">
          <AuditPanel onActionComplete={refreshCommandCenterSummary} />
        </section>
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
