import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import {
  fetchSwftProject,
  upsertSwftProject,
  fetchSwftParameters,
  setSwftParameter,
  syncSwftCatalog,
  importSwftPolicy,
  importSwftPolicyStates,
  uploadSwftSbom,
  uploadSwftTrivy,
  uploadSwftSignature,
  fetchSwftServices,
  fetchSwftRegions,
  ingestSwftEvidenceFromStorage,
  fetchAzurePolicySets,
  importAzurePolicySet,
} from "@lib/api";
import type { SwftProject, SwftParameter, StorageEvidenceItem, AzurePolicySet } from "@lib/types";
import { LoadingState } from "@components/LoadingState";
import { ErrorState } from "@components/ErrorState";
import { Breadcrumbs } from "@components/Breadcrumbs";

export const SwftWorkspacePage = () => {
  const params = useParams<{ projectId: string }>();
  const [searchParams] = useSearchParams();
  const projectId = params.projectId ? decodeURIComponent(params.projectId) : "";
  const initialRunParam = searchParams.get("runId") ?? "";
  const [loading, setLoading] = useState(true);
  const [projectError, setProjectError] = useState<string | null>(null);
  const [project, setProject] = useState<SwftProject | null>(null);
  const [availableServices, setAvailableServices] = useState<string[]>([]);
  const [servicesLoading, setServicesLoading] = useState(true);
  const [servicesError, setServicesError] = useState<string | null>(null);
  const [selectedServices, setSelectedServices] = useState<string[]>([]);
  const [serviceQuery, setServiceQuery] = useState("");
  const [availableRegions, setAvailableRegions] = useState<string[]>([]);
  const [regionsLoading, setRegionsLoading] = useState(true);
  const [regionsError, setRegionsError] = useState<string | null>(null);
  const [selectedRegions, setSelectedRegions] = useState<string[]>([]);
  const [regionQuery, setRegionQuery] = useState("");
  const [boundaryInput, setBoundaryInput] = useState("");
  const [projectStatus, setProjectStatus] = useState<string | null>(null);

  const [controlId, setControlId] = useState("");
  const [parameters, setParameters] = useState<SwftParameter[]>([]);
  const [parameterValues, setParameterValues] = useState<Record<string, string>>({});
  const [parameterStatus, setParameterStatus] = useState<string | null>(null);
  const [parameterError, setParameterError] = useState<string | null>(null);

  const [catalogFile, setCatalogFile] = useState<File | null>(null);
  const [baselineFile, setBaselineFile] = useState<File | null>(null);
  const [baselineName, setBaselineName] = useState("fedramp-high");
  const [catalogName, setCatalogName] = useState("sp800-53-r5.2.0");
  const [catalogStatus, setCatalogStatus] = useState<string | null>(null);

  const [policyFile, setPolicyFile] = useState<File | null>(null);
  const [policyName, setPolicyName] = useState("nist-sp-800-53-r5");
  const [policyScope, setPolicyScope] = useState("commercial");
  const [policyStatus, setPolicyStatus] = useState<string | null>(null);

  const [stateFile, setStateFile] = useState<File | null>(null);
  const [stateInitiative, setStateInitiative] = useState("nist-sp-800-53-r5");
  const [stateScope, setStateScope] = useState("commercial");
  const [stateStatus, setStateStatus] = useState<string | null>(null);

  const [policyOptions, setPolicyOptions] = useState<AzurePolicySet[]>([]);
  const [policyOptionsLoading, setPolicyOptionsLoading] = useState(true);
  const [policyOptionsError, setPolicyOptionsError] = useState<string | null>(null);
  const [selectedBuiltinPolicy, setSelectedBuiltinPolicy] = useState("nist-sp-800-53-r5");
  const [builtinScope, setBuiltinScope] = useState("gov");
  const [builtinStatus, setBuiltinStatus] = useState<string | null>(null);
  const [builtinError, setBuiltinError] = useState<string | null>(null);
  const [builtinLoading, setBuiltinLoading] = useState(false);

  const [sbomRunId, setSbomRunId] = useState(initialRunParam);
  const [sbomFile, setSbomFile] = useState<File | null>(null);
  const [sbomStatus, setSbomStatus] = useState<string | null>(null);

  const [trivyRunId, setTrivyRunId] = useState(initialRunParam);
  const [trivyFile, setTrivyFile] = useState<File | null>(null);
  const [trivyArtifact, setTrivyArtifact] = useState("");
  const [trivyStatus, setTrivyStatus] = useState<string | null>(null);

  const [sigRunId, setSigRunId] = useState(initialRunParam);
  const [sigFile, setSigFile] = useState<File | null>(null);
  const [sigDigest, setSigDigest] = useState("");
  const [sigVerified, setSigVerified] = useState(true);
  const [sigStatus, setSigStatus] = useState<string | null>(null);
  const [autoRunId, setAutoRunId] = useState(initialRunParam);
  const [autoStatus, setAutoStatus] = useState<StorageEvidenceItem[] | null>(null);
  const [autoError, setAutoError] = useState<string | null>(null);
  const [autoLoading, setAutoLoading] = useState(false);
  const [ingestionMode, setIngestionMode] = useState<"auto" | "manual">("auto");

  const applyRunIdToForms = useCallback((value: string) => {
    setSbomRunId(value);
    setTrivyRunId(value);
    setSigRunId(value);
  }, []);

  useEffect(() => {
    if (!initialRunParam) return;
    setAutoRunId(initialRunParam);
    setSbomRunId((prev) => prev || initialRunParam);
    setTrivyRunId((prev) => prev || initialRunParam);
    setSigRunId((prev) => prev || initialRunParam);
  }, [initialRunParam]);

  const filteredServices = useMemo(() => {
    const remaining = availableServices.filter((svc) => !selectedServices.includes(svc));
    if (!serviceQuery) return remaining;
    const lowered = serviceQuery.toLowerCase();
    const startsWith: string[] = [];
    const contains: string[] = [];
    remaining.forEach((svc) => {
      const lowerName = svc.toLowerCase();
      if (lowerName.startsWith(lowered)) {
        startsWith.push(svc);
      } else if (lowerName.includes(lowered)) {
        contains.push(svc);
      }
    });
    return [...startsWith, ...contains];
  }, [serviceQuery, availableServices, selectedServices]);

  const addServiceFromQuery = (value?: string) => {
    const candidate = (value ?? serviceQuery ?? "").trim();
    if (!candidate) return;
    const canonical =
      availableServices.find((svc) => svc.toLowerCase() === candidate.toLowerCase()) || filteredServices[0];
    setServiceQuery("");
    if (!canonical) {
      setServicesError(`"${candidate}" is not a recognized Azure service.`);
      return;
    }
    setServicesError(null);
    setSelectedServices((prev) => (prev.includes(canonical) ? prev : [...prev, canonical]));
  };

  const filteredRegions = useMemo(() => {
    const remaining = availableRegions.filter((region) => !selectedRegions.includes(region));
    if (!regionQuery) return remaining;
    const lowered = regionQuery.toLowerCase();
    const startsWith: string[] = [];
    const contains: string[] = [];
    remaining.forEach((region) => {
      const lowerName = region.toLowerCase();
      if (lowerName.startsWith(lowered)) {
        startsWith.push(region);
      } else if (lowerName.includes(lowered)) {
        contains.push(region);
      }
    });
    return [...startsWith, ...contains];
  }, [regionQuery, availableRegions, selectedRegions]);

  const addRegionFromQuery = (value?: string) => {
    const candidate = (value ?? regionQuery ?? "").trim();
    if (!candidate) return;
    const canonical =
      availableRegions.find((region) => region.toLowerCase() === candidate.toLowerCase()) || filteredRegions[0];
    setRegionQuery("");
    if (!canonical) {
      setRegionsError(`"${candidate}" is not a recognized Azure region.`);
      return;
    }
    setRegionsError(null);
    setSelectedRegions((prev) => (prev.includes(canonical) ? prev : [...prev, canonical]));
  };

  useEffect(() => {
    let cancelled = false;
    const loadServices = async () => {
      try {
        const services = await fetchSwftServices();
        if (!cancelled) {
          setAvailableServices(services);
          setServicesLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setServicesError((err as Error).message);
          setServicesLoading(false);
        }
      }
    };
    void loadServices();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadRegions = async () => {
      try {
        const regions = await fetchSwftRegions();
        if (!cancelled) {
          setAvailableRegions(regions);
          setRegionsLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setRegionsError((err as Error).message);
          setRegionsLoading(false);
        }
      }
    };
    void loadRegions();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadPolicyOptions = async () => {
      try {
        const sets = await fetchAzurePolicySets();
        if (cancelled) return;
        setPolicyOptions(sets);
        if (sets.length > 0) {
          setSelectedBuiltinPolicy(sets[0].id);
          setBuiltinScope(sets[0].default_scope);
        }
        setPolicyOptionsLoading(false);
      } catch (err) {
        if (!cancelled) {
          setPolicyOptionsError((err as Error).message);
          setPolicyOptionsLoading(false);
        }
      }
    };
    void loadPolicyOptions();
    return () => {
      cancelled = true;
    };
  }, []);

  const loadProject = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setProjectError(null);
    try {
      const record = await fetchSwftProject(projectId);
      setProject(record);
      setSelectedServices(record.services);
      setSelectedRegions(record.regions);
      setBoundaryInput(record.boundary_description ?? "");
    } catch (err) {
      setProject(null);
      setProjectError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) void loadProject();
  }, [projectId, loadProject]);

  const saveProject = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!projectId) return;
    setProjectStatus("Saving...");
    try {
      const updated = await upsertSwftProject(projectId, {
        services: selectedServices,
        regions: selectedRegions,
        boundary_description: boundaryInput || null,
      });
      setProject(updated);
      setProjectStatus("Project boundary saved.");
      setProjectError(null);
    } catch (err) {
      setProjectStatus(null);
      setProjectError((err as Error).message);
    }
  };

  const loadParameters = async () => {
    if (!projectId || !controlId) return;
    setParameterStatus("Loading parameters...");
    setParameterError(null);
    try {
      const rows = await fetchSwftParameters(projectId, controlId);
      setParameters(rows);
      const nextValues: Record<string, string> = {};
      rows.forEach((row) => {
        nextValues[row.param_id] = row.current_value ?? "";
      });
      setParameterValues(nextValues);
      setParameterStatus(`Loaded ${rows.length} parameter(s).`);
    } catch (err) {
      setParameters([]);
      setParameterStatus(null);
      setParameterError((err as Error).message);
    }
  };

  const saveParameter = async (paramId: string) => {
    if (!projectId || !controlId) return;
    setParameterStatus(`Saving ${paramId}...`);
    try {
      await setSwftParameter(projectId, controlId, paramId, parameterValues[paramId] ?? "");
      await loadParameters();
      setParameterStatus(`Updated ${paramId}.`);
    } catch (err) {
      setParameterStatus(null);
      setParameterError((err as Error).message);
    }
  };

  const submitCatalog = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!catalogFile || !baselineFile) {
      setCatalogStatus("Both files are required.");
      return;
    }
    setCatalogStatus("Syncing catalog...");
    try {
      const result = await syncSwftCatalog({
        catalogFile,
        baselineFile,
        baselineName,
        catalogName,
      });
      setCatalogStatus(`Catalog synced (${result.catalog.controls} controls; baseline ${result.baseline.controls}).`);
    } catch (err) {
      setCatalogStatus((err as Error).message);
    }
  };

  const submitPolicy = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!policyFile) {
      setPolicyStatus("Provide an initiative JSON file.");
      return;
    }
    setPolicyStatus("Importing initiative...");
    try {
      const result = await importSwftPolicy(policyFile, policyName, policyScope);
      setPolicyStatus(`Imported ${result.policies} policies (${result.mappings} mappings).`);
    } catch (err) {
      setPolicyStatus((err as Error).message);
    }
  };

  const submitPolicyStates = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!stateFile) {
      setStateStatus("Provide a states JSON export.");
      return;
    }
    setStateStatus("Importing policy states...");
    try {
      const result = await importSwftPolicyStates(stateFile, stateInitiative, stateScope);
      setStateStatus(`Processed ${result.processed} entries (${result.inserted} stored).`);
    } catch (err) {
      setStateStatus((err as Error).message);
    }
  };

  const fetchEvidenceFromStorage = async () => {
    if (!projectId) return;
    const trimmed = autoRunId.trim();
    if (!trimmed) {
      setAutoError("Provide a run ID to import evidence.");
      return;
    }
    setAutoLoading(true);
    setAutoError(null);
    setAutoStatus(null);
    try {
      const response = await ingestSwftEvidenceFromStorage(projectId, trimmed);
      setAutoStatus(response.results);
      const stored = response.results.some((item) => item.status === "stored");
      if (stored) {
        applyRunIdToForms(trimmed);
      }
    } catch (err) {
      setAutoError((err as Error).message);
    } finally {
      setAutoLoading(false);
    }
  };

  const importBuiltinPolicySet = async () => {
    if (!selectedBuiltinPolicy) return;
    setBuiltinLoading(true);
    setBuiltinError(null);
    setBuiltinStatus(null);
    try {
      const result = await importAzurePolicySet(selectedBuiltinPolicy, builtinScope);
      setBuiltinStatus(`Imported ${result.policies} policies (${result.mappings} mappings).`);
    } catch (err) {
      setBuiltinError((err as Error).message);
    } finally {
      setBuiltinLoading(false);
    }
  };

  const submitSbom = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!projectId || !sbomRunId || !sbomFile) {
      setSbomStatus("Provide a run ID and SBOM file.");
      return;
    }
    setSbomStatus("Uploading SBOM...");
    try {
      const result = await uploadSwftSbom(projectId, sbomRunId, sbomFile);
      setSbomStatus(`Stored SBOM for run ${result.run_id}.`);
    } catch (err) {
      setSbomStatus((err as Error).message);
    }
  };

  const submitTrivy = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!projectId || !trivyRunId || !trivyFile) {
      setTrivyStatus("Provide a run ID and Trivy report.");
      return;
    }
    setTrivyStatus("Uploading Trivy report...");
    try {
      const result = await uploadSwftTrivy(projectId, trivyRunId, trivyFile, trivyArtifact || undefined);
      setTrivyStatus(`Stored Trivy report with ${result.metadata?.findings ?? 0} finding(s).`);
    } catch (err) {
      setTrivyStatus((err as Error).message);
    }
  };

  const submitSignature = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!projectId || !sigRunId || !sigFile || !sigDigest) {
      setSigStatus("Provide run ID, digest, and signature file.");
      return;
    }
    setSigStatus("Uploading signature...");
    try {
      const result = await uploadSwftSignature(projectId, sigRunId, sigFile, sigDigest, sigVerified);
      setSigStatus(`Signature stored (verified=${result.metadata?.verified ? "yes" : "no"}).`);
    } catch (err) {
      setSigStatus((err as Error).message);
    }
  };

  const projectInitialized = Boolean(project);
  if (!projectId) return <ErrorState message="Project ID missing" />;
  if (loading) return <LoadingState message="Loading SWFT workspace" />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Breadcrumbs
          items={[
            { label: "Projects", to: "/" },
            { label: projectId, to: `/projects/${projectId}` },
            { label: "SWFT Workspace" },
          ]}
        />
        <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          Beta
        </span>
      </div>

      <section className="rounded-2xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-6 shadow-sm dark:border-slate-800 dark:from-slate-950 dark:to-slate-900">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">Workspace overview</p>
            <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">{projectId}</h1>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Import SBOM/Trivy evidence, Azure Policy initiatives, and NIST parameters for this repository. Everything pins to the compliance database for SSP exports.
            </p>
          </div>
          <dl className="grid grid-cols-2 gap-4 text-sm text-slate-600 dark:text-slate-300">
            <div className="rounded-xl border border-slate-200 bg-white p-3 text-center dark:border-slate-700 dark:bg-slate-900">
              <dt className="text-xs uppercase tracking-wide">Evidence status</dt>
              <dd className="text-lg font-semibold text-slate-900 dark:text-white">
                {autoStatus?.some((entry) => entry.status === "stored") ? "Ingested" : "Pending"}
              </dd>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-3 text-center dark:border-slate-700 dark:bg-slate-900">
              <dt className="text-xs uppercase tracking-wide">Open parameters</dt>
              <dd className="text-lg font-semibold text-slate-900 dark:text-white">
                {parameters.length > 0 ? parameters.filter((param) => !param.current_value).length : "—"}
              </dd>
            </div>
          </dl>
        </div>
      </section>
      {projectError && (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
          {projectError}
        </div>
      )}
      <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Project Boundary</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Define the services, regions, and boundary narrative for <span className="font-semibold">{projectId}</span>.
          </p>
        </div>
        <form className="space-y-5" onSubmit={saveProject}>
          <div className="grid gap-5 lg:grid-cols-2">
            <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900/30">
              <div className="mb-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Azure Footprint</p>
                <h4 className="text-base font-semibold text-slate-900 dark:text-white">Azure Services</h4>
                <p className="text-sm text-slate-500 dark:text-slate-400">Select every Azure capability that defines this boundary.</p>
              </div>
              {servicesLoading ? (
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Loading service catalog…</p>
              ) : (
                <div className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    {selectedServices.length === 0 && <span className="text-xs text-slate-500">No services selected.</span>}
                    {selectedServices.map((name) => (
                      <span
                        key={name}
                        className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-900 dark:bg-blue-900/40 dark:text-blue-100"
                      >
                        {name}
                        <button
                          type="button"
                          onClick={() => setSelectedServices((prev) => prev.filter((svc) => svc !== name))}
                          className="text-blue-600 hover:text-blue-800 dark:text-blue-200 dark:hover:text-white"
                          aria-label={`Remove ${name}`}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start">
                    <input
                      value={serviceQuery}
                      onChange={(event) => setServiceQuery(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === "Tab") {
                          event.preventDefault();
                          addServiceFromQuery();
                        }
                      }}
                      placeholder="Type to search Azure services"
                      className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                    />
                    <button
                      type="button"
                      onClick={addServiceFromQuery}
                      className="rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-100 dark:hover:bg-slate-800"
                    >
                      Add Service
                    </button>
                  </div>
                  {filteredServices.length > 0 && serviceQuery && (
                    <div className="max-h-40 overflow-y-auto rounded-md border border-slate-200 dark:border-slate-700">
                      {filteredServices.slice(0, 8).map((name) => (
                        <button
                          key={name}
                          type="button"
                          onClick={() => addServiceFromQuery(name)}
                          className="flex w-full items-center justify-between px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                        >
                          <span>{name}</span>
                          <span className="text-xs text-slate-400">Add</span>
                        </button>
                      ))}
                    </div>
                  )}
                  {servicesError && <p className="text-xs text-rose-500">{servicesError}</p>}
                  <p className="text-xs text-slate-500 dark:text-slate-400">Only services from the official Azure catalog are allowed.</p>
                </div>
              )}
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900/30">
              <div className="mb-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Azure Footprint</p>
                <h4 className="text-base font-semibold text-slate-900 dark:text-white">Azure Regions</h4>
                <p className="text-sm text-slate-500 dark:text-slate-400">Declare every Azure region in scope for this system boundary.</p>
              </div>
              {regionsLoading ? (
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Loading region catalog…</p>
              ) : (
                <div className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    {selectedRegions.length === 0 && <span className="text-xs text-slate-500">No regions selected.</span>}
                    {selectedRegions.map((name) => (
                      <span
                        key={name}
                        className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-900 dark:bg-emerald-900/40 dark:text-emerald-100"
                      >
                        {name}
                        <button
                          type="button"
                          onClick={() => setSelectedRegions((prev) => prev.filter((region) => region !== name))}
                          className="text-emerald-600 hover:text-emerald-800 dark:text-emerald-200 dark:hover:text-white"
                          aria-label={`Remove ${name}`}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start">
                    <input
                      value={regionQuery}
                      onChange={(event) => setRegionQuery(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === "Tab") {
                          event.preventDefault();
                          addRegionFromQuery();
                        }
                      }}
                      placeholder="Type to search Azure regions"
                      className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                    />
                    <button
                      type="button"
                      onClick={() => addRegionFromQuery()}
                      className="rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-100 dark:hover:bg-slate-800"
                    >
                      Add Region
                    </button>
                  </div>
                  {filteredRegions.length > 0 && regionQuery && (
                    <div className="max-h-40 overflow-y-auto rounded-md border border-slate-200 dark:border-slate-700">
                      {filteredRegions.slice(0, 8).map((name) => (
                        <button
                          key={name}
                          type="button"
                          onClick={() => addRegionFromQuery(name)}
                          className="flex w-full items-center justify-between px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                        >
                          <span>{name}</span>
                          <span className="text-xs text-slate-400">Add</span>
                        </button>
                      ))}
                    </div>
                  )}
                  {regionsError && <p className="text-xs text-rose-500">{regionsError}</p>}
                  <p className="text-xs text-slate-500 dark:text-slate-400">Only regions from the official Azure catalog are allowed.</p>
                </div>
              )}
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Boundary Description</label>
            <textarea
              value={boundaryInput}
              onChange={(event) => setBoundaryInput(event.target.value)}
              rows={4}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>
          <div className="flex items-center gap-3">
            <button
              type="submit"
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-50"
            >
              {projectInitialized ? "Update Boundary" : "Create Project"}
            </button>
            {projectStatus && <span className="text-sm text-slate-600 dark:text-slate-300">{projectStatus}</span>}
          </div>
        </form>
      </section>

      <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Control Parameters</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400">Prompt Dev teams for NIST parameter values and capture them for SSP export.</p>
          </div>
          <div className="flex gap-2">
            <input
              value={controlId}
              onChange={(event) => setControlId(event.target.value.toUpperCase())}
              placeholder="AC-2"
              className="w-32 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
            <button
              type="button"
              onClick={loadParameters}
              className="rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-100 dark:hover:bg-slate-800"
            >
              Load
            </button>
          </div>
        </div>
        {parameterError && <p className="text-sm text-rose-500">{parameterError}</p>}
        {parameterStatus && <p className="text-sm text-slate-500 dark:text-slate-400">{parameterStatus}</p>}
        {parameters.length > 0 ? (
          <div className="space-y-3">
            {parameters.map((param) => (
              <div key={param.param_id} className="rounded-md border border-slate-200 p-3 text-sm dark:border-slate-800">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-medium text-slate-900 dark:text-white">
                      {param.param_id} {param.label && <span className="text-slate-500">({param.label})</span>}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{param.description}</p>
                    {param.allowed_values.length > 0 && (
                      <p className="text-xs text-slate-500 dark:text-slate-400">Allowed: {param.allowed_values.join(", ")}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      value={parameterValues[param.param_id] ?? ""}
                      onChange={(event) =>
                        setParameterValues((prev) => ({
                          ...prev,
                          [param.param_id]: event.target.value,
                        }))
                      }
                      className="w-64 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
                    />
                    <button
                      type="button"
                      onClick={() => saveParameter(param.param_id)}
                      className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-blue-500"
                    >
                      Save
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500 dark:text-slate-400">No parameters loaded yet.</p>
        )}
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Evidence Ingestion</h3>
          <div className="flex gap-2">
            <button
              type="button"
              className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold ${
                ingestionMode === "auto"
                  ? "bg-blue-600 text-white shadow"
                  : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
              }`}
              onClick={() => setIngestionMode("auto")}
            >
              Auto import
            </button>
            <button
              type="button"
              className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold ${
                ingestionMode === "manual"
                  ? "bg-blue-600 text-white shadow"
                  : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
              }`}
              onClick={() => setIngestionMode("manual")}
            >
              Manual upload
            </button>
          </div>
          {ingestionMode === "auto" ? (
            <div className="space-y-4 rounded-lg border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-700 dark:bg-slate-900/30">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Preferred</p>
                  <p className="text-sm font-semibold text-slate-900 dark:text-white">Fetch from Azure Storage</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Paste the GitHub Actions run ID and we’ll pull SBOM/Trivy JSON directly from the blob containers. Evidence is pinned just like manual uploads.
                  </p>
                </div>
                <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  Automatic
                </span>
              </div>
              <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                <input
                  value={autoRunId}
                  onChange={(event) => {
                    setAutoRunId(event.target.value);
                    setAutoStatus(null);
                    setAutoError(null);
                  }}
                  placeholder="Run ID"
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 sm:flex-1"
                />
                <button
                  type="button"
                  onClick={fetchEvidenceFromStorage}
                  disabled={autoLoading}
                  className="rounded-md bg-sky-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {autoLoading ? "Importing..." : "Import evidence"}
                </button>
              </div>
              {autoError && <p className="mt-2 text-xs text-rose-500 dark:text-rose-300">{autoError}</p>}
              {autoStatus && autoStatus.length > 0 && (
                <ul className="mt-3 space-y-2 text-xs">
                  {autoStatus.map((item) => {
                    const tone =
                      item.status === "stored"
                        ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-400/10 dark:text-emerald-200"
                        : item.status === "missing"
                        ? "bg-amber-100 text-amber-800 dark:bg-amber-400/10 dark:text-amber-200"
                        : "bg-rose-100 text-rose-800 dark:bg-rose-400/10 dark:text-rose-200";
                    const label =
                      item.status === "stored" ? "Stored" : item.status === "missing" ? "Missing" : "Failed";
                    return (
                      <li key={item.kind} className="rounded-md border border-slate-200 px-3 py-2 dark:border-slate-700">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-200">
                            {item.kind}
                          </span>
                          <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${tone}`}>{label}</span>
                        </div>
                        {item.message && (
                          <p className="mt-1 text-slate-600 dark:text-slate-400">{item.message}</p>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-300">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Manual upload</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Use this path when automated import isn’t available. Upload SBOM/Trivy JSON or cosign verification output directly.
              </p>
              <div className="mt-4 space-y-4">
                <form className="space-y-2" onSubmit={submitSbom}>
                  <p className="text-sm text-slate-500 dark:text-slate-400">CycloneDX SBOM</p>
                  <input
                    value={sbomRunId}
                    onChange={(event) => setSbomRunId(event.target.value)}
                    placeholder="Run ID"
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                  />
                  <input type="file" onChange={(event) => setSbomFile(event.target.files?.[0] ?? null)} className="w-full text-sm" />
                  <button type="submit" className="rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white">
                    Upload SBOM
                  </button>
                  {sbomStatus && <p className="text-xs text-slate-500 dark:text-slate-400">{sbomStatus}</p>}
                </form>
                <form className="space-y-2" onSubmit={submitTrivy}>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Trivy Report</p>
                  <input
                    value={trivyRunId}
                    onChange={(event) => setTrivyRunId(event.target.value)}
                    placeholder="Run ID"
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                  />
                  <input type="file" onChange={(event) => setTrivyFile(event.target.files?.[0] ?? null)} className="w-full text-sm" />
                  <input
                    value={trivyArtifact}
                    onChange={(event) => setTrivyArtifact(event.target.value)}
                    placeholder="Artifact hint (optional)"
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                  />
                  <button type="submit" className="rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 dark:border-slate-700 dark:text-slate-100">
                    Upload Trivy
                  </button>
                  {trivyStatus && <p className="text-xs text-slate-500 dark:text-slate-400">{trivyStatus}</p>}
                </form>
                <form className="space-y-2" onSubmit={submitSignature}>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Cosign Signature</p>
                  <input
                    value={sigRunId}
                    onChange={(event) => setSigRunId(event.target.value)}
                    placeholder="Run ID"
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                  />
                  <input type="file" onChange={(event) => setSigFile(event.target.files?.[0] ?? null)} className="w-full text-sm" />
                  <input
                    value={sigDigest}
                    onChange={(event) => setSigDigest(event.target.value)}
                    placeholder="sha256:..."
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                  />
                  <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                    <input type="checkbox" checked={sigVerified} onChange={(event) => setSigVerified(event.target.checked)} />
                    Verified
                  </label>
                  <button type="submit" className="rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 dark:border-slate-700 dark:text-slate-100">
                    Upload Signature
                  </button>
                  {sigStatus && <p className="text-xs text-slate-500 dark:text-slate-400">{sigStatus}</p>}
                </form>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Azure Policy Imports</h3>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Import built-in Azure Policy initiatives from Microsoft's GitHub catalog or upload your own JSON exports.
        </p>
        <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-700 dark:bg-slate-900/30">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">GitHub catalog</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Select a regulatory policy set from the Azure Policy repository and ingest it directly into SWFT.
              </p>
            </div>
            <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              Beta
            </span>
          </div>
          {policyOptionsError ? (
            <p className="mt-3 text-xs text-rose-500 dark:text-rose-300">{policyOptionsError}</p>
          ) : (
            <div className="mt-3 space-y-2">
              <select
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                value={selectedBuiltinPolicy}
                onChange={(event) => {
                  setSelectedBuiltinPolicy(event.target.value);
                  const policy = policyOptions.find((item) => item.id === event.target.value);
                  if (policy) setBuiltinScope(policy.default_scope);
                  setBuiltinStatus(null);
                  setBuiltinError(null);
                }}
                disabled={policyOptionsLoading}
              >
                {policyOptions.map((policy) => (
                  <option key={policy.id} value={policy.id}>
                    {policy.label}
                  </option>
                ))}
              </select>
              <textarea
                className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
                value={policyOptions.find((item) => item.id === selectedBuiltinPolicy)?.description ?? ""}
                readOnly
                rows={2}
              />
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 sm:w-32">Scope</label>
                <input
                  value={builtinScope}
                  onChange={(event) => setBuiltinScope(event.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 sm:flex-1"
                  placeholder="e.g. gov or commercial"
                />
                <button
                  type="button"
                  onClick={importBuiltinPolicySet}
                  disabled={policyOptionsLoading || builtinLoading}
                  className="rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {builtinLoading ? "Importing..." : "Import from GitHub"}
                </button>
              </div>
              {builtinError && <p className="text-xs text-rose-500 dark:text-rose-300">{builtinError}</p>}
              {builtinStatus && <p className="text-xs text-emerald-600 dark:text-emerald-300">{builtinStatus}</p>}
            </div>
          )}
        </div>
        <form className="space-y-3" onSubmit={submitPolicy}>
          <p className="text-sm text-slate-500 dark:text-slate-400">Initiative JSON export</p>
          <input type="file" onChange={(event) => setPolicyFile(event.target.files?.[0] ?? null)} className="w-full text-sm" />
          <div className="flex gap-2">
            <input
              value={policyName}
              onChange={(event) => setPolicyName(event.target.value)}
              className="w-1/2 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
              placeholder="nist-sp-800-53-r5"
            />
            <select
              value={policyScope}
              onChange={(event) => setPolicyScope(event.target.value)}
              className="w-1/2 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
            >
              <option value="commercial">commercial</option>
              <option value="gov">gov</option>
            </select>
          </div>
          <button type="submit" className="rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 dark:border-slate-700 dark:text-slate-100">
            Import Initiative
          </button>
          {policyStatus && <p className="text-xs text-slate-500 dark:text-slate-400">{policyStatus}</p>}
        </form>
        <form className="space-y-3" onSubmit={submitPolicyStates}>
          <p className="text-sm text-slate-500 dark:text-slate-400">Policy state snapshot</p>
          <input type="file" onChange={(event) => setStateFile(event.target.files?.[0] ?? null)} className="w-full text-sm" />
          <div className="flex gap-2">
            <input
              value={stateInitiative}
              onChange={(event) => setStateInitiative(event.target.value)}
              className="w-1/2 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
              placeholder="nist-sp-800-53-r5"
            />
            <select
              value={stateScope}
              onChange={(event) => setStateScope(event.target.value)}
              className="w-1/2 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
            >
              <option value="commercial">commercial</option>
              <option value="gov">gov</option>
            </select>
          </div>
          <button type="submit" className="rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 dark:border-slate-700 dark:text-slate-100">
            Import States
          </button>
          {stateStatus && <p className="text-xs text-slate-500 dark:text-slate-400">{stateStatus}</p>}
        </form>
      </section>
    </div>
  );
};
