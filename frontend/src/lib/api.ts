import type { ProjectSummary, RunSummary, RunDetail, ArtifactType } from "@lib/types";

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
