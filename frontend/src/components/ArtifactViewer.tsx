import { useEffect, useState } from "react";
import type { ArtifactType } from "@lib/types";
import { fetchArtifact } from "@lib/api";

const formatJson = (payload: unknown) => JSON.stringify(payload, null, 2);

export const ArtifactViewer = ({ projectId, runId, artifactType }: { projectId: string; runId: string; artifactType: ArtifactType }) => {
  const [content, setContent] = useState<string>("Loading…");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let mounted = true;
    fetchArtifact(projectId, runId, artifactType)
      .then((payload) => { if (mounted) setContent(formatJson(payload)); })
      .catch((err) => { if (mounted) setError(err instanceof Error ? err.message : String(err)); });
    return () => { mounted = false; };
  }, [projectId, runId, artifactType]);
  if (error) return <pre className="mt-4 overflow-auto rounded-lg border border-rose-200 bg-rose-50 p-4 text-xs text-rose-700 dark:border-rose-500/40 dark:bg-rose-500/10 dark:text-rose-200">{error}</pre>;
  return <pre className="mt-4 max-h-96 overflow-auto rounded-lg border border-slate-200 bg-slate-100 p-4 text-xs text-slate-700 dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-200">{content}</pre>;
};
