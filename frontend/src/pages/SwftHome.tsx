import { Link } from "react-router-dom";
import { useApi } from "@hooks/useApi";
import { fetchProjects } from "@lib/api";
import { LoadingState } from "@components/LoadingState";
import { ErrorState } from "@components/ErrorState";

export const SwftHomePage = () => {
  const { data, loading, error } = useApi(fetchProjects, []);
  if (loading) return <LoadingState message="Loading projects" />;
  if (error || !data) return <ErrorState message={error ?? "Unable to load projects"} />;
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-500 dark:text-slate-400">Project-scoped compliance workspace</p>
          <h2 className="text-2xl font-semibold text-slate-900 dark:text-white">SWFT Workspace</h2>
        </div>
        <Link
          to="/"
          className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700 shadow-sm transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-100 dark:hover:bg-slate-800"
        >
          Back to Dashboard
        </Link>
      </div>
      <p className="text-sm text-slate-600 dark:text-slate-400">
        Select a repository to open its SWFT compliance workspace. Dev teams can ingest catalog data, define boundaries, and upload evidence for a single repo,
        while Authorizing Officials can review progress and export SSP/POA&amp;M artifacts.
      </p>
      <div className="divide-y divide-slate-200 overflow-hidden rounded-lg border border-slate-200 dark:divide-slate-800 dark:border-slate-800">
        {data.map((project) => (
          <div key={project.project_id} className="flex items-center justify-between px-4 py-3">
            <div>
              <p className="font-medium text-slate-900 dark:text-white">{project.project_id}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">{project.run_count} runs tracked</p>
            </div>
            <Link
              to={`/swft/${encodeURIComponent(project.project_id)}`}
              className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-blue-500"
            >
              Open Workspace
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
};
