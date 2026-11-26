import { useLanguage } from "../language";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";


const fixed = (value, digits = 2) => value == null ? "--" : Number(value).toFixed(digits);
const percent = (value, digits = 1) => value == null ? "--" : `${fixed(value * 100, digits)}%`;


function ExperimentTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="experiment-report__tooltip">
      <strong>{label}</strong>
      {payload.map((item) => <span key={item.dataKey} style={{ color: item.color }}>{item.name}: {fixed(item.value, 2)}{item.unit || ""}</span>)}
    </div>
  );
}


function ExperimentReport({ result }) {
  const { t } = useLanguage();
  const evaluation = result?.evaluation || {};
  const overall = evaluation.overall || {};
  const scenarios = (evaluation.scenarios || []).map((item) => ({
    ...item,
    scenario_label: item.scenario_id,
    candidate_reduction_percent: item.candidate_reduction_rate == null ? null : item.candidate_reduction_rate * 100,
  }));

  if (!scenarios.length) return null;

  return (
    <div className="experiment-report">
      <div className="experiment-report__heading">
        <div><p className="section-label">{t("DECISION EVIDENCE")}</p><h3>{t("GA benchmark analysis")}</h3></div>
        <span>{t("{count} scenarios", { count: scenarios.length })}</span>
      </div>

      <div className="experiment-report__kpis">
        <div><span>{t("Mean score gap")}</span><strong>{fixed(overall.mean_score_gap)}</strong><small>{t("points from exhaustive")}</small></div>
        <div><span>{t("Maximum gap")}</span><strong>{fixed(overall.maximum_score_gap)}</strong><small>{t("worst GA deviation")}</small></div>
        <div><span>{t("Within 1 point")}</span><strong>{percent(overall.within_one_point_rate)}</strong><small>{t("GA reliability")}</small></div>
        <div><span>{t("Mean speedup")}</span><strong>{overall.mean_speedup == null ? "--" : `${fixed(overall.mean_speedup)}x`}</strong><small>{t("versus exhaustive")}</small></div>
        <div><span>{t("Candidate reduction")}</span><strong>{percent(overall.mean_candidate_reduction_rate)}</strong><small>{t("search-space saving")}</small></div>
      </div>

      <div className="experiment-report__charts">
        <div className="experiment-report__chart-card">
          <div><p className="section-label">{t("SOLUTION QUALITY")}</p><h4>{t("Recovery score comparison")}</h4></div>
          <div className="experiment-report__chart">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={scenarios} margin={{ top: 12, right: 12, left: -18, bottom: 0 }}>
                <CartesianGrid stroke="#183946" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="scenario_label" stroke="#7696a3" fontSize={10} />
                <YAxis domain={[0, 100]} stroke="#7696a3" fontSize={10} />
                <Tooltip content={<ExperimentTooltip />} />
                <Legend wrapperStyle={{ fontSize: "10px" }} />
                <Bar dataKey="baseline_score" name={t("Isolation")} fill="#315f70" radius={[2, 2, 0, 0]} />
                <Bar dataKey="exhaustive_score" name={t("Exhaustive")} fill="#54cfd4" radius={[2, 2, 0, 0]} />
                <Line type="monotone" dataKey="ga_mean_score" name={t("GA mean")} stroke="#ffba61" strokeWidth={3} dot={{ r: 3 }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="experiment-report__chart-card">
          <div><p className="section-label">{t("COMPUTATIONAL EFFICIENCY")}</p><h4>{t("Search reduction and speedup")}</h4></div>
          <div className="experiment-report__chart">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={scenarios} margin={{ top: 12, right: 4, left: -18, bottom: 0 }}>
                <CartesianGrid stroke="#183946" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="scenario_label" stroke="#7696a3" fontSize={10} />
                <YAxis yAxisId="percent" domain={[0, 100]} stroke="#7696a3" fontSize={10} unit="%" />
                <YAxis yAxisId="speed" orientation="right" stroke="#b68b55" fontSize={10} unit="x" />
                <Tooltip content={<ExperimentTooltip />} />
                <Legend wrapperStyle={{ fontSize: "10px" }} />
                <Bar yAxisId="percent" dataKey="candidate_reduction_percent" name={t("Candidate reduction")} unit="%" fill="#54cfd4" radius={[3, 3, 0, 0]} />
                <Line yAxisId="speed" type="monotone" dataKey="ga_speedup" name={t("GA speedup")} unit="x" stroke="#ffba61" strokeWidth={3} dot={{ r: 3 }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="experiment-report__table-wrap">
        <div className="experiment-report__table">
          <div className="experiment-report__row experiment-report__row--head"><span>{t("Scenario")}</span><span>{t("Pipe")}</span><span>{t("Leak area")}</span><span>{t("Exhaustive")}</span><span>{t("GA mean")}</span><span>{t("Gap")}</span><span>{t("Hit rate")}</span><span>{t("Speedup")}</span><span>{t("Reduction")}</span><span>{t("Best seed")}</span></div>
          {scenarios.map((item) => <div className="experiment-report__row" key={item.scenario_id}>
            <strong>{item.scenario_id}</strong>
            <span>{item.pipe_id}</span>
            <span>{fixed(item.leak_area, 6)}</span>
            <span>{fixed(item.exhaustive_score)}</span>
            <span>{fixed(item.ga_mean_score)}</span>
            <span>{fixed(item.ga_mean_score_gap)}</span>
            <span>{percent(item.ga_global_optimum_hit_rate)}</span>
            <span>{item.ga_speedup == null ? "--" : `${fixed(item.ga_speedup)}x`}</span>
            <span>{percent(item.candidate_reduction_rate)}</span>
            <span>{item.ga_best_seed ?? "--"}</span>
          </div>)}
        </div>
      </div>
    </div>
  );
}


export default ExperimentReport;
