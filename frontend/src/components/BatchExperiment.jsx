import { useEffect, useMemo, useState } from "react";
import { experimentDownloadUrl, startBatchExperiment, waitForBatchExperiment } from "../api/client";


const parseNumbers = (value) => value.split(",").map((item) => Number(item.trim())).filter(Number.isFinite);
const fixed = (value, digits = 2) => value == null ? "--" : Number(value).toFixed(digits);


function BatchExperiment({ networkId, pipes, runtimeMode }) {
  const [selectedPipes, setSelectedPipes] = useState([]);
  const [leakAreas, setLeakAreas] = useState("0.0003, 0.0007");
  const [seeds, setSeeds] = useState("7, 42, 101");
  const [job, setJob] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const busy = job && !["completed", "failed"].includes(job.status);

  useEffect(() => {
    setSelectedPipes(pipes.slice(0, 4).map((pipe) => pipe.id));
    setJob(null);
    setResult(null);
  }, [networkId, pipes]);

  const totalRuns = useMemo(() => {
    const areaCount = parseNumbers(leakAreas).length;
    const seedCount = parseNumbers(seeds).length;
    return selectedPipes.length * areaCount * (2 + seedCount);
  }, [leakAreas, seeds, selectedPipes]);

  const togglePipe = (pipeId) => setSelectedPipes((current) => {
    if (current.includes(pipeId)) return current.filter((item) => item !== pipeId);
    return current.length < 12 ? [...current, pipeId] : current;
  });

  const run = async () => {
    const areas = parseNumbers(leakAreas);
    const experimentSeeds = parseNumbers(seeds).map(Math.trunc);
    if (!selectedPipes.length || !areas.length || !experimentSeeds.length) {
      setError("Select at least one pipe and enter valid leak areas and seeds.");
      return;
    }
    setError("");
    setResult(null);
    try {
      const created = await startBatchExperiment({
        network_id: networkId,
        pipe_ids: selectedPipes,
        leak_areas: areas,
        seeds: experimentSeeds,
      });
      setJob(created);
      setResult(await waitForBatchExperiment(created.job_id, setJob));
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const ga = result?.summary?.genetic_algorithm || {};
  const exhaustive = result?.summary?.exhaustive_search || {};

  return (
    <section className="panel experiment-panel" id="experiments">
      <div className="panel-heading experiment-heading">
        <div><p className="section-label">BATCH EXPERIMENTS</p><h2>Reproducible benchmark runner</h2></div>
        <span className={`mode-tag mode-tag--${runtimeMode}`}>{runtimeMode || "loading"}</span>
      </div>
      {runtimeMode === "demo" && <p className="experiment-warning">Demo runs use synthetic values for interface testing only. Rerun in Real mode before using results in the report.</p>}

      <div className="experiment-form">
        <div className="experiment-pipes">
          <span className="field-label">Failure pipes (maximum 12)</span>
          <div className="pipe-options">{pipes.map((pipe) => (
            <button className={selectedPipes.includes(pipe.id) ? "pipe-chip pipe-chip--active" : "pipe-chip"} type="button" key={pipe.id} onClick={() => togglePipe(pipe.id)} disabled={busy}>{pipe.id}</button>
          ))}</div>
        </div>
        <label><span className="field-label">Leak areas (m³, comma-separated)</span><input value={leakAreas} onChange={(event) => setLeakAreas(event.target.value)} disabled={busy} /></label>
        <label><span className="field-label">GA seeds (comma-separated)</span><input value={seeds} onChange={(event) => setSeeds(event.target.value)} disabled={busy} /></label>
      </div>

      <div className="experiment-runbar">
        <div><strong>{totalRuns}</strong><span>method runs across {selectedPipes.length * parseNumbers(leakAreas).length} scenarios</span></div>
        <button className="primary-button" type="button" onClick={run} disabled={busy || !selectedPipes.length}>{busy ? "Running benchmark..." : "Start batch experiment"}</button>
      </div>
      {error && <p className="experiment-error">{error}</p>}
      {job && <div className="experiment-progress"><div><span>{job.progress?.message || job.status}</span><strong>{fixed(job.progress?.percent, 0)}%</strong></div><progress max="100" value={job.progress?.percent || 0} /></div>}

      {result && <div className="experiment-result">
        <div><span>Scenarios</span><strong>{result.configuration.scenario_count}</strong></div>
        <div><span>GA mean score</span><strong>{fixed(ga.mean_score)}</strong></div>
        <div><span>Optimum hit rate</span><strong>{ga.global_optimum_hit_rate == null ? "--" : `${fixed(ga.global_optimum_hit_rate * 100, 1)}%`}</strong></div>
        <div><span>Exhaustive mean time</span><strong>{fixed(exhaustive.mean_computation_time_seconds, 3)}s</strong></div>
        <div className="experiment-downloads"><a href={experimentDownloadUrl(job.job_id, "csv")}>Download CSV</a><a href={experimentDownloadUrl(job.job_id, "json")}>Download JSON</a></div>
      </div>}
    </section>
  );
}


export default BatchExperiment;
