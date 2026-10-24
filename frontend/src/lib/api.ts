import {
  User,
  Workspace,
  Repository,
  WorkflowRun,
  Failure,
  FailureDetail,
  Analysis,
  FixProposal,
  VerificationRun,
  DashboardSummary,
  AnalyticsTrend,
} from '../types';

const API_BASE = '/api/v1';

// Token storage key
const TOKEN_KEY = 'deployguard_token';

export const getStoredToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

export const setStoredToken = (token: string) => {
  localStorage.setItem(TOKEN_KEY, token);
};

export const clearStoredToken = () => {
  localStorage.removeItem(TOKEN_KEY);
};

// Generic authenticated fetch wrapper
async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = 'API request failed';
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail || errorJson.error || errorDetail;
    } catch {
      errorDetail = response.statusText || errorDetail;
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

// API methods
export const api = {
  // Auth
  register: async (display_name: string, email: string, password: string) => {
    const data = await apiFetch<{ access_token: string; user: User }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ display_name, email, password }),
    });
    setStoredToken(data.access_token);
    return data;
  },
  login: async (email: string, password: string) => {
    const data = await apiFetch<{ access_token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setStoredToken(data.access_token);
    return data;
  },
  getMe: () => apiFetch<User>('/auth/me'),
  logout: () => {
    clearStoredToken();
    return Promise.resolve();
  },

  // Health
  getHealth: () => apiFetch<{ status: string; app: string; mode?: string }>('/health'),
  getReady: () => apiFetch<{ status: string; database: string; ai_provider: string }>('/ready'),

  // Workspaces
  getWorkspaces: () => apiFetch<Workspace[]>('/workspaces'),

  // Dashboard
  getDashboardSummary: (workspaceId?: string) =>
    apiFetch<DashboardSummary>(`/dashboard/summary${workspaceId ? `?workspace_id=${workspaceId}` : ''}`),
  getAnalyticsTrends: (workspaceId?: string) =>
    apiFetch<AnalyticsTrend>(`/dashboard/trends${workspaceId ? `?workspace_id=${workspaceId}` : ''}`),

  // Repositories
  getRepositories: (workspaceId?: string) =>
    apiFetch<Repository[]>(`/repositories${workspaceId ? `?workspace_id=${workspaceId}` : ''}`),
  connectRepository: (workspaceId: string, fullName: string, defaultBranch = 'main') =>
    apiFetch<Repository>('/repositories', {
      method: 'POST',
      body: JSON.stringify({ workspace_id: workspaceId, full_name: fullName, default_branch: defaultBranch }),
    }),
  syncRepository: (repositoryId: string) =>
    apiFetch<{ status: string; runs_imported: number }>(`/repositories/${repositoryId}/sync`, {
      method: 'POST',
    }),
  deleteRepository: (repositoryId: string) =>
    apiFetch<{ message: string }>(`/repositories/${repositoryId}`, {
      method: 'DELETE',
    }),

  // Workflows
  getWorkflowRuns: (repositoryId?: string) =>
    apiFetch<WorkflowRun[]>(`/workflows${repositoryId ? `?repository_id=${repositoryId}` : ''}`),
  getWorkflowLogs: (workflowRunId: string) =>
    apiFetch<{ sanitized_excerpt: string; content_hash: string }>(`/workflows/${workflowRunId}/logs`),

  // Failures
  getFailures: (params?: { repository_id?: string; category?: string; status?: string; search?: string }) => {
    const query = new URLSearchParams();
    if (params?.repository_id) query.set('repository_id', params.repository_id);
    if (params?.category) query.set('category', params.category);
    if (params?.status) query.set('status', params.status);
    if (params?.search) query.set('search', params.search);
    return apiFetch<Failure[]>(`/failures?${query.toString()}`);
  },
  getFailureDetail: (failureId: string) => apiFetch<FailureDetail>(`/failures/${failureId}`),
  analyzeFailure: (failureId: string) =>
    apiFetch<Analysis>(`/failures/${failureId}/analyze`, {
      method: 'POST',
    }),
  getFailureAnalyses: (failureId: string) => apiFetch<Analysis[]>(`/failures/${failureId}/analyses`),

  // Fix proposals
  getProposals: () => apiFetch<FixProposal[]>('/proposals'),
  getProposal: (proposalId: string) => apiFetch<FixProposal>(`/proposals/${proposalId}`),
  createProposal: (analysisId: string, patchContent: string, explanation: string, affectedFiles: string[]) =>
    apiFetch<FixProposal>(`/analyses/${analysisId}/proposals`, {
      method: 'POST',
      body: JSON.stringify({ analysis_id: analysisId, patch_content: patchContent, explanation, affected_files: affectedFiles }),
    }),
  approveProposal: (proposalId: string, approved: boolean, reviewNotes?: string) =>
    apiFetch<FixProposal>(`/proposals/${proposalId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approved, review_notes: reviewNotes }),
    }),
  verifyProposal: (proposalId: string, testCommand?: string) =>
    apiFetch<VerificationRun>(`/proposals/${proposalId}/verify`, {
      method: 'POST',
      body: JSON.stringify({ allow_sandbox_execution: true, test_command: testCommand }),
    }),
};
