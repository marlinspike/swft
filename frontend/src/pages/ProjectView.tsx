import { useParams } from "react-router-dom";
import { fetchRuns } from "@lib/api";
import { useApi } from "@hooks/useApi";
import { RunTable } from "@components/RunTable";
import { LoadingState } from "@components/LoadingState";
import { ErrorState } from "@components/ErrorState";
import { Breadcrumbs } from "@components/Breadcrumbs";

export const ProjectPage = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { data, loading, error } = useApi(() => fetchRuns(projectId ?? ""), [projectId]);
  if (!projectId) return <ErrorState message="Project not specified" />;
  if (loading) return <LoadingState message={`Loading runs for ${projectId}`} />;
  if (error || !data) return <ErrorState message={error ?? "Unable to load runs"} />;
  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: "Projects", to: "/" }, { label: projectId }]} />
      <RunTable projectId={projectId} runs={data} />
    </div>
  );
};
