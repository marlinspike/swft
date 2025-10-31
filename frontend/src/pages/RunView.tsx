import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { fetchArtifact, fetchRunDetail } from "@lib/api";
import { useApi } from "@hooks/useApi";
import { LoadingState } from "@components/LoadingState";
import { ErrorState } from "@components/ErrorState";
import { Breadcrumbs } from "@components/Breadcrumbs";
import { RunDetailCard } from "@components/RunDetailCard";
import { CollapsibleSection } from "@components/CollapsibleSection";
import { JsonModal } from "@components/JsonModal";

type SbomSummary = {
  totalComponents: number;
  uniqueTypes: number;
  uniqueLicenses: number;
  typeBreakdown: { label: string; count: number }[];
  topComponents: { name: string; version: string; type: string }[];
};

type TrivyFinding = {
  id: string;
  severity: string;
  title: string;
  packageName: string;
  installedVersion: string;
  fixedVersion: string;
  target: string;
};

type TrivySummary = {
  totalFindings: number;
  severityCounts: { severity: string; count: number }[];
  topFindings: TrivyFinding[];
};

const severityOrder = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"];
const severityColors: Record<string, string> = {
  CRITICAL: "bg-rose-500/20 text-rose-300 border border-rose-500/40",
  HIGH: "bg-orange-500/20 text-orange-200 border border-orange-500/40",
  MEDIUM: "bg-amber-500/20 text-amber-200 border border-amber-500/40",
  LOW: "bg-emerald-500/20 text-emerald-200 border border-emerald-500/40",
  UNKNOWN: "bg-slate-600/30 text-slate-200 border border-slate-600/40"
};

const buildSbomSummary = (payload: Record<string, unknown>): SbomSummary => {
  const components = Array.isArray(payload.components) ? payload.components : [];
  const typeCounts = new Map<string, number>();
  const licenseCounts = new Map<string, number>();
  const topComponents = [] as { name: string; version: string; type: string }[];
  for (const entry of components) {
    if (typeof entry !== "object" || entry === null) continue;
    const component = entry as Record<string, unknown>;
    const name = typeof component.name === "string" ? component.name : "Unknown";
    const version = typeof component.version === "string" ? component.version : "N/A";
    const type = typeof component.type === "string" ? component.type : "unknown";
    typeCounts.set(type, (typeCounts.get(type) ?? 0) + 1);
    const licenses = Array.isArray(component.licenses) ? component.licenses : [];
    for (const lic of licenses) {
      if (typeof lic !== "object" || lic === null) continue;
      const licenseInfo = lic as Record<string, unknown>;
      const license =
        typeof licenseInfo.license === "object" && licenseInfo.license !== null
          ? (licenseInfo.license as Record<string, unknown>)
          : null;
      const licenseName =
        (license?.name as string | undefined) ??
        (license?.id as string | undefined) ??
        "Unknown";
      licenseCounts.set(licenseName, (licenseCounts.get(licenseName) ?? 0) + 1);
    }
    topComponents.push({ name, version, type });
  }
  const sortedTypes = Array.from(typeCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([label, count]) => ({ label, count }));
  const sortedLicenses = Array.from(licenseCounts.entries()).sort((a, b) => b[1] - a[1]);
  return {
    totalComponents: components.length,
    uniqueTypes: typeCounts.size,
    uniqueLicenses: licenseCounts.size,
    typeBreakdown: sortedTypes.slice(0, 5),
    topComponents: topComponents.slice(0, 8),
  };
};

const buildTrivySummary = (payload: Record<string, unknown>): TrivySummary => {
  const results = Array.isArray(payload.Results) ? payload.Results : [];
  const severityCounts = new Map<string, number>();
  const findings: TrivyFinding[] = [];
  for (const entry of results) {
    if (typeof entry !== "object" || entry === null) continue;
    const result = entry as Record<string, unknown>;
    const target = typeof result.Target === "string" ? result.Target : "unknown";
    const vulns = Array.isArray(result.Vulnerabilities) ? result.Vulnerabilities : [];
    for (const vulnEntry of vulns) {
      if (typeof vulnEntry !== "object" || vulnEntry === null) continue;
      const vuln = vulnEntry as Record<string, unknown>;
      const severity = typeof vuln.Severity === "string" ? vuln.Severity.toUpperCase() : "UNKNOWN";
      severityCounts.set(severity, (severityCounts.get(severity) ?? 0) + 1);
      findings.push({
        id: typeof vuln.VulnerabilityID === "string" ? vuln.VulnerabilityID : "N/A",
        severity,
        title: typeof vuln.Title === "string" ? vuln.Title : "No title provided",
        packageName: typeof vuln.PkgName === "string" ? vuln.PkgName : "unknown",
        installedVersion: typeof vuln.InstalledVersion === "string" ? vuln.InstalledVersion : "unknown",
        fixedVersion: typeof vuln.FixedVersion === "string" && vuln.FixedVersion.length > 0 ? vuln.FixedVersion : "—",
        target
      });
    }
  }
  const sortedSeverity = severityOrder
    .map((severity) => ({ severity, count: severityCounts.get(severity) ?? 0 }))
    .filter((entry) => entry.count > 0);
  const rankedFindings = findings
    .sort((a, b) => {
      const aRank = severityOrder.indexOf(a.severity);
      const bRank = severityOrder.indexOf(b.severity);
      if (aRank === bRank) return a.id.localeCompare(b.id);
      return aRank - bRank;
    })
    .slice(0, 10);
  return {
    totalFindings: findings.length,
    severityCounts: sortedSeverity,
    topFindings: rankedFindings
  };
};

