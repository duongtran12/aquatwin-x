import { useCallback, useEffect, useMemo, useState } from "react";
import { getHistory, getNetwork, historyDownloadUrl, simulateFailure, simulateWhatIf, startOptimization, waitForOptimization } from "./api/client";
import FitnessChart from "./components/FitnessChart";
import KpiCard from "./components/KpiCard";
import MetricComparison from "./components/MetricComparison";
import NetworkMap from "./components/NetworkMap";

const NETWORK_ID = "aquatwin_demo";
const fixed = (value, digits = 2) => Number(value || 0).toFixed(digits);
const RUN_LABELS = { failure: "Failure", manual_recovery: "Manual recovery", optimization: "AI recovery" };

function App() {
  const [network, setNetwork] = useState(null);
  const [selectedPipe, setSelectedPipe] = useState("P3");
  const [selectedValves, setSelectedValves] = useState([]);
  const [scenario, setScenario] = useState({ leakArea: 0.0005, startHour: 2, endHour: 12 });
  const [failureResult, setFailureResult] = useState(null);
  const [manualResult, setManualResult] = useState(null);
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState("");
  const [jobStatus, setJobStatus] = useState("");
  const [error, setError] = useState("");

  const refreshHistory = useCallback(() => (
    getHistory().then(setHistory).catch((requestError) => setError(requestError.message))
  ), []);

  useEffect(() => {
    getNetwork(NETWORK_ID).then(setNetwork).catch((requestError) => setError(requestError.message));
    refreshHistory();
  }, [refreshHistory]);

  useEffect(() => {
    if (!network) return;
    setSelectedValves(network.valves.filter((valve) => valve.link_id === selectedPipe).map((valve) => valve.valve_id));
  }, [network, selectedPipe]);

  useEffect(() => {
    setFailureResult(null);
    setManualResult(null);
    setOptimizationResult(null);
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

  const execute = async (taskName, action) => {
    setBusy(taskName);
    setError("");
    try { await action(); } catch (requestError) { setError(requestError.message); } finally { setBusy(""); }
  };

  const runFailure = () => execute("failure", async () => {
    setFailureResult(await simulateFailure(NETWORK_ID, scenarioPayload()));
    setManualResult(null);
    setOptimizationResult(null);
    await refreshHistory();
  });

  const runManualRecovery = () => execute("manual", async () => {
    setManualResult(await simulateWhatIf(
      NETWORK_ID,
      scenarioPayload(),
      selectedValves.map((valveId) => ({ valve_id: valveId, status: "CLOSED" })),
    ));
    setOptimizationResult(null);
    await refreshHistory();
  });

  const runAiRecovery = () => execute("optimization", async () => {
    setJobStatus("queued");
    const job = await startOptimization(NETWORK_ID, scenarioPayload());
    setOptimizationResult(await waitForOptimization(job.job_id, setJobStatus));
    setManualResult(null);
    setJobStatus("completed");
    await refreshHistory();
  });

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

  const toggleValve = (valveId) => setSelectedValves((current) => (
    current.includes(valveId) ? current.filter((item) => item !== valveId) : [...current, valveId]
  ));

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <a className="brand" href="#overview"><span className="brand-mark">AX</span><span><strong>AquaTwin</strong><small>Decision system</small></span></a>
        <nav>
          <a className="nav-link nav-link--active" href="#overview"><span>01</span>Overview</a>
          <a className="nav-link" href="#scenario"><span>02</span>Scenario</a>
          <a className="nav-link" href="#impact"><span>03</span>Impact</a>
          <a className="nav-link" href="#recovery"><span>04</span>Recovery</a>
          <a className="nav-link" href="#history"><span>05</span>History</a>
        </nav>
        <div className={demoMode ? "sidebar-note sidebar-note--demo" : "sidebar-note"}><span className="status-dot" /><div><strong>{demoMode ? "Demo twin active" : "Digital twin online"}</strong><small>{demoMode ? "Synthetic preview data" : "WNTR / PDD model"}</small></div></div>
      </aside>

      <main className="dashboard">
        <header className="topbar" id="overview">
          <div><p className="eyebrow">WATER NETWORK OPERATIONS</p><h1>Resilience control room</h1></div>
          <div className="network-badge"><span>Active network · {runtime?.effective_mode || "loading"}</span><strong>{network?.network?.name || "Loading..."}</strong></div>
        </header>
        {demoMode && <div className="runtime-notice"><strong>DEMO MODE</strong><span>Synthetic preview data is active because WNTR is blocked. These values must not be used in the experimental report.</span></div>}
        {error && <div className="alert"><strong>Request failed</strong><span>{error}</span></div>}

        <section className="overview-grid">
          <article className="panel map-panel">
            <div className="panel-heading"><div><p className="section-label">LIVE TOPOLOGY</p><h2>Distribution network</h2></div><div className="legend"><span className="legend-normal" />Normal <span className="legend-impact" />Affected</div></div>
            {network ? <NetworkMap elements={network.elements} selectedPipe={selectedPipe} nodeStates={nodeStates} onSelectPipe={setSelectedPipe} /> : <div className="loading-block">Loading network model...</div>}
            <div className="map-footer">
              <span><strong>{nodeCount}</strong> nodes</span><span><strong>{network?.network?.pipes || 0}</strong> pipes</span><span><strong>{network?.valves?.length || 0}</strong> virtual valves</span><span className="map-tip">Select a pipe to define the incident</span>
            </div>
          </article>

          <article className="panel scenario-panel" id="scenario">
            <div className="panel-heading"><div><p className="section-label">SCENARIO BUILDER</p><h2>Pipe leak</h2></div><span className="incident-pill">Selected: {selectedPipe}</span></div>
            <label className="field-label" htmlFor="pipe">Failure pipe</label>
            <select id="pipe" value={selectedPipe} onChange={(event) => setSelectedPipe(event.target.value)}>{(network?.elements?.links || []).map((link) => <option key={link.id}>{link.id}</option>)}</select>
            <label className="field-label" htmlFor="area">Leak area (m²)</label>
            <input id="area" type="number" min="0.0001" step="0.0001" value={scenario.leakArea} onChange={(event) => setScenario({ ...scenario, leakArea: event.target.value })} />
            <div className="two-fields">
              <div><label className="field-label" htmlFor="start">Start (hour)</label><input id="start" type="number" min="0" max="23" value={scenario.startHour} onChange={(event) => setScenario({ ...scenario, startHour: event.target.value })} /></div>
              <div><label className="field-label" htmlFor="end">End (hour)</label><input id="end" type="number" min="1" max="24" value={scenario.endHour} onChange={(event) => setScenario({ ...scenario, endHour: event.target.value })} /></div>
            </div>
            <div className="scenario-summary"><span>Duration</span><strong>{Math.max(0, Number(scenario.endHour) - Number(scenario.startHour))} hours</strong></div>
            <button className="primary-button" type="button" disabled={Boolean(busy) || !network} onClick={runFailure}>{busy === "failure" ? "Simulating..." : "Run failure simulation"}</button>
          </article>
        </section>

        <section id="impact">
          <div className="section-heading"><div><p className="section-label">IMPACT ANALYSIS</p><h2>Worst-state indicators</h2></div><span>{worstStep ? `Snapshot at ${worstStep.time_seconds / 3600}h` : "Awaiting simulation"}</span></div>
          <div className="kpi-grid">
            <KpiCard label="Service availability" value={failureSummary ? `${fixed(failureSummary.minimum_service_availability * 100, 1)}%` : "--"} detail="Minimum during incident" tone="cyan" />
            <KpiCard label="Pressure violations" value={failureSummary?.maximum_pressure_violations ?? "--"} detail="Nodes below requirement" tone="amber" />
            <KpiCard label="Affected nodes" value={failureSummary?.maximum_affected_nodes ?? "--"} detail="Pressure loss ≥ 2 m" tone="red" />
            <KpiCard label="Leakage volume" value={failureSummary ? `${fixed(failureSummary.total_leakage_volume)} m³` : "--"} detail="Integrated over scenario" tone="blue" />
          </div>
        </section>

        <section className="recovery-grid" id="recovery">
          <article className="panel recovery-panel">
            <div className="panel-heading"><div><p className="section-label">WHAT-IF CONTROL</p><h2>Manual isolation</h2></div></div>
            <p className="panel-copy">Choose virtual valves to close, then evaluate service and leakage after isolation.</p>
            <div className="valve-grid">{(network?.valves || []).map((valve) => (
              <label className={selectedValves.includes(valve.valve_id) ? "valve-option valve-option--selected" : "valve-option"} key={valve.valve_id}>
                <input type="checkbox" checked={selectedValves.includes(valve.valve_id)} onChange={() => toggleValve(valve.valve_id)} /><span>{valve.valve_id}<small>{valve.link_id} / {valve.endpoint}</small></span>
              </label>
            ))}</div>
            <button className="secondary-button" type="button" disabled={Boolean(busy) || !failureSummary || selectedValves.length === 0} onClick={runManualRecovery}>{busy === "manual" ? "Evaluating..." : `Evaluate ${selectedValves.length} valve action(s)`}</button>
          </article>

          <article className="panel ai-panel">
            <div className="panel-heading"><div><p className="section-label">AI RECOVERY</p><h2>Genetic optimization</h2></div><span className="ai-badge">GA</span></div>
            <p className="panel-copy">Search up to two valve operations for the best balance of service continuity, pressure and leakage.</p>
            <dl className="algorithm-specs"><div><dt>Population</dt><dd>20</dd></div><div><dt>Generations</dt><dd>20</dd></div><div><dt>Action limit</dt><dd>2</dd></div></dl>
            <button className="primary-button" type="button" disabled={Boolean(busy) || !failureSummary} onClick={runAiRecovery}>{busy === "optimization" ? `Optimizing · ${jobStatus}` : "Find optimal recovery"}</button>
            {optimizationResult?.best_candidate && <div className="best-score"><span>Best solution score</span><strong>{fixed(optimizationResult.best_candidate.score, 1)}</strong><small>{optimizationResult.unique_evaluated_count} unique candidates evaluated</small></div>}
          </article>
        </section>

        <section className="analysis-grid">
          <article className="panel comparison-panel"><div className="panel-heading"><div><p className="section-label">DECISION EVIDENCE</p><h2>Before / after comparison</h2></div></div><MetricComparison failure={failureSummary} recovery={recoverySummary} /></article>
          <article className="panel chart-panel"><div className="panel-heading"><div><p className="section-label">CONVERGENCE</p><h2>GA fitness history</h2></div><div className="chart-legend"><span />Best <span />Average</div></div><FitnessChart history={optimizationResult?.history} /></article>
        </section>

        <section className="panel decision-panel">
          <div><p className="section-label">RECOMMENDED RESPONSE</p><h2>{bestActions.length ? "Recovery plan ready for review" : "Run a recovery analysis to generate a plan"}</h2><p>{bestActions.length ? "The following control actions produced the current recovery indicators." : "AquaTwin-X keeps recommendations explainable by showing every proposed valve operation and its measured impact."}</p></div>
          <div className="action-list">{bestActions.map((action, index) => <div className="action-item" key={`${action.valve_id}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><strong>{action.status === "CLOSED" ? "Close" : "Open"} {action.valve_id}</strong><small>{action.link_id ? `on ${action.link_id}` : "virtual isolation valve"}</small></div>)}</div>
        </section>

        <section className="panel history-panel" id="history">
          <div className="panel-heading">
            <div><p className="section-label">RUN ARCHIVE</p><h2>Recent simulations</h2></div>
            <button className="text-button" type="button" onClick={refreshHistory}>Refresh</button>
          </div>
          {history.length ? (
            <div className="history-table">
              <div className="history-row history-row--head"><span>Run</span><span>Pipe</span><span>Mode</span><span>Result</span><span>Created</span><span>Export</span></div>
              {history.map((item) => (
                <div className="history-row" key={item.run_id}>
                  <strong>{RUN_LABELS[item.run_type] || item.run_type}</strong>
                  <span>{item.pipe_id || "-"}</span>
                  <span className={`mode-tag mode-tag--${item.runtime_mode}`}>{item.runtime_mode}</span>
                  <span>{item.summary.score != null ? `Score ${fixed(item.summary.score, 1)}` : `${item.summary.maximum_affected_nodes ?? 0} affected`}</span>
                  <span>{new Date(item.created_at).toLocaleString("vi-VN")}</span>
                  <span className="export-links"><a href={historyDownloadUrl(item.run_id, "json")}>JSON</a><a href={historyDownloadUrl(item.run_id, "csv")}>CSV</a></span>
                </div>
              ))}
            </div>
          ) : <p className="empty-state history-empty">No saved runs yet. Start a failure simulation to create the first record.</p>}
        </section>
      </main>
    </div>
  );
}

export default App;
