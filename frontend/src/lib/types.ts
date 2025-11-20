export type ArtifactType = "sbom" | "trivy" | "run" | "appdesign";

export interface ProjectSummary {
  project_id: string;
  run_count: number;
  latest_run_at: string | null;
}

export interface RunSummary {
  project_id: string;
  run_id: string;
  created_at: string | null;
  artifact_counts: Record<string, number>;
  sbom_component_total: number | null;
  cosign_status: string | null;
  trivy_findings_total: number | null;
  trivy_findings_failset: number | null;
  deployment_url: string | null;
}

export interface ArtifactDescriptor {
  project_id: string;
  run_id: string;
  artifact_type: ArtifactType;
  blob_name: string;
  container: string;
  last_modified: string | null;
  size_bytes: number | null;
}

export interface RunDetail {
  summary: RunSummary;
  artifacts: ArtifactDescriptor[];
  metadata: Record<string, unknown>;
}

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export type AssistantPersona = "security_assessor" | "compliance_officer" | "devops_engineer" | "software_developer";
export type AssistantFacet = "run_manifest" | "sbom" | "trivy" | "general" | "architecture";
export type AssistantHistoryDepth = 0 | 2 | 5 | 7 | 10 | 15 | "all";

export interface AssistantMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AssistantRequest {
  question: string;
  persona: AssistantPersona;
  facet: AssistantFacet;
  selected_model?: string;
  history?: AssistantMessage[];
  history_depth: AssistantHistoryDepth;
  conversation_id?: string;
  context?: Record<string, string>;
  project_id?: string;
  run_id?: string;
}

export interface AssistantMetadata {
  provider: string;
  model_key: string;
  model_identifier: string;
  persona: AssistantPersona;
  facet: AssistantFacet;
  history_included: number;
  max_output_tokens?: number | null;
  max_input_tokens?: number | null;
  total_context_window?: number | null;
}

export interface AssistantResponse {
  answer: string;
  conversation_id: string;
  metadata: AssistantMetadata;
}

export interface AssistantModelOption {
  key: string;
  label: string;
  response_format?: string | null;
  total_context_window?: number | null;
  max_input_tokens?: number | null;
  max_output_tokens?: number | null;
}

export interface AssistantConfig {
  provider: string;
  models: AssistantModelOption[];
  personas: AssistantPersona[];
  facets: AssistantFacet[];
  history_depths: AssistantHistoryDepth[];
  streaming_enabled: boolean;
}

export type AssistantStreamEvent =
  | {
      type: "metadata";
      conversation_id: string;
      metadata: AssistantMetadata;
    }
  | {
      type: "delta";
      delta: string;
    }
  | {
      type: "final";
      conversation_id: string;
      answer: string;
      metadata: AssistantMetadata;
    }
  | {
      type: "error";
      error: string;
    };

export interface SwftProject {
  project_id: string;
  services: string[];
  regions: string[];
  boundary_description: string | null;
}

export interface SwftProjectPayload {
  services: string[];
  regions: string[];
  boundary_description?: string | null;
}

export interface SwftParameter {
  control_id: string;
  param_id: string;
  label?: string | null;
  description?: string | null;
  allowed_values: string[];
  current_value?: string | null;
}

export interface CatalogSyncResult {
  catalog: Record<string, unknown>;
  baseline: Record<string, unknown>;
}

export interface PolicyImportResult {
  initiative: string;
  scope: string;
  policies: number;
  mappings: number;
  version: string;
}

export interface PolicyStateResult {
  processed: number;
  inserted: number;
}

export interface EvidenceResult {
  evidence_id: number;
  run_id: string;
  kind: "sbom" | "trivy" | "signature";
  metadata?: Record<string, unknown>;
}

export interface StorageEvidenceItem {
  kind: string;
  status: "stored" | "missing" | "failed";
  message?: string | null;
  evidence_id?: number | null;
  metadata?: Record<string, unknown>;
}

export interface StorageEvidenceResponse {
  project_id: string;
  run_id: string;
  results: StorageEvidenceItem[];
}

export interface AzurePolicySet {
  id: string;
  label: string;
  default_scope: string;
  description: string;
}
