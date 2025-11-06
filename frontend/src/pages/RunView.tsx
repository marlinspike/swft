import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { fetchArtifact, fetchRunDetail } from "@lib/api";
import type { AssistantFacet } from "@lib/types";
import { useApi } from "@hooks/useApi";
import { LoadingState } from "@components/LoadingState";
import { ErrorState } from "@components/ErrorState";
import { Breadcrumbs } from "@components/Breadcrumbs";
import { RunDetailCard } from "@components/RunDetailCard";
import { CollapsibleSection } from "@components/CollapsibleSection";
import { JsonModal } from "@components/JsonModal";
import { InfoPopover } from "@components/InfoPopover";
import { AssistantPanel } from "@components/assistant/AssistantPanel";
import { SparklesIcon } from "@heroicons/react/24/outline";

// Full run detail page: fetches the main run record, enriches it with SBOM/Trivy summaries,
// and renders a stack of cards with provenance and security insights.
type SbomSummary = {
  totalComponents: number;
  uniqueTypes: number;
  uniqueLicenses: number;
  typeBreakdown: { label: string; count: number }[];
  topComponents: { name: string; version: string; type: string }[];
  topLicenses: { name: string; count: number }[];
  baseImage: { name: string; version?: string; supplier?: string } | null;
  componentsWithoutLicense: number;
  topEcosystems: { name: string; count: number }[];
  generator: string | null;
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
  platform: {
    osFamily: string | null;
    osName: string | null;
    imageID: string | null;
    repoDigests: string[];
  };
  scanner: {
    version: string | null;
    dbUpdatedAt: string | null;
  };
  highestSeverity: string | null;
  fixableCount: number;
  withoutFixCount: number;
  classBreakdown: { name: string; count: number }[];
  latestPublished: string | null;
};

const severityOrder = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"];
const severityColors: Record<string, string> = {
  CRITICAL:
    "border border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/40 dark:bg-rose-500/20 dark:text-rose-200",
  HIGH:
    "border border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-500/40 dark:bg-orange-500/20 dark:text-orange-200",
  MEDIUM:
    "border border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/40 dark:bg-amber-500/20 dark:text-amber-200",
  LOW:
    "border border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/40 dark:bg-emerald-500/20 dark:text-emerald-200",
  UNKNOWN:
    "border border-slate-200 bg-slate-100 text-slate-700 dark:border-slate-600/40 dark:bg-slate-600/30 dark:text-slate-200"
};

// Quick reference copy for the info popovers so designers can tweak content in one place.
const infoHelp = {
  sbom: {
    description: "Summaries below come directly from sbom.cyclonedx.json and describe the components bundled in this container image.",
    items: [
      { label: "Generator", content: "Identifies the SBOM tool and version that produced this inventory so you know which engine to validate." },
      { label: "Base image & OS", content: "Shows the parent container and operating-system component detected in the SBOM for provenance and hardening checks." },
      { label: "Licensing alert", content: "Components missing license metadata are flagged so legal/compliance teams can review obligations before approval." },
      { label: "Package ecosystems", content: "Highlights the package registries represented in the SBOM to focus supply-chain reviews." }
    ]
  },
  trivyOverview: {
    description: "This section reflects the findings from trivy-report.json and offers context on severity, fix availability, and package classes.",
    items: [
      { label: "Highest severity", content: "The most severe vulnerability detected; if blank, no issues met the scan thresholds." },
      { label: "Fixable vs. no fix", content: "How many findings already have a patched version available versus items still waiting on a vendor fix." },
      { label: "Latest published CVE", content: "Timestamp of the newest disclosure among the detected findings to gauge how fresh the risk landscape is." }
    ]
  },
  trivyScanner: {
    description: "Tracks which Trivy binary and vulnerability database snapshot were used so the assessment can be reproduced or audited.",
    items: [
      { label: "Trivy version", content: "The CLI version invoked by the workflow (from run.json)." },
      { label: "DB updated", content: "When Trivy’s vulnerability database was last refreshed before this scan." },
      { label: "Repo digest", content: "The immutable container digest that was scanned to tie findings back to an exact image." }
    ]
  },
  trivyPolicy: {
    description: "Pulled from run.json to show how the scan was parameterised and what triggers a pipeline failure.",
    items: [
      { label: "Scan severities", content: "Only vulnerabilities at these severities were included in the report." },
      { label: "Fail-on severities", content: "Findings at these levels cause the policy to fail (subject to workflow flags)." },
      { label: "Ignore unfixed", content: "Whether vulnerabilities without a published fix are excluded from failing the run." }
    ]
  }
} as const;

