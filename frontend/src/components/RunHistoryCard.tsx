import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ResponsiveLine, type Point, type SliceTooltipProps } from "@nivo/line";
import { useTheme } from "@hooks/useTheme";
import type { RunSummary } from "@lib/types";

/**
 * Supported comparison window sizes exposed to the user.
 */
type WindowOption = 2 | 3 | 5 | 7 | 9 | 11;
const WINDOW_OPTIONS: WindowOption[] = [2, 3, 5, 7, 9, 11];

type MetricKey = "sbomComponents" | "trivyTotal" | "trivyFailset";

// Describe each line on the chart so toggling metrics is a simple lookup.
type MetricConfig = {
  key: MetricKey;
  label: string;
  color: string;
  accessor: (run: RunSummary) => number | null;
  description: string;
};

const METRICS: MetricConfig[] = [
  {
    key: "sbomComponents",
    label: "SBOM components",
    color: "#38bdf8",
    accessor: (run) => run.sbom_component_total,
    description: "Component count derived from the CycloneDX SBOM."
  },
  {
    key: "trivyTotal",
    label: "Trivy total findings",
    color: "#f97316",
    accessor: (run) => run.trivy_findings_total ?? 0,
    description: "Total vulnerabilities reported by Trivy."
  },
  {
    key: "trivyFailset",
    label: "Trivy fail-set",
    color: "#ef4444",
    accessor: (run) => run.trivy_findings_failset ?? 0,
    description: "Findings in the enforced severity set."
  }
];

/**
 * Convert an ISO timestamp into a locale string (fallbacks for missing/invalid values).
 */
