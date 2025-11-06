export type ArtifactType = "sbom" | "trivy" | "run";

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
