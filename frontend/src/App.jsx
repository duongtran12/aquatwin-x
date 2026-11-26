import { useLanguage, localizeStatus, runtimeLabel, valveActionLabel } from "./language";
import { useCallback, useEffect, useMemo, useState } from "react";
import { cancelJob, deleteNetwork, getHistory, getHistoryAnalytics, getHistoryItem, getNetwork, getNetworks, getSystemHealth, historyDownloadUrl, importNetwork, importValveRegistry, setHistoryArchived, simulateFailure, simulateWhatIf, startOptimization, waitForOptimization } from "./api/client";
import BatchExperiment from "./components/BatchExperiment";
import ExperimentAnalytics from "./components/ExperimentAnalytics";
import FitnessChart from "./components/FitnessChart";
import HistoryComparison from "./components/HistoryComparison";
import HistoryDetail from "./components/HistoryDetail";
import KpiCard from "./components/KpiCard";
import MetricComparison from "./components/MetricComparison";
import NetworkMap from "./components/NetworkMap";
import { findScenarioPreset, SCENARIO_PRESETS } from "./scenarios";
import { resolveSystemStatus } from "./systemStatus";

const DEFAULT_NETWORK_ID = "aquatwin_demo";
const fixed = (value, digits = 2) => Number(value || 0).toFixed(digits);
const RUN_LABELS = { failure: "Failure", manual_recovery: "Manual recovery", optimization: "AI recovery" };

