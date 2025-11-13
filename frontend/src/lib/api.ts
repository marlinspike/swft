import type {
  AssistantConfig,
  AssistantRequest,
  AssistantResponse,
  AssistantStreamEvent,
  ProjectSummary,
  RunSummary,
  RunDetail,
  ArtifactType,
  SwftProject,
  SwftProjectPayload,
  SwftParameter,
  CatalogSyncResult,
  PolicyImportResult,
  PolicyStateResult,
  EvidenceResult,
  StorageEvidenceResponse,
  AzurePolicySet,
} from "@lib/types";

const apiUrl = (path: string) => `${import.meta.env.VITE_API_BASE_URL ?? "/api"}${path}`;
const encodeProject = (projectId: string) => encodeURIComponent(projectId);

async function handle<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const fetchProjects = async (): Promise<ProjectSummary[]> => handle<ProjectSummary[]>(await fetch(apiUrl("/projects")));
export const fetchRuns = async (projectId: string): Promise<RunSummary[]> => handle<RunSummary[]>(await fetch(apiUrl(`/projects/${projectId}/runs`)));
export const fetchRunDetail = async (projectId: string, runId: string): Promise<RunDetail> => handle<RunDetail>(await fetch(apiUrl(`/projects/${projectId}/runs/${runId}`)));
export const fetchArtifact = async (projectId: string, runId: string, artifactType: ArtifactType): Promise<unknown> => handle<unknown>(await fetch(apiUrl(`/projects/${projectId}/runs/${runId}/artifacts/${artifactType}`)));
export const fetchAssistantConfig = async (): Promise<AssistantConfig> => handle<AssistantConfig>(await fetch(apiUrl("/assistant/config")));
export const postAssistantMessage = async (payload: AssistantRequest): Promise<AssistantResponse> =>
  handle<AssistantResponse>(
    await fetch(apiUrl("/assistant/chat"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  );

export const streamAssistantMessage = async (
  payload: AssistantRequest,
  onEvent: (event: AssistantStreamEvent) => void
): Promise<void> => {
  const response = await fetch(apiUrl("/assistant/chat/stream"), {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/x-ndjson" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }
  if (!response.body) throw new Error("Streaming unsupported in this browser.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let newlineIndex = buffer.indexOf("\n");
    while (newlineIndex !== -1) {
      const line = buffer.slice(0, newlineIndex).trim();
      buffer = buffer.slice(newlineIndex + 1);
      if (line.length > 0) {
        const parsed = JSON.parse(line) as AssistantStreamEvent;
        onEvent(parsed);
      }
      newlineIndex = buffer.indexOf("\n");
    }
  }
  const remaining = decoder.decode();
  const finalBuffer = buffer + remaining;
  if (finalBuffer.trim().length > 0) {
    const parsed = JSON.parse(finalBuffer.trim()) as AssistantStreamEvent;
    onEvent(parsed);
  }
};

export const fetchSwftProject = async (projectId: string): Promise<SwftProject> =>
  handle<SwftProject>(await fetch(apiUrl(`/swft/${encodeProject(projectId)}/project`)));

export const upsertSwftProject = async (projectId: string, payload: SwftProjectPayload): Promise<SwftProject> =>
  handle<SwftProject>(
    await fetch(apiUrl(`/swft/${encodeProject(projectId)}/project`), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  );

export const fetchSwftParameters = async (projectId: string, controlId: string): Promise<SwftParameter[]> =>
  handle<SwftParameter[]>(await fetch(apiUrl(`/swft/${encodeProject(projectId)}/controls/${encodeURIComponent(controlId)}/parameters`)));

export const setSwftParameter = async (projectId: string, controlId: string, paramId: string, value: string): Promise<void> => {
  await handle(
    await fetch(
      apiUrl(`/swft/${encodeProject(projectId)}/controls/${encodeURIComponent(controlId)}/parameters/${encodeURIComponent(paramId)}`),
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value }),
      }
    )
  );
};

export interface CatalogSyncPayload {
  catalogFile: File;
  baselineFile: File;
  baselineName: string;
  catalogName?: string;
}

export const syncSwftCatalog = async (payload: CatalogSyncPayload): Promise<CatalogSyncResult> => {
  const form = new FormData();
  form.append("catalog", payload.catalogFile);
  form.append("baseline", payload.baselineFile);
  form.append("baseline_name", payload.baselineName);
  form.append("catalog_name", payload.catalogName ?? "sp800-53-r5.2.0");
  return handle<CatalogSyncResult>(
    await fetch(apiUrl("/swft/catalog/sync"), {
      method: "POST",
      body: form,
    })
  );
};

export const importSwftPolicy = async (file: File, name: string, scope: string): Promise<PolicyImportResult> => {
  const form = new FormData();
  form.append("file", file);
  form.append("name", name);
  form.append("scope", scope);
  return handle<PolicyImportResult>(
    await fetch(apiUrl("/swft/policy/initiatives"), {
      method: "POST",
      body: form,
    })
  );
};

export const importSwftPolicyStates = async (file: File, initiative: string, scope: string): Promise<PolicyStateResult> => {
  const form = new FormData();
  form.append("file", file);
  form.append("initiative", initiative);
  form.append("scope", scope);
  return handle<PolicyStateResult>(
    await fetch(apiUrl("/swft/policy/states"), {
      method: "POST",
      body: form,
    })
  );
};

const uploadEvidence = async (path: string, form: FormData): Promise<EvidenceResult> =>
  handle<EvidenceResult>(
    await fetch(apiUrl(path), {
      method: "POST",
      body: form,
    })
  );

export const uploadSwftSbom = async (projectId: string, runId: string, file: File): Promise<EvidenceResult> => {
  const form = new FormData();
  form.append("file", file);
  return uploadEvidence(`/swft/${encodeProject(projectId)}/runs/${encodeURIComponent(runId)}/evidence/sbom`, form);
};

export const uploadSwftTrivy = async (projectId: string, runId: string, file: File, artifactHint?: string): Promise<EvidenceResult> => {
  const form = new FormData();
  form.append("file", file);
  if (artifactHint) form.append("artifact_hint", artifactHint);
  return uploadEvidence(`/swft/${encodeProject(projectId)}/runs/${encodeURIComponent(runId)}/evidence/trivy`, form);
};

export const uploadSwftSignature = async (
  projectId: string,
  runId: string,
  file: File,
  digest: string,
  verified: boolean
): Promise<EvidenceResult> => {
  const form = new FormData();
  form.append("file", file);
  form.append("digest", digest);
  form.append("verified", verified ? "true" : "false");
  return uploadEvidence(`/swft/${encodeProject(projectId)}/runs/${encodeURIComponent(runId)}/evidence/signature`, form);
};

export const fetchSwftServices = async (): Promise<string[]> => handle<string[]>(await fetch(apiUrl("/swft/services")));
export const fetchSwftRegions = async (): Promise<string[]> => handle<string[]>(await fetch(apiUrl("/swft/regions")));

export const ingestSwftEvidenceFromStorage = async (projectId: string, runId: string, kinds?: string[]): Promise<StorageEvidenceResponse> => {
  const body = kinds ? { kinds } : {};
  return handle<StorageEvidenceResponse>(
    await fetch(apiUrl(`/swft/${encodeProject(projectId)}/runs/${encodeURIComponent(runId)}/evidence/from-storage`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
  );
};

export const fetchAzurePolicySets = async (): Promise<AzurePolicySet[]> => handle<AzurePolicySet[]>(await fetch(apiUrl("/swft/policy/builtins")));

export const importAzurePolicySet = async (policyId: string, scope?: string): Promise<PolicyImportResult> => {
  const payload: Record<string, string> = { policy_id: policyId };
  if (scope) payload.scope = scope;
  return handle<PolicyImportResult>(
    await fetch(apiUrl("/swft/policy/builtins"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  );
};
