import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";


const fixed = (value, digits = 1) => value == null ? "--" : Number(value).toFixed(digits);


function ChartTooltip({ active, payload, label, suffix = "" }) {
  if (!active || !payload?.length) return null;
  return <div className="analytics-tooltip"><strong>{label}</strong><span>{fixed(payload[0].value, 2)}{suffix}</span></div>;
}


function ExperimentAnalytics({ analytics, mode, onModeChange, loading }) {
  const scoreTimeline = (analytics?.timeline || [])
    .filter((item) => item.score != null)
    .map((item, index) => ({ ...item, order: index + 1 }));
  const recovery = analytics?.recovery || {};
  const optimization = analytics?.optimization || {};

  return (
    <section className="panel analytics-panel" id="analytics">
      <div className="panel-heading analytics-heading">
        <div><p className="section-label">EXPERIMENT ANALYTICS</p><h2>Performance overview</h2></div>
        <div className="mode-filter" aria-label="Runtime data filter">
          {["all", "demo", "real"].map((value) => <button className={mode === value ? "mode-filter__active" : ""} type="button" key={value} onClick={() => onModeChange(value)}>{value}</button>)}
        </div>
      </div>

      {loading ? <p className="analytics-empty">Loading analytics...</p> : analytics?.total_runs ? (
        <>
          <div className="analytics-kpis">
            <div><span>Total runs</span><strong>{analytics.total_runs}</strong><small>{analytics.runtime_counts.real || 0} real · {analytics.runtime_counts.demo || 0} demo</small></div>
            <div><span>Best GA score</span><strong>{fixed(optimization.best_score)}</strong><small>{optimization.run_count || 0} optimization runs</small></div>
            <div><span>Average leakage reduced</span><strong>{fixed(recovery.average_leakage_reduction, 2)}</strong><small>m³ across recovery runs</small></div>
            <div><span>Average service gain</span><strong>{recovery.average_service_gain == null ? "--" : `${fixed(recovery.average_service_gain * 100, 2)}%`}</strong><small>{recovery.run_count || 0} comparable runs</small></div>
          </div>

          <div className="analytics-charts">
            <div className="analytics-chart-card">
              <div><p className="section-label">PIPE IMPACT</p><h3>Average affected nodes</h3></div>
              <div className="analytics-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={analytics.by_pipe} margin={{ top: 12, right: 8, left: -25, bottom: 0 }}>
                    <CartesianGrid stroke="#183946" strokeDasharray="4 4" vertical={false} />
                    <XAxis dataKey="pipe_id" stroke="#7696a3" fontSize={11} />
                    <YAxis stroke="#7696a3" fontSize={11} allowDecimals={false} />
                    <Tooltip content={<ChartTooltip />} />
                    <Bar dataKey="average_affected_nodes" fill="#54cfd4" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="analytics-chart-card">
              <div><p className="section-label">GA QUALITY</p><h3>Optimization score history</h3></div>
              {scoreTimeline.length ? <div className="analytics-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={scoreTimeline} margin={{ top: 12, right: 12, left: -20, bottom: 0 }}>
                    <CartesianGrid stroke="#183946" strokeDasharray="4 4" />
                    <XAxis dataKey="order" stroke="#7696a3" fontSize={11} />
                    <YAxis domain={[0, 100]} stroke="#7696a3" fontSize={11} />
                    <Tooltip content={<ChartTooltip suffix=" pts" />} />
                    <Line type="monotone" dataKey="score" stroke="#ffba61" strokeWidth={3} dot={{ r: 3, fill: "#ffba61" }} />
                  </LineChart>
                </ResponsiveContainer>
              </div> : <p className="analytics-chart-empty">Run AI Recovery to create the first score point.</p>}
            </div>
          </div>
        </>
      ) : <p className="analytics-empty">No {mode === "all" ? "" : `${mode} `}runs available. Complete a simulation to populate analytics.</p>}
    </section>
  );
}


export default ExperimentAnalytics;
