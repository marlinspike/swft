import type { RunDetail } from "@lib/types";

const formatDate = (value: string | null) => (value ? new Date(value).toLocaleString() : "—");
const truncateCommit = (commit: string | undefined): string => (commit && commit.length > 7 ? commit.slice(0, 7) : commit ?? "—");

export const RunDetailCard = ({ detail }: { detail: RunDetail }) => {
  const metadata = detail.metadata ?? {};
  const repo = typeof metadata.repository === "string" ? metadata.repository : "—";
  const workflow = typeof metadata.workflow === "string" ? metadata.workflow : "—";
  const ref = typeof metadata.ref === "string" ? metadata.ref : "—";
  const branch = ref.startsWith("refs/heads/") ? ref.replace("refs/heads/", "") : ref;
  const runInfo = typeof metadata.run === "object" && metadata.run !== null ? (metadata.run as Record<string, unknown>) : null;
  const runUrl = runInfo && typeof runInfo.url === "string" ? runInfo.url : undefined;
  const commitSha = typeof metadata.commitSha === "string" ? metadata.commitSha : undefined;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition dark:border-slate-800 dark:bg-slate-900/60">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Run timeline</h3>
        <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">Run {detail.summary.run_id}</p>
        <dl className="mt-4 space-y-3 text-sm text-slate-600 dark:text-slate-300">
          <div className="flex items-center justify-between">
            <dt>Created</dt>
            <dd>{formatDate(detail.summary.created_at)}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt>Cosign verification</dt>
            <dd className={detail.summary.cosign_status === "passed" ? "text-emerald-400" : "text-rose-400"}>{detail.summary.cosign_status ?? "unknown"}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt>Trivy findings</dt>
            <dd>{detail.summary.trivy_findings_total ?? 0} total / {detail.summary.trivy_findings_failset ?? 0} fail-set</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt>Deployment URL</dt>
            <dd>
              {detail.summary.deployment_url ? (
                <a href={detail.summary.deployment_url} className="text-blue-600 underline dark:text-blue-300" target="_blank" rel="noreferrer">Open Instance</a>
              ) : (
                <span className="text-slate-500 dark:text-slate-400">Not deployed</span>
              )}
            </dd>
          </div>
        </dl>
      </div>
      <div className="space-y-4">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition dark:border-slate-800 dark:bg-slate-900/60">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">GitHub context</h3>
          <dl className="mt-4 space-y-3 text-sm text-slate-600 dark:text-slate-300">
            <div className="flex items-center justify-between">
              <dt>Repository</dt>
              <dd className="text-slate-900 dark:text-slate-100">{repo}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt>Workflow</dt>
              <dd className="text-slate-600 dark:text-slate-300">{workflow}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt>Branch</dt>
              <dd className="text-slate-600 dark:text-slate-300">{branch}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt>Commit</dt>
              <dd className="text-slate-600 dark:text-slate-300">{truncateCommit(commitSha)}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt>Run link</dt>
              <dd>
                {runUrl ? (
                  <a href={runUrl} className="text-blue-600 underline dark:text-blue-300" target="_blank" rel="noreferrer">Open in GitHub</a>
                ) : (
                  <span className="text-slate-500 dark:text-slate-400">Not provided</span>
                )}
              </dd>
            </div>
          </dl>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition dark:border-slate-800 dark:bg-slate-900/60">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Artifacts</h3>
          <ul className="mt-4 space-y-2 text-sm text-slate-600 dark:text-slate-300">
            {detail.artifacts.map((artifact) => (
              <li key={artifact.blob_name} className="flex items-center justify-between">
                <span className="font-medium text-slate-900 uppercase dark:text-slate-100">{artifact.artifact_type}</span>
                <span className="text-xs text-slate-500 dark:text-slate-400">{artifact.blob_name}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};