const formatTimestamp = (value: string | null): string => {
  if (!value) return "Timestamp unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

/**
 * Shape the latest runs into Nivo series, filtering to the set of active metrics.
 */
const buildChartSeries = (
  runs: RunSummary[],
  metrics: MetricConfig[],
  active: Set<MetricKey>
): Array<{
    id: string;
    color: string;
    data: Array<{ x: string; y: number | null; runId: string; createdAtLabel: string }>;
  }> => {
  const chronological = runs.slice().reverse();
  const enriched = chronological.map((run) => ({
    ...run,
    label: formatTimestamp(run.created_at),
    runId: run.run_id
  }));
  return metrics
    .filter((metric) => active.has(metric.key))
    .map((metric) => ({
      id: metric.label,
      color: metric.color,
      data: enriched.map((run) => ({
        x: run.runId,
        y: metric.accessor(run),
        runId: run.runId,
        createdAtLabel: run.label,
        run
      }))
    }));
};

/**
 * Derive a Nivo theme palette that mirrors the current Tailwind light/dark mode styling.
 */
const useNivoTheme = (isDark: boolean) =>
  useMemo(
    () => ({
      textColor: isDark ? "#cbd5f5" : "#334155",
      grid: { line: { stroke: isDark ? "rgba(148, 163, 184, 0.2)" : "rgba(148, 163, 184, 0.35)", strokeWidth: 1 } },
      axis: {
        ticks: { text: { fill: isDark ? "#e2e8f0" : "#475569", fontSize: 12 } },
        legend: { text: { fill: isDark ? "#e2e8f0" : "#475569", fontSize: 12 } },
        domain: { line: { stroke: isDark ? "rgba(148, 163, 184, 0.35)" : "rgba(148, 163, 184, 0.5)", strokeWidth: 1 } }
      },
      crosshair: { line: { stroke: isDark ? "#38bdf8" : "#0ea5e9", strokeWidth: 1, strokeOpacity: 0.65 } },
      tooltip: {
        container: {
          background: isDark ? "#0f172a" : "#ffffff",
          color: isDark ? "#e2e8f0" : "#1f2937",
          fontSize: 13,
          borderRadius: 12,
          padding: 12,
          boxShadow: isDark ? "0 10px 30px rgba(15, 23, 42, 0.45)" : "0 10px 35px rgba(15, 23, 42, 0.15)"
        }
      }
    }),
    [isDark]
  );

/**
 * Trend card that renders SBOM/Trivy metrics across the last N runs with interactive navigation.
 */
export const RunHistoryCard = ({ projectId, runs }: { projectId: string; runs: RunSummary[] }) => {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const isDark = theme === "dark";

  // Default to five runs when we can but gracefully fall back if there isn't enough data.
  const preferredDefault = WINDOW_OPTIONS.includes(5) ? 5 : WINDOW_OPTIONS[0];
  const [windowSize, setWindowSize] = useState<WindowOption>(preferredDefault);
  // Maintain the selected metrics inside a Set so toggles are easy to flip on/off.
  const [visibleMetrics, setVisibleMetrics] = useState<Set<MetricKey>>(() => new Set(METRICS.map((metric) => metric.key)));

  const effectiveCount = Math.min(windowSize, runs.length);
  const recentRuns = useMemo(() => runs.slice(0, effectiveCount), [runs, effectiveCount]);
  const chartSeries = useMemo(() => buildChartSeries(recentRuns, METRICS, visibleMetrics), [recentRuns, visibleMetrics]);
  const noMetricsSelected = chartSeries.length === 0;
  const hasRenderableData = chartSeries.some((serie) => serie.data.some((point) => point.y !== null));
  const showPlaceholder = noMetricsSelected || !hasRenderableData;
  const placeholderTitle = noMetricsSelected ? "Select a metric to visualise" : "Not enough data yet";
  const placeholderSubtitle = noMetricsSelected ? "Enable at least one metric above to render the chart." : "Generate additional runs to populate SBOM and Trivy metrics.";
  const nivoTheme = useNivoTheme(isDark);

  const toggleMetric = (key: MetricKey) => {
    // Preserve at least one metric so the chart never renders empty lines.
    setVisibleMetrics((current) => {
      const next = new Set(current);
      if (next.has(key)) {
        if (next.size === 1) return current; // keep at least one metric visible
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const handlePointClick = (point: Point) => {
    // Jump straight to the run detail when the user clicks a point on the chart.
    const runId = point.data.runId as string | undefined;
    if (runId) {
      navigate(`/projects/${projectId}/runs/${runId}`);
    }
  };

  const windowLabel = effectiveCount < windowSize ? `${effectiveCount} of ${windowSize}` : `${effectiveCount}`;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition dark:border-slate-800 dark:bg-slate-950/50">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">Trend history</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">Compare SBOM and Trivy signals across recent runs. Click any point to jump to the run detail.</p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-100/70 p-1 dark:border-slate-700 dark:bg-slate-900/60">
          {WINDOW_OPTIONS.map((option) => {
            const isActive = option === windowSize;
            const disabled = runs.length < 2 && option > 2;
            return (
              <button
                key={option}
                type="button"
                onClick={() => setWindowSize(option)}
                disabled={disabled}
                className={`rounded-full px-3 py-1 text-sm font-medium transition ${
                  isActive ? "bg-white text-blue-600 shadow-sm dark:bg-slate-700 dark:text-blue-200" : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
                } ${disabled ? "cursor-not-allowed opacity-50" : ""}`}
              >
                {option}
              </button>
            );
          })}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {METRICS.map((metric) => {
          const isActive = visibleMetrics.has(metric.key);
          return (
            <button
              key={metric.key}
              type="button"
              onClick={() => toggleMetric(metric.key)}
              className={`group flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition ${
                isActive
                  ? "border-transparent bg-slate-900 text-white shadow-sm dark:bg-slate-700"
                  : "border-slate-200 bg-white text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-slate-600"
              }`}
            >
              <span className="flex h-2.5 w-2.5 items-center justify-center rounded-full" style={{ background: metric.color }} />
              <span>{metric.label}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-3 text-xs font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">Showing {windowLabel} most recent runs</div>

      <div className="mt-6 h-80">
        {showPlaceholder ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-200 bg-slate-50/70 dark:border-slate-700 dark:bg-slate-900/30">
            <span className="text-sm font-semibold text-slate-600 dark:text-slate-300">{placeholderTitle}</span>
            <span className="text-xs text-slate-500 dark:text-slate-400">{placeholderSubtitle}</span>
          </div>
        ) : (
          <ResponsiveLine
            data={chartSeries}
            margin={{ top: 20, right: 30, bottom: 50, left: 56 }}
            xScale={{ type: "point" }}
            yScale={{ type: "linear", min: 0, max: "auto", stacked: false }}
            theme={nivoTheme}
            colors={(serie) => (typeof serie.color === "string" ? serie.color : undefined)}
            lineWidth={3}
            enablePoints
            pointSize={10}
            pointBorderWidth={2}
            pointBorderColor={isDark ? "#0f172a" : "#ffffff"}
            enableSlices="x"
            sliceTooltip={({ slice }: SliceTooltipProps) => (
              <div className="rounded-xl bg-white p-3 text-sm text-slate-700 shadow-lg ring-1 ring-slate-200 dark:bg-slate-900 dark:text-slate-200 dark:ring-slate-700">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">Run {slice.points[0]?.data.runId as string}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400">{slice.points[0]?.data.createdAtLabel as string}</div>
                <div className="mt-2 space-y-1">
                  {slice.points.map((point) => (
                    <div key={point.id} className="flex items-center gap-2">
                      <span className="inline-flex h-2.5 w-2.5 flex-none rounded-full" style={{ background: point.serieColor }} />
                      <span className="flex-1 text-xs">{point.serieId}</span>
                      <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">{point.data.yFormatted}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            axisBottom={{ tickRotation: -35, legend: "Run ID", legendOffset: 40, legendPosition: "middle" }}
            axisLeft={{ legend: "Counts", legendOffset: -45, legendPosition: "middle" }}
            crosshairType="x"
            onClick={handlePointClick}
            useMesh
            motionConfig="gentle"
            animate
          />
        )}
      </div>
    </div>
  );
};
