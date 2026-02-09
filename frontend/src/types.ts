export type VerificationStatus = "verified" | "failed" | "unsupported";
export type VerificationRunState = "idle" | "running" | "verified" | "failed" | "unsupported";

export interface VerificationErrorPayload {
  message: string;
  line?: number | null;
  column?: number | null;
}

export interface VerificationPayload {
  status: VerificationStatus;
  errors: VerificationErrorPayload[];
  latency_ms: number;
  stdout: string;
  stderr: string;
}

export interface AttemptVerificationPayload {
  status: VerificationStatus;
  errors: VerificationErrorPayload[];
  latency_ms: number;
}

export interface RepairAttemptPayload {
  attempt: number;
  source: string;
  lean_code: string;
  verification: AttemptVerificationPayload;
  error_class: string;
  error_messages: string[];
  targeted_fix: string;
  diff_from_previous: string;
}

export interface ExplanationStepPayload {
  line_number: number;
  tactic: string;
  explanation: string;
}

export interface ExplanationPayload {
  summary: string;
  steps: ExplanationStepPayload[];
}

export interface AnnotatedLinePayload {
  line_number: number;
  text: string;
  has_info: boolean;
  theorem_name?: string | null;
  short_explanation?: string | null;
  concept_summary?: string | null;
  knowledge_id?: string | null;
  concept_key?: string | null;
}

export interface KnowledgeEntryPayload {
  id: string;
  concept_key: string;
  theorem_name: string;
  summary: string;
  detailed_explanation: string;
  research_context: string;
  paper_notes: string;
  related_theorems: string[];
}

export interface StageTracePayload {
  stage: string;
  latency_ms: number;
  payload: Record<string, unknown>;
}

export interface FormalizeResponse {
  request_id: string;
  original_statement: string;
  mode: string;
  ast: Record<string, unknown>;
  capability: {
    tier: number;
    tier_label: string;
    status: "supported" | "unsupported";
    supported: boolean;
    reason: string;
    signals: string[];
  };
  model_response?: {
    status: "success" | "failure" | "unsupported";
    lean_code: string;
    explanation: string;
    error_message: string;
    reason?: string;
  };
  lean_code: string;
  verification: VerificationPayload;
  attempts_used: number;
  repair_history: RepairAttemptPayload[];
  explanation: ExplanationPayload;
  annotated_lines: AnnotatedLinePayload[];
  knowledge_entries: KnowledgeEntryPayload[];
  stage_traces: StageTracePayload[];
  total_latency_ms: number;
}

export interface FormalizeRequestPayload {
  statement: string;
  mode: "ast" | "direct";
  enable_repair_loop: boolean;
}