function App() {
  const { language, setLanguage, locale, t } = useLanguage();
  const [networks, setNetworks] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
  const [networkId, setNetworkId] = useState(DEFAULT_NETWORK_ID);
  const [network, setNetwork] = useState(null);
  const [selectedPipe, setSelectedPipe] = useState("P3");
  const [selectedValves, setSelectedValves] = useState([]);
  const [scenario, setScenario] = useState({ leakArea: 0.0005, startHour: 2, endHour: 12 });
  const [failureResult, setFailureResult] = useState(null);
  const [manualResult, setManualResult] = useState(null);
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [historyFilters, setHistoryFilters] = useState({ networkId: "all", runType: "all", runtimeMode: "all", archiveStatus: "active" });
  const [analytics, setAnalytics] = useState(null);
  const [analyticsMode, setAnalyticsMode] = useState("all");
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [selectedHistory, setSelectedHistory] = useState(null);
  const [comparisonIds, setComparisonIds] = useState([]);
  const [comparisonItems, setComparisonItems] = useState(null);
  const [comparisonBusy, setComparisonBusy] = useState(false);
  const [historyBusy, setHistoryBusy] = useState("");
  const [busy, setBusy] = useState("");
  const [optimizationJob, setOptimizationJob] = useState(null);
  const [optimizerConfig, setOptimizerConfig] = useState({
    populationSize: 20,
    generations: 20,
    maxActions: 2,
    seed: 42,
  });
  const [error, setError] = useState("");
  const [notice, setNotice] = useState(null);
  const [networkImportBusy, setNetworkImportBusy] = useState(false);

  const scenarioErrors = useMemo(() => {
    const errors = [];
    const leakArea = Number(scenario.leakArea);
    const startHour = Number(scenario.startHour);
    const endHour = Number(scenario.endHour);
    if (!Number.isFinite(leakArea) || leakArea <= 0) errors.push("Leak area must be greater than zero.");
    if (!Number.isInteger(startHour) || startHour < 0 || startHour > 23) errors.push("Start hour must be from 0 to 23.");
    if (!Number.isInteger(endHour) || endHour < 1 || endHour > 24) errors.push("End hour must be from 1 to 24.");
    if (Number.isFinite(startHour) && Number.isFinite(endHour) && endHour <= startHour) errors.push("End hour must be later than start hour.");
    return errors;
  }, [scenario]);
  const scenarioValid = scenarioErrors.length === 0;
  const activeScenarioPreset = useMemo(() => findScenarioPreset(scenario), [scenario]);
  const optimizerErrors = useMemo(() => {
    const errors = [];
    if (!Number.isInteger(optimizerConfig.populationSize) || optimizerConfig.populationSize < 4 || optimizerConfig.populationSize > 100) errors.push("Population must be from 4 to 100.");
    if (!Number.isInteger(optimizerConfig.generations) || optimizerConfig.generations < 1 || optimizerConfig.generations > 200) errors.push("Generations must be from 1 to 200.");
    if (!Number.isInteger(optimizerConfig.maxActions) || optimizerConfig.maxActions < 1 || optimizerConfig.maxActions > 5) errors.push("Action limit must be from 1 to 5.");
    if (!Number.isInteger(optimizerConfig.seed)) errors.push("Seed must be an integer.");
    return errors;
  }, [optimizerConfig]);
  const optimizerValid = optimizerErrors.length === 0;

  const refreshHistory = useCallback(() => (
    getHistory(20, historyFilters).then(setHistory).catch((requestError) => setError(requestError.message))
  ), [historyFilters]);

  const refreshAnalytics = useCallback(async () => {
    setAnalyticsLoading(true);
    try {
      setAnalytics(await getHistoryAnalytics(analyticsMode));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setAnalyticsLoading(false);
    }
  }, [analyticsMode]);

  useEffect(() => {
    getNetworks().then(setNetworks).catch((requestError) => setError(requestError.message));
    getSystemHealth().then(setSystemHealth).catch(() => setSystemHealth({ status: "unavailable" }));
  }, []);

  useEffect(() => {
    refreshHistory();
  }, [refreshHistory]);

  useEffect(() => {
    setNetwork(null);
    setFailureResult(null);
    setManualResult(null);
    setOptimizationResult(null);
    getNetwork(networkId).then(setNetwork).catch((requestError) => setError(requestError.message));
  }, [networkId]);

  useEffect(() => {
    refreshAnalytics();
  }, [refreshAnalytics]);

  useEffect(() => {
    if (!network) return;
    const pipes = network.elements.links.filter((link) => link.type === "pipe");
    if (!pipes.some((pipe) => pipe.id === selectedPipe)) setSelectedPipe(pipes[0]?.id || "");
    setSelectedValves(network.valves.filter((valve) => valve.link_id === selectedPipe).map((valve) => valve.valve_id));
  }, [network, selectedPipe]);

  useEffect(() => {
    setFailureResult(null);
    setManualResult(null);
    setOptimizationResult(null);
    setNotice(null);
  }, [selectedPipe, scenario.leakArea, scenario.startHour, scenario.endHour]);

  const scenarioPayload = useCallback(() => ({
    pipe_id: selectedPipe,
    leak_area: Number(scenario.leakArea),
    start_time: Number(scenario.startHour) * 3600,
    end_time: Number(scenario.endHour) * 3600,
    split_position: 0.5,
    discharge_coefficient: 0.75,
    pressure_drop_threshold: 2,
  }), [scenario, selectedPipe]);

  const execute = async (taskName, action, successMessage) => {
    setBusy(taskName);
    setError("");
    setNotice(null);
    try {
      await action();
      setNotice([successMessage]);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy("");
    }
  };

  const runFailure = () => execute("failure", async () => {
    setFailureResult(await simulateFailure(networkId, scenarioPayload()));
    setManualResult(null);
    setOptimizationResult(null);
    await Promise.all([refreshHistory(), refreshAnalytics()]);
  }, "Failure simulation completed and saved to history.");

  const runManualRecovery = () => execute("manual", async () => {
    setManualResult(await simulateWhatIf(
      networkId,
      scenarioPayload(),
      selectedValves.map((valveId) => ({ valve_id: valveId, status: "CLOSED" })),
    ));
    setOptimizationResult(null);
    await Promise.all([refreshHistory(), refreshAnalytics()]);
  }, "Manual recovery evaluated and saved to history.");

  const runAiRecovery = () => execute("optimization", async () => {
    setOptimizationJob({ status: "queued", progress: { percent: 0, message: "Waiting to start" } });
    const job = await startOptimization(networkId, scenarioPayload(), optimizerConfig);
    setOptimizationJob(job);
    setOptimizationResult(await waitForOptimization(job.job_id, setOptimizationJob));
    setManualResult(null);
    await Promise.all([refreshHistory(), refreshAnalytics()]);
  }, "AI recovery completed and saved to history.");

  const cancelOptimization = async () => {
    if (!optimizationJob?.job_id || busy !== "optimization") return;
    setError("");
    try {
      setOptimizationJob(await cancelJob(optimizationJob.job_id));
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const updateOptimizerConfig = (field, value) => {
    setOptimizerConfig((current) => ({ ...current, [field]: Number(value) }));
    setOptimizationResult(null);
  };

  const updateHistoryFilter = (field, value) => {
    setHistoryFilters((current) => ({ ...current, [field]: value }));
  };

  const openHistory = async (runId) => {
    setHistoryBusy(runId);
    setError("");
    try {
      setSelectedHistory(await getHistoryItem(runId));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setHistoryBusy("");
    }
  };

  const toggleHistoryComparison = (runId) => {
    setComparisonItems(null);
    setComparisonIds((current) => {
      if (current.includes(runId)) return current.filter((item) => item !== runId);
      return current.length < 2 ? [...current, runId] : [current[1], runId];
    });
  };

  const compareHistory = async () => {
    if (comparisonIds.length !== 2) return;
    setComparisonBusy(true);
    setError("");
    try {
      setComparisonItems(await Promise.all(comparisonIds.map(getHistoryItem)));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setComparisonBusy(false);
    }
  };

  const updateHistoryArchive = async (item) => {
    setHistoryBusy(item.run_id);
    setError("");
    setNotice(null);
    try {
      await setHistoryArchived(item.run_id, !item.archived);
      setComparisonIds((current) => current.filter((runId) => runId !== item.run_id));
      setComparisonItems(null);
      if (selectedHistory?.run_id === item.run_id) setSelectedHistory(null);
      await Promise.all([refreshHistory(), refreshAnalytics()]);
      setNotice([item.archived ? "Run restored to active history." : "Run archived. Its evidence remains available."]);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setHistoryBusy("");
    }
  };

  const handleNetworkImport = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setNetworkImportBusy(true);
    setError("");
    setNotice(null);
    try {
      const imported = await importNetwork(file);
      setNetworks(await getNetworks());
      setNetworkId(imported.network.name);
      setNotice(["Network {network} imported with {count} virtual valves.", { network: imported.network.name, count: imported.valves.length }]);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setNetworkImportBusy(false);
    }
  };

  const handleNetworkDelete = async () => {
    if (network?.source !== "uploaded" || busy) return;
    if (!window.confirm(t("Delete uploaded network {network}? Saved run history will be kept.", { network: networkId }))) return;
    setNetworkImportBusy(true);
    setError("");
    setNotice(null);
    try {
      await deleteNetwork(networkId);
      const availableNetworks = await getNetworks();
      setNetworks(availableNetworks);
      setNetworkId(availableNetworks.some((item) => item.name === DEFAULT_NETWORK_ID)
        ? DEFAULT_NETWORK_ID
        : availableNetworks[0]?.name || "");
      setNotice(["Network {network} deleted. Historical run evidence was preserved.", { network: networkId }]);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setNetworkImportBusy(false);
    }
  };

  const handleValveImport = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || network?.source !== "uploaded" || busy) return;
    setNetworkImportBusy(true);
    setError("");
    setNotice(null);
    try {
      const updated = await importValveRegistry(networkId, file);
      setNetwork(updated);
      setNotice(["Valve registry updated with {count} surveyed valve locations.", { count: updated.valves.length }]);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setNetworkImportBusy(false);
    }
  };

  const worstStep = useMemo(() => {
    if (!failureResult?.time_steps?.length) return null;
    return failureResult.time_steps.reduce((worst, step) => (
      step.metrics.service_availability < worst.metrics.service_availability ? step : worst
    ));
  }, [failureResult]);

  const nodeStates = useMemo(() => Object.fromEntries(
    (worstStep?.nodes || []).filter((node) => node.pressure_change <= -2).map((node) => [node.id, "affected"]),
  ), [worstStep]);

  const failureSummary = failureResult?.summary || manualResult?.failure?.summary || optimizationResult?.failure_summary;
  const recoverySummary = optimizationResult?.best_candidate?.summary || manualResult?.recovery?.summary;
  const bestActions = optimizationResult?.best_candidate?.actions || manualResult?.actions || [];
  const nodeCount = (network?.network?.junctions || 0) + (network?.network?.reservoirs || 0);
  const runtime = network?.runtime;
  const demoMode = runtime?.effective_mode === "demo";
  const systemStatus = resolveSystemStatus(systemHealth, runtime);
  const pipeLinks = useMemo(() => (network?.elements?.links || []).filter((link) => link.type === "pipe"), [network]);

  const toggleValve = (valveId) => setSelectedValves((current) => (
    current.includes(valveId) ? current.filter((item) => item !== valveId) : [...current, valveId]
  ));

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <a className="brand" href="#overview"><span className="brand-mark">AX</span><span><strong>AquaTwin</strong><small>{t("Decision system")}</small></span></a>
        <nav>
          <a className="nav-link nav-link--active" href="#overview"><span>01</span>{t("Overview")}</a>
          <a className="nav-link" href="#scenario"><span>02</span>{t("Scenario")}</a>
          <a className="nav-link" href="#impact"><span>03</span>{t("Impact")}</a>
          <a className="nav-link" href="#recovery"><span>04</span>{t("Recovery")}</a>
          <a className="nav-link" href="#analytics"><span>05</span>{t("Analytics")}</a>
          <a className="nav-link" href="#experiments"><span>06</span>{t("Experiments")}</a>
          <a className="nav-link" href="#history"><span>07</span>{t("History")}</a>
        </nav>
        <div className={`sidebar-note sidebar-note--${systemStatus.key}`} title={systemHealth?.build_commit ? t("Build {commit}", { commit: systemHealth.build_commit }) : undefined}><span className="status-dot" /><div><strong>{t(systemStatus.title)}</strong><small>{t(systemStatus.detail)}{systemHealth?.version ? ` · v${systemHealth.version}` : ""}</small></div></div>
      </aside>

      <main className="dashboard">
        <header className="topbar" id="overview">
          <div><p className="eyebrow">{t("WATER NETWORK OPERATIONS")}</p><h1>{t("Resilience control room")}</h1></div>
          <div className="network-controls">
            <label className="language-control">
              <span>{t("Language")}</span>
              <select value={language} onChange={(event) => setLanguage(event.target.value)}>
                <option value="vi" lang="vi">Tiếng Việt</option>
                <option value="en" lang="en">English</option>
              </select>
            </label>
            <label className="network-badge">
              <span>{t("Active network")} / {runtimeLabel(t, runtime?.effective_mode)}</span>
              <select value={networkId} onChange={(event) => setNetworkId(event.target.value)}>
                {networks.map((item) => <option key={item.name} value={item.name}>{item.name}{item.source === "uploaded" ? ` (${t("uploaded")})` : ""}</option>)}
              </select>
            </label>
            <label className={networkImportBusy ? "network-import network-import--busy" : "network-import"}>
              <input type="file" accept=".inp" disabled={networkImportBusy} onChange={handleNetworkImport} />
              <span>{networkImportBusy ? t("Importing...") : t("Import EPANET .inp")}</span>
              <small>{t("Max 5 MB / valves generated automatically")}</small>
            </label>
            {network?.source === "uploaded" && <label className={networkImportBusy ? "valve-import valve-import--busy" : "valve-import"}>
              <input type="file" accept=".json,application/json" disabled={networkImportBusy || Boolean(busy)} onChange={handleValveImport} />
              <span>{t("Import valves JSON")}</span>
              <small>{t("{count} {source} locations", { count: network.valves.length, source: t(network.valve_source || "active") })}</small>
            </label>}
            {network?.source === "uploaded" && <button className="network-delete" type="button" disabled={networkImportBusy || Boolean(busy)} onClick={handleNetworkDelete}>{t("Delete")}</button>}
          </div>
        </header>
        {demoMode && <div className="runtime-notice"><strong>{t("DEMO MODE")}</strong><span>{t("Synthetic preview data is active because WNTR is blocked. These values must not be used in the experimental report.")}</span></div>}
        {error && <div className="alert" role="alert"><strong>{t("Request failed")}</strong><span>{localizeStatus(t, error)}</span></div>}
        {notice && <div className="success-notice" role="status"><strong>{t("COMPLETED")}</strong><span>{t(...notice)}</span><button type="button" onClick={() => setNotice(null)} aria-label={t("Dismiss notification")}>×</button></div>}

        <section className="overview-grid">
          <article className="panel map-panel">
            <div className="panel-heading"><div><p className="section-label">{t("LIVE TOPOLOGY")}</p><h2>{t("Distribution network")}</h2></div><div className="legend"><span className="legend-normal" />{t("Normal")} <span className="legend-impact" />{t("Affected")}</div></div>
            {network ? <NetworkMap elements={network.elements} selectedPipe={selectedPipe} nodeStates={nodeStates} onSelectPipe={setSelectedPipe} /> : <div className="loading-block">{t("Loading network model...")}</div>}
            <div className="map-footer">
              <span><strong>{nodeCount}</strong> {t("nodes")}</span><span><strong>{network?.network?.pipes || 0}</strong> {t("pipes")}</span><span><strong>{network?.valves?.length || 0}</strong> {network?.valve_source === "surveyed" ? t("surveyed valves") : t("virtual valves")}</span><span className="map-tip">{t("Select a pipe to define the incident")}</span>
            </div>
          </article>

          <article className="panel scenario-panel" id="scenario">
            <div className="panel-heading"><div><p className="section-label">{t("SCENARIO BUILDER")}</p><h2>{t("Pipe leak")}</h2></div><span className="incident-pill">{t("Selected: {pipe}", { pipe: selectedPipe })}</span></div>
            <div className="scenario-presets" aria-label={t("Quick incident scenarios")}>
              {SCENARIO_PRESETS.map((preset) => (
                <button
                  className={activeScenarioPreset === preset.id ? "scenario-preset scenario-preset--active" : "scenario-preset"}
                  disabled={Boolean(busy)}
                  key={preset.id}
                  onClick={() => setScenario({ ...preset.scenario })}
                  title={t(preset.description)}
                  type="button"
                >
                  <strong>{t(preset.label)}</strong>
                  <small>{preset.scenario.leakArea} m²</small>
                </button>
              ))}
            </div>
            <label className="field-label" htmlFor="pipe">{t("Failure pipe")}</label>
            <select id="pipe" value={selectedPipe} onChange={(event) => setSelectedPipe(event.target.value)}>{pipeLinks.map((link) => <option key={link.id}>{link.id}</option>)}</select>
            <label className="field-label" htmlFor="area">{t("Leak area (m²)")}</label>
            <input id="area" type="number" min="0.0001" step="0.0001" aria-invalid={Number(scenario.leakArea) <= 0} value={scenario.leakArea} onChange={(event) => setScenario({ ...scenario, leakArea: event.target.value })} />
            <div className="two-fields">
              <div><label className="field-label" htmlFor="start">{t("Start (hour)")}</label><input id="start" type="number" min="0" max="23" value={scenario.startHour} onChange={(event) => setScenario({ ...scenario, startHour: event.target.value })} /></div>
              <div><label className="field-label" htmlFor="end">{t("End (hour)")}</label><input id="end" type="number" min="1" max="24" value={scenario.endHour} onChange={(event) => setScenario({ ...scenario, endHour: event.target.value })} /></div>
            </div>
            <div className="scenario-summary"><span>{t("Duration")}</span><strong>{t("{count} hours", { count: Math.max(0, Number(scenario.endHour) - Number(scenario.startHour)) })}</strong></div>
            {!scenarioValid && <div className="validation-message">{scenarioErrors.map((message) => <span key={message}>{t(message)}</span>)}</div>}
            <button className="primary-button" type="button" disabled={Boolean(busy) || !network || !scenarioValid} onClick={runFailure}>{busy === "failure" ? t("Simulating...") : t("Run failure simulation")}</button>
          </article>
        </section>

        <section id="impact">
          <div className="section-heading"><div><p className="section-label">{t("IMPACT ANALYSIS")}</p><h2>{t("Worst-state indicators")}</h2></div><span>{worstStep ? t("Snapshot at {hour}h", { hour: worstStep.time_seconds / 3600 }) : t("Awaiting simulation")}</span></div>
          <div className="kpi-grid">
            <KpiCard label={t("Service availability")} value={failureSummary ? `${fixed(failureSummary.minimum_service_availability * 100, 1)}%` : "--"} detail={t("Minimum during incident")} tone="cyan" />
            <KpiCard label={t("Pressure violations")} value={failureSummary?.maximum_pressure_violations ?? "--"} detail={t("Nodes below requirement")} tone="amber" />
            <KpiCard label={t("Affected nodes")} value={failureSummary?.maximum_affected_nodes ?? "--"} detail={t("Pressure loss ≥ 2 m")} tone="red" />
            <KpiCard label={t("Leakage volume")} value={failureSummary ? `${fixed(failureSummary.total_leakage_volume)} m³` : "--"} detail={t("Integrated over scenario")} tone="blue" />
          </div>
        </section>

        <section className="recovery-grid" id="recovery">
          <article className="panel recovery-panel">
            <div className="panel-heading"><div><p className="section-label">{t("WHAT-IF CONTROL")}</p><h2>{t("Manual isolation")}</h2></div></div>
            <p className="panel-copy">{t("Choose virtual valves to close, then evaluate service and leakage after isolation.")}</p>
            <div className="valve-grid">{(network?.valves || []).map((valve) => (
              <label className={selectedValves.includes(valve.valve_id) ? "valve-option valve-option--selected" : "valve-option"} key={valve.valve_id}>
                <input type="checkbox" checked={selectedValves.includes(valve.valve_id)} onChange={() => toggleValve(valve.valve_id)} /><span>{valve.valve_id}<small>{valve.link_id} / {t(valve.endpoint)}</small></span>
              </label>
            ))}</div>
            <button className="secondary-button" type="button" disabled={Boolean(busy) || !failureSummary || selectedValves.length === 0} onClick={runManualRecovery}>{busy === "manual" ? t("Evaluating...") : t("Evaluate {count} valve action(s)", { count: selectedValves.length })}</button>
          </article>

          <article className="panel ai-panel">
            <div className="panel-heading"><div><p className="section-label">{t("AI RECOVERY")}</p><h2>{t("Genetic optimization")}</h2></div><span className="ai-badge">GA</span></div>
            <p className="panel-copy">{t("Search within the action limit to balance service continuity, pressure and leakage.")}</p>
            <div className="optimizer-config">
              <label><span>{t("Population")}</span><input type="number" min="4" max="100" value={optimizerConfig.populationSize} onChange={(event) => updateOptimizerConfig("populationSize", event.target.value)} disabled={Boolean(busy)} /></label>
              <label><span>{t("Generations")}</span><input type="number" min="1" max="200" value={optimizerConfig.generations} onChange={(event) => updateOptimizerConfig("generations", event.target.value)} disabled={Boolean(busy)} /></label>
              <label><span>{t("Action limit")}</span><input type="number" min="1" max="5" value={optimizerConfig.maxActions} onChange={(event) => updateOptimizerConfig("maxActions", event.target.value)} disabled={Boolean(busy)} /></label>
              <label><span>{t("Random seed")}</span><input type="number" value={optimizerConfig.seed} onChange={(event) => updateOptimizerConfig("seed", event.target.value)} disabled={Boolean(busy)} /></label>
            </div>
            {!optimizerValid && <p className="optimizer-error">{t(optimizerErrors[0])}</p>}
            <button className="primary-button" type="button" disabled={Boolean(busy) || !failureSummary || !optimizerValid} onClick={runAiRecovery}>{busy === "optimization" ? t("Optimizing · {percent}%", { percent: fixed(optimizationJob?.progress?.percent, 0) }) : t("Find optimal recovery")}</button>
            {busy === "optimization" && optimizationJob?.cancellable && <button className="secondary-button ai-cancel" type="button" onClick={cancelOptimization} disabled={optimizationJob.status === "cancelling"}>{optimizationJob.status === "cancelling" ? t("Cancelling...") : t("Cancel optimization")}</button>}
            {busy === "optimization" && optimizationJob?.progress && <div className="experiment-progress ai-progress"><div><span>{localizeStatus(t, optimizationJob.progress.message || optimizationJob.status)}</span><strong>{fixed(optimizationJob.progress.percent, 0)}%</strong></div><progress max="100" value={optimizationJob.progress.percent || 0} /></div>}
            {optimizationResult?.best_candidate && <div className="best-score"><span>{t("Best solution score")}</span><strong>{fixed(optimizationResult.best_candidate.score, 1)}</strong><small>{t("{count} unique candidates evaluated", { count: optimizationResult.unique_evaluated_count })}</small></div>}
          </article>
        </section>

        <section className="analysis-grid">
          <article className="panel comparison-panel"><div className="panel-heading"><div><p className="section-label">{t("DECISION EVIDENCE")}</p><h2>{t("Before / after comparison")}</h2></div></div><MetricComparison failure={failureSummary} recovery={recoverySummary} /></article>
          <article className="panel chart-panel"><div className="panel-heading"><div><p className="section-label">{t("CONVERGENCE")}</p><h2>{t("GA fitness history")}</h2></div><div className="chart-legend"><span />{t("Best")} <span />{t("Average")}</div></div><FitnessChart history={optimizationResult?.history} /></article>
        </section>

        <section className="panel decision-panel">
          <div><p className="section-label">{t("RECOMMENDED RESPONSE")}</p><h2>{bestActions.length ? t("Recovery plan ready for review") : t("Run a recovery analysis to generate a plan")}</h2><p>{bestActions.length ? t("The following control actions produced the current recovery indicators.") : t("AquaTwin-X keeps recommendations explainable by showing every proposed valve operation and its measured impact.")}</p></div>
          <div className="action-list">{bestActions.map((action, index) => <div className="action-item" key={`${action.valve_id}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><strong>{valveActionLabel(t, action)}</strong><small>{action.link_id ? t("on {link}", { link: action.link_id }) : t("virtual isolation valve")}</small></div>)}</div>
        </section>

        <ExperimentAnalytics analytics={analytics} mode={analyticsMode} onModeChange={setAnalyticsMode} loading={analyticsLoading} />

        <BatchExperiment networkId={networkId} pipes={pipeLinks} runtimeMode={runtime?.effective_mode} />

        <section className="panel history-panel" id="history">
          <div className="panel-heading">
            <div><p className="section-label">{t("RUN ARCHIVE")}</p><h2>{t("Recent simulations")}</h2></div>
            <button className="text-button" type="button" onClick={refreshHistory}>{t("Refresh")}</button>
          </div>
          <div className="history-filters">
            <label><span>{t("Network")}</span><select value={historyFilters.networkId} onChange={(event) => updateHistoryFilter("networkId", event.target.value)}><option value="all">{t("All networks")}</option>{networks.map((item) => <option value={item.name} key={item.name}>{item.name}</option>)}</select></label>
            <label><span>{t("Run type")}</span><select value={historyFilters.runType} onChange={(event) => updateHistoryFilter("runType", event.target.value)}><option value="all">{t("All run types")}</option><option value="failure">{t("Failure")}</option><option value="manual_recovery">{t("Manual recovery")}</option><option value="optimization">{t("AI recovery")}</option></select></label>
            <label><span>{t("Runtime")}</span><select value={historyFilters.runtimeMode} onChange={(event) => updateHistoryFilter("runtimeMode", event.target.value)}><option value="all">{t("All modes")}</option><option value="real">{t("Real WNTR")}</option><option value="demo">{t("Demo")}</option></select></label>
            <label><span>{t("Archive")}</span><select value={historyFilters.archiveStatus} onChange={(event) => updateHistoryFilter("archiveStatus", event.target.value)}><option value="active">{t("Active runs")}</option><option value="archived">{t("Archived runs")}</option><option value="all">{t("All runs")}</option></select></label>
            <strong>{t("{count} matching runs", { count: history.length })}</strong>
          </div>
          <div className="history-compare-bar">
            <span><strong>{comparisonIds.length}/2</strong> {t("runs selected for comparison")}</span>
            <div><button type="button" onClick={() => { setComparisonIds([]); setComparisonItems(null); }} disabled={!comparisonIds.length}>{t("Clear")}</button><button type="button" onClick={compareHistory} disabled={comparisonIds.length !== 2 || comparisonBusy}>{comparisonBusy ? t("Loading...") : t("Compare selected")}</button></div>
          </div>
          {history.length ? (
            <div className="history-table">
              <div className="history-row history-row--head"><span>{t("Run")}</span><span>{t("Pipe")}</span><span>{t("Mode")}</span><span>{t("Result")}</span><span>{t("Created")}</span><span>{t("Actions")}</span></div>
              {history.map((item) => (
                <div className={item.archived ? "history-row history-row--archived" : "history-row"} key={item.run_id}>
                  <strong>{t(RUN_LABELS[item.run_type] || item.run_type)}</strong>
                  <span>{item.pipe_id || "-"}</span>
                  <span className={`mode-tag mode-tag--${item.runtime_mode}`}>{runtimeLabel(t, item.runtime_mode)}</span>
                  <span>{item.summary.score != null ? t("Score {score}", { score: fixed(item.summary.score, 1) }) : t("{count} affected", { count: item.summary.maximum_affected_nodes ?? 0 })}</span>
                  <span>{new Date(item.created_at).toLocaleString(locale)}</span>
                  <span className="export-links"><button className={comparisonIds.includes(item.run_id) ? "compare-toggle compare-toggle--active" : "compare-toggle"} type="button" onClick={() => toggleHistoryComparison(item.run_id)}>{comparisonIds.includes(item.run_id) ? t("Selected") : t("Compare")}</button><button type="button" onClick={() => openHistory(item.run_id)} disabled={historyBusy === item.run_id}>{historyBusy === item.run_id ? "..." : t("View")}</button><button className="archive-toggle" type="button" onClick={() => updateHistoryArchive(item)} disabled={historyBusy === item.run_id}>{item.archived ? t("Restore") : t("Archive")}</button><a href={historyDownloadUrl(item.run_id, "html")} target="_blank" rel="noreferrer">{t("Report")}</a><a href={historyDownloadUrl(item.run_id, "json")}>JSON</a><a href={historyDownloadUrl(item.run_id, "csv")}>CSV</a></span>
                </div>
              ))}
            </div>
          ) : <p className="empty-state history-empty">{t("No saved runs match the current filters.")}</p>}
        </section>
      </main>
      {selectedHistory && <HistoryDetail item={selectedHistory} onClose={() => setSelectedHistory(null)} reportUrl={historyDownloadUrl(selectedHistory.run_id, "html")} jsonUrl={historyDownloadUrl(selectedHistory.run_id, "json")} csvUrl={historyDownloadUrl(selectedHistory.run_id, "csv")} />}
      {comparisonItems && <HistoryComparison items={comparisonItems} onClose={() => setComparisonItems(null)} />}
    </div>
  );
}

export default App;