// Extract the handful of SBOM stats the UI needs while tolerating partially populated documents.
const buildSbomSummary = (payload: Record<string, unknown>): SbomSummary => {
  const components = Array.isArray(payload.components) ? payload.components : [];
  const typeCounts = new Map<string, number>();
  const licenseCounts = new Map<string, number>();
  const topComponents = [] as { name: string; version: string; type: string }[];
  let baseImage: { name: string; version?: string; supplier?: string } | null = null;
  let componentsWithoutLicense = 0;
  const ecosystemCounts = new Map<string, number>();
  const metadata = typeof payload.metadata === "object" && payload.metadata !== null ? (payload.metadata as Record<string, unknown>) : null;
  const metadataComponent = metadata && typeof metadata.component === "object" && metadata.component !== null ? (metadata.component as Record<string, unknown>) : null;
  let generator: string | null = null;
  if (metadataComponent) {
    const name = typeof metadataComponent.name === "string" ? metadataComponent.name : null;
    const version = typeof metadataComponent.version === "string" ? metadataComponent.version : undefined;
    const supplier =
      typeof metadataComponent.supplier === "object" && metadataComponent.supplier !== null
        ? (
            (metadataComponent.supplier as Record<string, unknown>).name ??
            (metadataComponent.supplier as Record<string, unknown>).url ??
            undefined
          )
        : undefined;
    if (name) {
      baseImage = { name, version, supplier: typeof supplier === "string" ? supplier : undefined };
    }
  }
  const toolsField = metadata ? (metadata as Record<string, unknown>).tools : null;
  const metadataTools = Array.isArray(toolsField) ? toolsField : null;
  if (metadataTools) {
    const tool = metadataTools.find((entry) => typeof entry === "object" && entry !== null) as Record<string, unknown> | undefined;
    if (tool) {
      const toolName = typeof tool.name === "string" ? tool.name : null;
      const toolVendor = typeof tool.vendor === "string" ? tool.vendor : null;
      const toolVersion = typeof tool.version === "string" ? tool.version : null;
      const parts = [toolVendor, toolName, toolVersion ? `v${toolVersion}` : null].filter((value): value is string => !!value);
      generator = parts.length > 0 ? parts.join(" ") : toolName ?? null;
    }
  }
  for (const entry of components) {
    if (typeof entry !== "object" || entry === null) continue;
    const component = entry as Record<string, unknown>;
    const name = typeof component.name === "string" ? component.name : "Unknown";
    const version = typeof component.version === "string" ? component.version : "N/A";
    const type = typeof component.type === "string" ? component.type : "unknown";
    typeCounts.set(type, (typeCounts.get(type) ?? 0) + 1);
    const licenses = Array.isArray(component.licenses) ? component.licenses : [];
    if (licenses.length === 0) componentsWithoutLicense += 1;
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
    const purl = typeof component.purl === "string" ? component.purl : null;
    if (purl?.startsWith("pkg:")) {
      const remainder = purl.slice(4);
      const typeSegment = remainder.split("/")[0] ?? "";
      const ecosystemType = typeSegment.split("@")[0]?.split("?")[0]?.split("#")[0] ?? "";
      if (ecosystemType) {
        const label = ecosystemType.toUpperCase();
        ecosystemCounts.set(label, (ecosystemCounts.get(label) ?? 0) + 1);
      }
    }
    topComponents.push({ name, version, type });
  }
  const sortedTypes = Array.from(typeCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([label, count]) => ({ label, count }));
  const sortedLicenses = Array.from(licenseCounts.entries()).sort((a, b) => b[1] - a[1]);
  const sortedEcosystems = Array.from(ecosystemCounts.entries()).sort((a, b) => b[1] - a[1]);
  return {
    totalComponents: components.length,
    uniqueTypes: typeCounts.size,
    uniqueLicenses: licenseCounts.size,
    typeBreakdown: sortedTypes.slice(0, 5),
    topComponents: topComponents.slice(0, 8),
    topLicenses: sortedLicenses.slice(0, 5).map(([name, count]) => ({ name, count })),
    baseImage,
    componentsWithoutLicense,
    topEcosystems: sortedEcosystems.slice(0, 5).map(([name, count]) => ({ name, count })),
    generator
  };
};

