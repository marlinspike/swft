import type {
  AssistantConfig,
  AssistantRequest,
  AssistantResponse,
  AssistantStreamEvent,
  ProjectSummary,
  RunSummary,
  RunDetail,
  ArtifactType,
} from "@lib/types";

const apiUrl = (path: string) => `${import.meta.env.VITE_API_BASE_URL ?? "/api"}${path}`;

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
