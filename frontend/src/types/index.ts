export type FailureCategory =
  | 'dependency_installation'
  | 'compilation_syntax'
  | 'unit_test'
  | 'linting_formatting'
  | 'missing_env_var'
  | 'configuration_error'
  | 'permission_error'
  | 'network_external_service'
  | 'resource_timeout'
  | 'unknown';

export type FailureStatus =
  | 'open'
  | 'investigating'
  | 'fix_proposed'
  | 'verified'
  | 'resolved';

export interface User {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
}

export interface Repository {
  id: string;
  workspace_id: string;
  provider: string;
  external_repository_id?: string;
  full_name: string;
  default_branch: string;
  connection_status: 'connected' | 'disconnected';
  last_synced_at?: string;
  created_at: string;
  workflow_runs_count: number;
  failure_count: number;
}

export interface WorkflowRun {
  id: string;
  repository_id: string;
  external_run_id: string;
  workflow_name: string;
  branch: string;
  commit_sha: string;
  status: string;
  conclusion?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  repository_name?: string;
}

export interface Failure {
  id: string;
  workflow_run_id: string;
  failed_job_name: string;
  category: FailureCategory;
  severity: 'high' | 'medium' | 'low';
  error_signature: string;
  summary: string;
  first_seen_at: string;
  last_seen_at: string;
  occurrence_count: number;
  status: FailureStatus;
  workflow_run?: WorkflowRun;
}

export interface FailureDetail extends Failure {
  log_excerpt?: string;
  stack_trace?: string;
  analysis_status?: string;
  latest_analysis_id?: string;
  latest_fix_proposal_id?: string;
}

export interface EvidenceItem {
  source: string;
  line_number?: number;
  snippet: string;
  relevance: string;
}

export interface AlternativeHypothesis {
  hypothesis: string;
  likelihood: 'low' | 'moderate' | 'high';
  reasoning: string;
}

export interface RecommendationItem {
  step: number;
  action: string;
  command?: string;
  target_file?: string;
}

export interface Analysis {
  id: string;
  failure_id: string;
  status: 'completed' | 'inconclusive' | 'failed';
  provider: string;
  model?: string;
  root_cause: string;
  evidence_json: string;
  alternatives_json: string;
  confidence: number;
  confidence_method: string;
  recommendations_json: string;
  token_usage: number;
  estimated_cost: number;
  duration_ms: number;
  created_at: string;
  parsed_evidence?: EvidenceItem[];
  parsed_alternatives?: AlternativeHypothesis[];
  parsed_recommendations?: RecommendationItem[];
}

export interface FixProposal {
  id: string;
  analysis_id: string;
  status: 'draft' | 'approved' | 'rejected' | 'applied';
  patch_content: string;
  explanation: string;
  affected_files_json: string;
  affected_files?: string[];
  approved_by?: string;
  approved_at?: string;
  created_at: string;
}

export interface VerificationRun {
  id: string;
  fix_proposal_id: string;
  status: 'not_run' | 'running' | 'passed' | 'failed' | 'timed_out' | 'cancelled' | 'unavailable' | 'inconclusive';
  test_summary_json: string;
  exit_code?: number;
  duration_ms: number;
  baseline_result?: string;
  candidate_result?: string;
  failure_reason?: string;
  created_at: string;
  completed_at?: string;
  parsed_test_summary?: any;
}

export interface DashboardSummary {
  monitored_repositories_count: number;
  total_workflow_runs_count: number;
  failed_workflow_runs_count: number;
  failure_rate_percent: number;
  analyses_completed_count: number;
  fix_verification_pass_rate_percent: number;
  open_failures_count: number;
  verified_fixes_count: number;
  recent_failures: Array<{
    id: string;
    workflow_name: string;
    failed_job: string;
    category: string;
    severity: string;
    status: string;
    branch: string;
    commit_sha: string;
    occurred_at: string;
  }>;
  top_failure_categories: Array<{
    category: string;
    count: number;
    percentage: number;
  }>;
}

export interface AnalyticsTrend {
  daily_trends: Array<{
    date: string;
    total_runs: number;
    failed_runs: number;
    failure_rate: number;
  }>;
  category_distribution: Array<{
    category: string;
    count: number;
    percentage: number;
  }>;
  average_mttr_minutes?: number;
  verification_outcomes: Record<string, number>;
  ai_cost_and_tokens: {
    total_tokens: number;
    estimated_cost_usd: number;
  };
}