const formatJson = (value: unknown): string => JSON.stringify(value, null, 2);

const SeverityBadge = ({ severity, count }: { severity: string; count?: number }) => {
  const style = severityColors[severity] ?? severityColors.UNKNOWN;
  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${style}`}>
      <span>{severity}</span>
      {typeof count === "number" && (
        <span className="text-slate-100">{count}</span>
      )}
    </span>
  );
};

const TypeBadge = ({ label, count }: { label: string; count: number }) => (
  <span className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800/60 px-3 py-1 text-xs font-medium text-slate-200">
    <span className="uppercase tracking-wide text-slate-400">{label}</span>
    <span>{count}</span>
  </span>
);

const SbomSummaryView = ({ summary }: { summary: SbomSummary }) => (
  <div className="space-y-6">
    <div className="grid gap-4 md:grid-cols-3">
      <div className="rounded-xl border border-blue-500/30 bg-blue-500/10 px-4 py-5">
        <p className="text-sm text-blue-200">Total components</p>
        <p className="mt-2 text-3xl font-semibold text-white">{summary.totalComponents}</p>
      </div>
      <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-5">
        <p className="text-sm text-emerald-200">Unique component types</p>
        <p className="mt-2 text-3xl font-semibold text-white">{summary.uniqueTypes}</p>
      </div>
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-5">
        <p className="text-sm text-amber-200">Referenced licenses</p>
        <p className="mt-2 text-3xl font-semibold text-white">{summary.uniqueLicenses}</p>
      </div>
    </div>
    <div className="space-y-3">
      <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Component types</h4>
      <div className="flex flex-wrap gap-2">
        {summary.typeBreakdown.length === 0 ? (
          <span className="text-sm text-slate-400">No component type data available.</span>
        ) : (
          summary.typeBreakdown.map((item) => <TypeBadge key={item.label} label={item.label} count={item.count} />)
        )}
      </div>
    </div>
    <div className="space-y-3">
      <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Highlighted components</h4>
      {summary.topComponents.length === 0 ? (
        <p className="text-sm text-slate-400">No component details recorded.</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-800">
          <table className="min-w-full divide-y divide-slate-800">
            <thead className="bg-slate-900/70">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">Version</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">Type</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-900 bg-slate-950/40">
              {summary.topComponents.map((component) => (
                <tr key={`${component.name}-${component.version}`} className="hover:bg-slate-900/60">
                  <td className="px-4 py-3 text-sm text-slate-100">{component.name}</td>
                  <td className="px-4 py-3 text-sm text-slate-300">{component.version}</td>
                  <td className="px-4 py-3 text-sm uppercase text-slate-400">{component.type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  </div>
);

const TrivySummaryView = ({ summary }: { summary: TrivySummary }) => (
  <div className="space-y-6">
    <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-5">
      <p className="text-sm text-rose-200">Total findings</p>
      <p className="mt-2 text-3xl font-semibold text-white">{summary.totalFindings}</p>
    </div>
    <div className="flex flex-wrap gap-2">
      {summary.severityCounts.length === 0 ? (
        <span className="text-sm text-slate-400">No vulnerabilities detected.</span>
      ) : (
        summary.severityCounts.map((item) => <SeverityBadge key={item.severity} severity={item.severity} count={item.count} />)
      )}
    </div>
    <div className="space-y-3">
      <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Top findings</h4>
      {summary.topFindings.length === 0 ? (
        <p className="text-sm text-slate-400">No vulnerabilities reported in the selected severities.</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-800">
          <table className="min-w-full divide-y divide-slate-800">
            <thead className="bg-slate-900/70">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">Severity</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">Vulnerability</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">Package</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">Fixed version</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">Target</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-900 bg-slate-950/40">
              {summary.topFindings.map((finding) => (
                <tr key={`${finding.id}-${finding.packageName}`} className="hover:bg-slate-900/60">
                  <td className="px-4 py-3 text-sm font-semibold uppercase text-slate-100">
                    <SeverityBadge severity={finding.severity} />
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-100">
                    <p className="font-medium">{finding.id}</p>
                    <p className="text-xs text-slate-400">{finding.title}</p>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-300">
                    <p className="font-medium text-slate-100">{finding.packageName}</p>
                    <p className="text-xs text-slate-500">Installed: {finding.installedVersion}</p>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-300">{finding.fixedVersion}</td>
                  <td className="px-4 py-3 text-sm text-slate-400">{finding.target}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  </div>
);

export const RunPage = () => {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>();
  const { data, loading, error } = useApi(() => fetchRunDetail(projectId ?? "", runId ?? ""), [projectId, runId]);
  const [sbomSummary, setSbomSummary] = useState<SbomSummary | null>(null);
  const [sbomRaw, setSbomRaw] = useState<string | null>(null);
  const [trivySummary, setTrivySummary] = useState<TrivySummary | null>(null);
  const [trivyRaw, setTrivyRaw] = useState<string | null>(null);
  const [artifactError, setArtifactError] = useState<string | null>(null);
  const [loadingArtifacts, setLoadingArtifacts] = useState<boolean>(false);
  const [rawModal, setRawModal] = useState<{ title: string; content: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    const loadArtifacts = async () => {
      if (!data || !projectId || !runId) return;
      setLoadingArtifacts(true);
      setArtifactError(null);
      try {
        const requests: Promise<void>[] = [];
        const hasSbom = data.artifacts.some((artifact) => artifact.artifact_type === "sbom");
        if (hasSbom) {
          requests.push(
            fetchArtifact(projectId, runId, "sbom").then((payload) => {
              if (cancelled) return;
              setSbomSummary(buildSbomSummary(payload as Record<string, unknown>));
              setSbomRaw(formatJson(payload));
            })
          );
        } else {
          setSbomSummary(null);
          setSbomRaw(null);
        }
        const hasTrivy = data.artifacts.some((artifact) => artifact.artifact_type === "trivy");
        if (hasTrivy) {
          requests.push(
            fetchArtifact(projectId, runId, "trivy").then((payload) => {
              if (cancelled) return;
              setTrivySummary(buildTrivySummary(payload as Record<string, unknown>));
              setTrivyRaw(formatJson(payload));
            })
          );
        } else {
          setTrivySummary(null);
          setTrivyRaw(null);
        }
        await Promise.all(requests);
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Failed to load artifacts.";
          setArtifactError(message);
        }
      } finally {
        if (!cancelled) setLoadingArtifacts(false);
      }
    };
    void loadArtifacts();
    return () => {
      cancelled = true;
    };
  }, [data, projectId, runId]);

  const runRaw = useMemo(() => (data ? formatJson(data.metadata) : null), [data]);

  if (!projectId || !runId) return <ErrorState message="Run reference incomplete" />;
  if (loading) return <LoadingState message={`Loading run ${runId}`} />;
  if (error || !data) return <ErrorState message={error ?? "Unable to load run detail"} />;

  const renderArtifactAction = (label: string, content: string | null) =>
    content
      ? (
        <button
          type="button"
          onClick={() => setRawModal({ title: label, content })}
          className="rounded-lg border border-blue-500/40 px-3 py-1 text-sm font-medium text-blue-200 transition hover:border-blue-400 hover:text-blue-100"
        >
          View raw JSON
        </button>
      )
      : null;

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: "Projects", to: "/" }, { label: projectId, to: `/projects/${projectId}` }, { label: `Run ${runId}` }]} />
      <CollapsibleSection
        title="Run overview"
        description="Execution details from the SWFT workflow and deployment output."
        actions={runRaw ? renderArtifactAction("Run metadata (run.json)", runRaw) : null}
        defaultOpen
      >
        <RunDetailCard detail={data} />
      </CollapsibleSection>
      <CollapsibleSection
        title="Software Bill of Materials (SBOM)"
        description="Component inventory captured from the container image."
        actions={renderArtifactAction("SBOM (sbom.cyclonedx.json)", sbomRaw)}
      >
        {loadingArtifacts ? (
          <LoadingState message="Loading SBOM summary" />
        ) : artifactError ? (
          <ErrorState message={artifactError} />
        ) : sbomSummary ? (
          <SbomSummaryView summary={sbomSummary} />
        ) : (
          <p className="text-sm text-slate-400">No SBOM artifact was uploaded for this run.</p>
        )}
      </CollapsibleSection>
      <CollapsibleSection
        title="Vulnerability scan (Trivy)"
        description="Findings reported by Trivy across the container image."
        actions={renderArtifactAction("Trivy report (trivy-report.json)", trivyRaw)}
      >
        {loadingArtifacts ? (
          <LoadingState message="Loading Trivy report" />
        ) : artifactError ? (
          <ErrorState message={artifactError} />
        ) : trivySummary ? (
          <TrivySummaryView summary={trivySummary} />
        ) : (
          <p className="text-sm text-slate-400">No Trivy report was captured for this run.</p>
        )}
      </CollapsibleSection>
      {rawModal && <JsonModal title={rawModal.title} content={rawModal.content} onClose={() => setRawModal(null)} />}
    </div>
  );
};