// Parse the Trivy JSON into a friendly shape that mirrors what security reviewers care about.
const buildTrivySummary = (payload: Record<string, unknown>): TrivySummary => {
  const results = Array.isArray(payload.Results) ? payload.Results : [];
  const severityCounts = new Map<string, number>();
  const findings: TrivyFinding[] = [];
  const metadata = typeof payload.Metadata === "object" && payload.Metadata !== null ? (payload.Metadata as Record<string, unknown>) : null;
  const osInfo = metadata && typeof metadata.OS === "object" && metadata.OS !== null ? (metadata.OS as Record<string, unknown>) : null;
  const osFamily = osInfo && typeof osInfo.Family === "string" ? osInfo.Family : null;
  const osName = osInfo && typeof osInfo.Name === "string" ? osInfo.Name : null;
  const imageID = metadata && typeof metadata.ImageID === "string" ? metadata.ImageID : null;
  const repoDigests = metadata && Array.isArray(metadata.RepoDigests)
    ? (metadata.RepoDigests as unknown[]).filter((item): item is string => typeof item === "string")
    : [];
  const scannerVersion = metadata && typeof metadata.Version === "string" ? metadata.Version : null;
  const dbUpdatedAt = metadata && typeof metadata.UpdatedAt === "string" ? metadata.UpdatedAt : null;
  const classCounts = new Map<string, number>();
  let highestSeverity: string | null = null;
  let highestSeverityIndex = severityOrder.length;
  let fixableCount = 0;
  let withoutFixCount = 0;
  let latestPublished: string | null = null;
  for (const entry of results) {
    if (typeof entry !== "object" || entry === null) continue;
    const result = entry as Record<string, unknown>;
    const target = typeof result.Target === "string" ? result.Target : "unknown";
    const vulns = Array.isArray(result.Vulnerabilities) ? result.Vulnerabilities : [];
    const resultClass = typeof result.Class === "string" ? result.Class : typeof result.Type === "string" ? result.Type : null;
    if (resultClass) {
      const label = resultClass.replace(/_/g, "-").toUpperCase();
      classCounts.set(label, (classCounts.get(label) ?? 0) + vulns.length);
    }
    for (const vulnEntry of vulns) {
      if (typeof vulnEntry !== "object" || vulnEntry === null) continue;
      const vuln = vulnEntry as Record<string, unknown>;
      const severity = typeof vuln.Severity === "string" ? vuln.Severity.toUpperCase() : "UNKNOWN";
      severityCounts.set(severity, (severityCounts.get(severity) ?? 0) + 1);
      const severityIndex = severityOrder.indexOf(severity);
      if (severityIndex !== -1 && severityIndex < highestSeverityIndex) {
        highestSeverityIndex = severityIndex;
        highestSeverity = severity;
      }
      const fixedVersion = typeof vuln.FixedVersion === "string" ? vuln.FixedVersion : "";
      if (fixedVersion && fixedVersion !== "0" && fixedVersion !== "-" && fixedVersion !== "—" && fixedVersion.toLowerCase() !== "none") {
        fixableCount += 1;
      } else {
        withoutFixCount += 1;
      }
      const published = typeof vuln.PublishedDate === "string" ? vuln.PublishedDate : null;
      if (published) {
        if (!latestPublished) {
          latestPublished = published;
        } else if (new Date(published).getTime() > new Date(latestPublished).getTime()) {
          latestPublished = published;
        }
      }
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
    topFindings: rankedFindings,
    platform: {
      osFamily,
      osName,
      imageID,
      repoDigests
    },
    scanner: {
      version: scannerVersion,
      dbUpdatedAt
    },
    highestSeverity,
    fixableCount,
    withoutFixCount,
    classBreakdown: Array.from(classCounts.entries())
      .filter(([, count]) => count > 0)
      .sort((a, b) => b[1] - a[1])
      .map(([name, count]) => ({ name, count }))
      .slice(0, 5),
    latestPublished
  };
};

const formatJson = (value: unknown): string => JSON.stringify(value, null, 2);

const SeverityBadge = ({ severity, count }: { severity: string; count?: number }) => {
  const style = severityColors[severity] ?? severityColors.UNKNOWN;
  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${style}`}>
      <span>{severity}</span>
      {typeof count === "number" && (
        <span className="text-slate-900 dark:text-slate-100">{count}</span>
      )}
    </span>
  );
};

const TypeBadge = ({ label, count }: { label: string; count: number }) => (
  <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-200">
    <span className="uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</span>
    <span>{count}</span>
  </span>
);

const SbomSummaryView = ({ summary }: { summary: SbomSummary }) => (
  <div className="space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Component inventory, base image details, and license coverage derived from the uploaded SBOM.
      </p>
      <InfoPopover title="SBOM insights" description={infoHelp.sbom.description} items={infoHelp.sbom.items} />
    </div>
    <div className="grid gap-4 md:grid-cols-3">
      <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-5 dark:border-blue-500/30 dark:bg-blue-500/10">
        <p className="text-sm text-blue-700 dark:text-blue-200">Total components</p>
        <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-white">{summary.totalComponents}</p>
      </div>
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-5 dark:border-emerald-500/30 dark:bg-emerald-500/10">
        <p className="text-sm text-emerald-700 dark:text-emerald-200">Unique component types</p>
        <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-white">{summary.uniqueTypes}</p>
      </div>
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-5 dark:border-amber-500/30 dark:bg-amber-500/10">
        <p className="text-sm text-amber-700 dark:text-amber-200">Referenced licenses</p>
        <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-white">{summary.uniqueLicenses}</p>
      </div>
    </div>
    {summary.generator && (
      <div className="rounded-xl border border-slate-200 bg-white px-4 py-4 text-sm text-slate-600 shadow-sm dark:border-slate-800 dark:bg-slate-900/60 dark:text-slate-300">
        <span className="font-semibold text-slate-700 dark:text-slate-200">Generated by:</span> {summary.generator}
      </div>
    )}
    <div className="space-y-3">
      <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Component types</h4>
      <div className="flex flex-wrap gap-2">
        {summary.typeBreakdown.length === 0 ? (
          <span className="text-sm text-slate-500 dark:text-slate-400">No component type data available.</span>
        ) : (
          summary.typeBreakdown.map((item) => <TypeBadge key={item.label} label={item.label} count={item.count} />)
        )}
      </div>
    </div>
    <div className="space-y-3">
      <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Highlighted components</h4>
      {summary.topComponents.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">No component details recorded.</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
            <thead className="bg-slate-100 dark:bg-slate-900/70">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Version</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Type</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white dark:divide-slate-900 dark:bg-slate-950/40">
              {summary.topComponents.map((component) => (
                <tr key={`${component.name}-${component.version}`} className="hover:bg-slate-50 dark:hover:bg-slate-900/60">
                  <td className="px-4 py-3 text-sm text-slate-900 dark:text-slate-100">{component.name}</td>
                  <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">{component.version}</td>
                  <td className="px-4 py-3 text-sm uppercase text-slate-500 dark:text-slate-400">{component.type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
    <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-700 shadow-sm dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
      <h4 className="text-sm font-semibold uppercase tracking-wide">Compliance alert</h4>
      <p className="mt-2">
        {summary.componentsWithoutLicense} components report no license metadata in the SBOM. Treat these as unknown obligations until they are manually reviewed.
        {summary.totalComponents > 0 && (
          <span> ({Math.round((summary.componentsWithoutLicense / summary.totalComponents) * 100)}% of listed components)</span>
        )}
      </p>
    </div>
    <div className="grid gap-4 md:grid-cols-2">
      <div className="space-y-3">
        <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Top licenses</h4>
        {summary.topLicenses.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">No license data recorded.</p>
        ) : (
          <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
            {summary.topLicenses.map((item) => (
              <li key={item.name} className="flex items-center justify-between">
                <span className="font-medium text-slate-900 dark:text-slate-100">{item.name}</span>
                <span className="text-xs text-slate-500 dark:text-slate-400">{item.count}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="space-y-3">
        <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Package ecosystems</h4>
        {summary.topEcosystems.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">No package ecosystem data detected.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {summary.topEcosystems.map((item) => (
              <span key={item.name} className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-200">
                <span className="uppercase tracking-wide text-slate-500 dark:text-slate-400">{item.name}</span>
                <span>{item.count}</span>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  </div>
);

const TrivySummaryView = ({
  summary,
  policy
}: {
  summary: TrivySummary;
  policy?: {
    scanSeverities: string | null;
    failSeverities: string | null;
    ignoreUnfixed: boolean | null;
    scannerVersion: string | null;
    scannerDbUpdatedAt: string | null;
  } | null;
}) => {
  const hasNoFindings = summary.totalFindings === 0;
  const borderColor = hasNoFindings
    ? "border-emerald-300 dark:border-emerald-500/40"
    : "border-rose-300 dark:border-rose-500/40";
  const backgroundColor = hasNoFindings
    ? "bg-emerald-50 dark:bg-emerald-500/10"
    : "bg-rose-50 dark:bg-rose-500/10";
  const labelColor = hasNoFindings
    ? "text-emerald-700 dark:text-emerald-200"
    : "text-rose-700 dark:text-rose-200";
  const valueColor = hasNoFindings
    ? "text-emerald-900 dark:text-white"
    : "text-rose-900 dark:text-white";
  const formatDateTime = (value: string | null) => (value ? new Date(value).toLocaleString() : "—");
  const fixablePercentage = summary.totalFindings > 0 ? Math.round((summary.fixableCount / summary.totalFindings) * 100) : 0;
  const ignoreUnfixedLabel = policy
    ? policy.ignoreUnfixed === null
      ? "—"
      : policy.ignoreUnfixed
        ? "Yes"
        : "No"
    : "—";
  const scannerVersion = summary.scanner.version ?? policy?.scannerVersion ?? null;
  const scannerDbUpdatedAt = summary.scanner.dbUpdatedAt ?? policy?.scannerDbUpdatedAt ?? null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Vulnerability assessment from trivy-report.json with severity posture, fix availability, and scan policy context.
        </p>
        <InfoPopover title="Trivy scan insights" description={infoHelp.trivyOverview.description} items={infoHelp.trivyOverview.items} />
      </div>
      <div className={`rounded-xl border px-4 py-5 ${borderColor} ${backgroundColor}`}>
        <p className={`text-sm ${labelColor}`}>Total findings</p>
        <p className={`mt-2 text-3xl font-semibold ${valueColor}`}>{summary.totalFindings}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {summary.severityCounts.length === 0 ? (
          <span className="text-sm text-slate-500 dark:text-slate-400">No vulnerabilities detected.</span>
        ) : (
          summary.severityCounts.map((item) => <SeverityBadge key={item.severity} severity={item.severity} count={item.count} />)
        )}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition dark:border-slate-800 dark:bg-slate-900/60">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Severity posture</h4>
          <dl className="mt-4 space-y-3 text-sm text-slate-600 dark:text-slate-300">
            <div className="flex items-center justify-between">
              <dt>Highest severity</dt>
              <dd className="text-slate-900 dark:text-slate-100">{summary.highestSeverity ?? "None detected"}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt>Fixable findings</dt>
              <dd>{summary.fixableCount} / {summary.totalFindings} ({fixablePercentage}%)</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt>No fix available</dt>
              <dd>{summary.withoutFixCount}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt>Latest published CVE</dt>
              <dd className="text-xs text-slate-500 dark:text-slate-400">{formatDateTime(summary.latestPublished)}</dd>
            </div>
          </dl>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition dark:border-slate-800 dark:bg-slate-900/60">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Package classes</h4>
          {summary.classBreakdown.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">No vulnerable package classes detected.</p>
          ) : (
            <ul className="mt-4 space-y-2 text-sm text-slate-600 dark:text-slate-300">
              {summary.classBreakdown.map((item) => (
                <li key={item.name} className="flex items-center justify-between">
                  <span className="font-medium text-slate-900 dark:text-slate-100">{item.name}</span>
                  <span className="text-xs text-slate-500 dark:text-slate-400">{item.count}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <div className="space-y-3">
        <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Top findings</h4>
        {summary.topFindings.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">No vulnerabilities reported in the selected severities.</p>
        ) : (
          <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800">
            <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
              <thead className="bg-slate-100 dark:bg-slate-900/70">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Severity</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Vulnerability</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Package</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Fixed version</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Target</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white dark:divide-slate-900 dark:bg-slate-950/40">
                {summary.topFindings.map((finding) => (
                  <tr key={`${finding.id}-${finding.packageName}`} className="hover:bg-slate-50 dark:hover:bg-slate-900/60">
                    <td className="px-4 py-3 text-sm font-semibold uppercase text-slate-900 dark:text-slate-100">
                      <SeverityBadge severity={finding.severity} />
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-900 dark:text-slate-100">
                      <p className="font-medium">{finding.id}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{finding.title}</p>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-700 dark:text-slate-300">
                      <p className="font-medium text-slate-900 dark:text-slate-100">{finding.packageName}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-500">Installed: {finding.installedVersion}</p>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-700 dark:text-slate-300">{finding.fixedVersion}</td>
                    <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">{finding.target}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition dark:border-slate-800 dark:bg-slate-900/60">
          <div className="flex items-start justify-between gap-3">
            <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Scanner metadata</h4>
            <InfoPopover title="Scanner metadata" description={infoHelp.trivyScanner.description} items={infoHelp.trivyScanner.items} align="left" />
          </div>
          <dl className="mt-4 space-y-3 text-sm text-slate-600 dark:text-slate-300">
            <div className="flex items-center justify-between">
              <dt>Trivy version</dt>
              <dd className="text-slate-900 dark:text-slate-100">{scannerVersion ?? "—"}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt>DB updated</dt>
              <dd className="text-xs text-slate-500 dark:text-slate-400">{formatDateTime(scannerDbUpdatedAt)}</dd>
            </div>
            <div className="flex items-start justify-between">
              <dt>Repo digest</dt>
              <dd className="text-xs text-slate-500 break-all dark:text-slate-400 md:max-w-xs">
                {summary.platform.repoDigests.length > 0 ? summary.platform.repoDigests[0] : "—"}
              </dd>
            </div>
          </dl>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition dark:border-slate-800 dark:bg-slate-900/60">
          <div className="flex items-start justify-between gap-3">
            <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Policy context</h4>
            <InfoPopover title="Policy context" description={infoHelp.trivyPolicy.description} items={infoHelp.trivyPolicy.items} align="left" />
          </div>
          <dl className="mt-4 space-y-3 text-sm text-slate-600 dark:text-slate-300">
            <div className="flex items-center justify-between">
              <dt>Scan severities</dt>
              <dd className="text-right text-slate-900 dark:text-slate-100">{policy?.scanSeverities ?? "—"}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt>Fail-on severities</dt>
              <dd className="text-right text-slate-900 dark:text-slate-100">{policy?.failSeverities ?? "—"}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt>Ignore unfixed</dt>
              <dd>{ignoreUnfixedLabel}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
};

export const RunPage = () => {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>();
  const { data, loading, error } = useApi(() => fetchRunDetail(projectId ?? "", runId ?? ""), [projectId, runId]);
  const [sbomSummary, setSbomSummary] = useState<SbomSummary | null>(null);
  const [sbomRaw, setSbomRaw] = useState<string | null>(null);
  const [trivySummary, setTrivySummary] = useState<TrivySummary | null>(null);
  const [trivyRaw, setTrivyRaw] = useState<string | null>(null);
  const [artifactError, setArtifactError] = useState<string | null>(null);
  const [loadingArtifacts, setLoadingArtifacts] = useState<boolean>(false);
  const [rawModal, setRawModal] = useState<{ title: string; content: string; fileName?: string } | null>(null);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [assistantFacet, setAssistantFacet] = useState<AssistantFacet>("run_manifest");
  const [assistantPrompt, setAssistantPrompt] = useState<string | undefined>(undefined);

  const openAssistant = (facet: AssistantFacet, prompt?: string) => {
    setAssistantFacet(facet);
    setAssistantPrompt(prompt);
    setAssistantOpen(true);
  };

  useEffect(() => {
    let cancelled = false;
    // Once the base run loads, pull the heavy SBOM/Trivy JSON in parallel and condense it.
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

  // Prepare formatted JSON strings ahead of time so the modal opens instantly.
  const runRaw = useMemo(() => (data ? formatJson(data.metadata) : null), [data]);
  const trivyPolicy = useMemo(() => {
    // Normalise the Trivy policy fields so we can display the exact scan/fail thresholds.
    if (!data) return null;
    const metadata = data.metadata ?? {};
    const assessment = typeof metadata.assessment === "object" && metadata.assessment !== null ? (metadata.assessment as Record<string, unknown>) : null;
    const trivyConfig = assessment && typeof assessment.trivy === "object" && assessment.trivy !== null ? (assessment.trivy as Record<string, unknown>) : null;
    if (!trivyConfig) return null;
    const scanSeverities =
      typeof trivyConfig.scanSeverities === "string"
        ? trivyConfig.scanSeverities
        : typeof trivyConfig.scan_levels === "string"
          ? trivyConfig.scan_levels
          : null;
    const failSeverities =
      typeof trivyConfig.failSeverities === "string"
        ? trivyConfig.failSeverities
        : typeof trivyConfig.fail_levels === "string"
          ? trivyConfig.fail_levels
          : null;
    const ignoreUnfixed =
      typeof trivyConfig.ignoreUnfixed === "boolean"
        ? trivyConfig.ignoreUnfixed
        : typeof trivyConfig.ignore_unfixed === "boolean"
          ? trivyConfig.ignore_unfixed
          : null;
    const scannerMeta =
      typeof trivyConfig.scanner === "object" && trivyConfig.scanner !== null
        ? (trivyConfig.scanner as Record<string, unknown>)
        : null;
    const scannerVersion =
      scannerMeta && typeof scannerMeta.version === "string" && scannerMeta.version.length > 0
        ? scannerMeta.version
        : null;
    const scannerDbUpdatedAt =
      scannerMeta && typeof scannerMeta.dbUpdatedAt === "string" && scannerMeta.dbUpdatedAt.length > 0
        ? scannerMeta.dbUpdatedAt
        : null;
    return {
      scanSeverities,
      failSeverities,
      ignoreUnfixed,
      scannerVersion,
      scannerDbUpdatedAt
    };
  }, [data]);

  if (!projectId || !runId) return <ErrorState message="Run reference incomplete" />;
  if (loading) return <LoadingState message={`Loading run ${runId}`} />;
  if (error || !data) return <ErrorState message={error ?? "Unable to load run detail"} />;

  // Helper for the "View raw JSON" buttons so each section stays uncluttered.
  const buildRawJsonButton = (label: string, content: string | null, fileName?: string) =>
    content
      ? (
        <button
          type="button"
          onClick={() => setRawModal({ title: label, content, fileName })}
          className="rounded-lg border border-blue-300 px-3 py-1 text-sm font-medium text-blue-600 transition hover:border-blue-400 hover:text-blue-500 dark:border-blue-500/40 dark:text-blue-200 dark:hover:border-blue-400 dark:hover:text-blue-100"
        >
          View raw JSON
        </button>
      )
      : null;

  const buildAssistantButton = (facetType: AssistantFacet, prompt: string) => (
    <button
      type="button"
      onClick={() => openAssistant(facetType, prompt)}
      className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900 dark:border-slate-700 dark:text-slate-300 dark:hover:border-slate-500 dark:hover:text-white"
    >
      <SparklesIcon className="h-4 w-4" />
      Ask about this
    </button>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Breadcrumbs items={[{ label: "Projects", to: "/" }, { label: projectId, to: `/projects/${projectId}` }, { label: `Run ${runId}` }]} />
        <button
          type="button"
          onClick={() => openAssistant("run_manifest")}
          className="inline-flex items-center gap-2 rounded-full bg-sky-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-700"
        >
          <SparklesIcon className="h-5 w-5" />
          Ask Assistant
        </button>
      </div>
      <CollapsibleSection
        title="Run overview"
        description="Execution details from the SWFT workflow and deployment output."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {buildRawJsonButton(
              "Run metadata (run.json)",
              runRaw,
              (data.artifacts.find((artifact) => artifact.artifact_type === "run")?.blob_name) ?? "run.json"
            )}
            {buildAssistantButton("run_manifest", `Summarize run ${runId} for an Authorizing Official.`)}
          </div>
        }
        defaultOpen
      >
        <RunDetailCard
          detail={data}
          sbomHighlights={
            sbomSummary
              ? {
                  totalComponents: sbomSummary.totalComponents,
                  uniqueTypes: sbomSummary.uniqueTypes,
                  uniqueLicenses: sbomSummary.uniqueLicenses,
                  baseImage: sbomSummary.baseImage,
                  topLicenses: sbomSummary.topLicenses
                }
              : null
          }
          trivyHighlights={
            trivySummary
              ? {
                  platform: trivySummary.platform
                }
              : null
          }
        />
      </CollapsibleSection>
      <CollapsibleSection
        title="Software Bill of Materials (SBOM)"
        description="Component inventory captured from the container image."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {buildRawJsonButton(
              "SBOM (sbom.cyclonedx.json)",
              sbomRaw,
              (data.artifacts.find((artifact) => artifact.artifact_type === "sbom")?.blob_name) ?? "sbom.cyclonedx.json"
            )}
            {buildAssistantButton("sbom", `Highlight critical supply-chain risks in the SBOM for run ${runId}.`)}
          </div>
        }
      >
        {loadingArtifacts ? (
          <LoadingState message="Loading SBOM summary" />
        ) : artifactError ? (
          <ErrorState message={artifactError} />
        ) : sbomSummary ? (
          <SbomSummaryView summary={sbomSummary} />
        ) : (
          <p className="text-sm text-slate-500 dark:text-slate-400">No SBOM artifact was uploaded for this run.</p>
        )}
      </CollapsibleSection>
      <CollapsibleSection
        title="Vulnerability scan (Trivy)"
        description="Findings reported by Trivy across the container image."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {buildRawJsonButton(
              "Trivy report (trivy-report.json)",
              trivyRaw,
              (data.artifacts.find((artifact) => artifact.artifact_type === "trivy")?.blob_name) ?? "trivy-report.json"
            )}
            {buildAssistantButton("trivy", `Explain the highest-risk vulnerabilities from the Trivy scan for run ${runId}.`)}
          </div>
        }
      >
        {loadingArtifacts ? (
          <LoadingState message="Loading Trivy report" />
        ) : artifactError ? (
          <ErrorState message={artifactError} />
        ) : trivySummary ? (
          <TrivySummaryView summary={trivySummary} policy={trivyPolicy} />
        ) : (
          <p className="text-sm text-slate-500 dark:text-slate-400">No Trivy report was captured for this run.</p>
        )}
      </CollapsibleSection>
      <AssistantPanel
        open={assistantOpen}
        onClose={() => {
          setAssistantOpen(false);
          setAssistantPrompt(undefined);
        }}
        projectId={projectId}
        runId={runId}
        initialFacet={assistantFacet}
        initialPrompt={assistantPrompt}
        contextArtifacts={{
          run: runRaw,
          sbom: sbomRaw,
          trivy: trivyRaw,
        }}
      />
      {rawModal && <JsonModal title={rawModal.title} content={rawModal.content} fileName={rawModal.fileName} onClose={() => setRawModal(null)} />}
    </div>
  );
};
