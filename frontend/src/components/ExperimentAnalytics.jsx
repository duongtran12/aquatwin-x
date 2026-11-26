import { useLanguage, runtimeLabel } from "../language";
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
  const { t } = useLanguage();
  const scoreTimeline = (analytics?.timeline || [])
    .filter((item) => item.score != null)
    .map((item, index) => ({ ...item, order: index + 1 }));
  const recovery = analytics?.recovery || {};
  const optimization = analytics?.optimization || {};

  return (
    <section className="panel analytics-panel" id="analytics">
      <div className="panel-heading analytics-heading">
        <div><p className="section-label">{t("EXPERIMENT ANALYTICS")}</p><h2>{t("Performance overview")}</h2></div>
        <div className="mode-filter" aria-label={t("Runtime data filter")}>
          {["all", "demo", "real"].map((value) => <button className={mode === value ? "mode-filter__active" : ""} type="button" key={value} onClick={() => onModeChange(value)}>{runtimeLabel(t, value)}</button>)}
        </div>
      </div>

      {loading ? <p className="analytics-empty">{t("Loading analytics...")}</p> : analytics?.total_runs ? (
        <>
          <div className="analytics-kpis">
            <div><span>{t("Total runs")}</span><strong>{analytics.total_runs}</strong><small>{t("{real} real · {demo} demo", { real: analytics.runtime_counts.real || 0, demo: analytics.runtime_counts.demo || 0 })}</small></div>
            <div><span>{t("Best GA score")}</span><strong>{fixed(optimization.best_score)}</strong><small>{t("{count} optimization runs", { count: optimization.run_count || 0 })}</small></div>
            <div><span>{t("Average leakage reduced")}</span><strong>{fixed(recovery.average_leakage_reduction, 2)}</strong><small>{t("m³ across recovery runs")}</small></div>
            <div><span>{t("Average service gain")}</span><strong>{recovery.average_service_gain == null ? "--" : `${fixed(recovery.average_service_gain * 100, 2)}%`}</strong><small>{t("{count} comparable runs", { count: recovery.run_count || 0 })}</small></div>
          </div>

          <div className="analytics-charts">
            <div className="analytics-chart-card">
              <div><p className="section-label">{t("PIPE IMPACT")}</p><h3>{t("Average affected nodes")}</h3></div>
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
              <div><p className="section-label">{t("GA QUALITY")}</p><h3>{t("Optimization score history")}</h3></div>
              {scoreTimeline.length ? <div className="analytics-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={scoreTimeline} margin={{ top: 12, right: 12, left: -20, bottom: 0 }}>
                    <CartesianGrid stroke="#183946" strokeDasharray="4 4" />
                    <XAxis dataKey="order" stroke="#7696a3" fontSize={11} />
                    <YAxis domain={[0, 100]} stroke="#7696a3" fontSize={11} />
                    <Tooltip content={<ChartTooltip suffix={` ${t("points")}`} />} />
                    <Line type="monotone" dataKey="score" stroke="#ffba61" strokeWidth={3} dot={{ r: 3, fill: "#ffba61" }} />
                  </LineChart>
                </ResponsiveContainer>
              </div> : <p className="analytics-chart-empty">{t("Run AI Recovery to create the first score point.")}</p>}
            </div>
          </div>
        </>
      ) : <p className="analytics-empty">{t(mode === "all" ? "No runs available. Complete a simulation to populate analytics." : "No runs for this mode. Complete a simulation in this mode to populate analytics.")}</p>}
    </section>
  );
}


export default ExperimentAnalytics;
