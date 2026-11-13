const METRICS = [
  { key: "minimum_service_availability", label: "Service availability", format: (value) => `${((value || 0) * 100).toFixed(1)}%`, better: "higher" },
  { key: "maximum_pressure_violations", label: "Pressure violations", format: (value) => String(value ?? 0), better: "lower" },
  { key: "maximum_affected_nodes", label: "Affected nodes", format: (value) => String(value ?? 0), better: "lower" },
  { key: "total_leakage_volume", label: "Leakage volume", format: (value) => `${(value || 0).toFixed(2)} m³`, better: "lower" },
];

function MetricComparison({ failure, recovery }) {
  if (!failure) return <p className="empty-state">Run a failure scenario to view its impact.</p>;
  return (
    <div className="metric-table">
      <div className="metric-row metric-row--head"><span>Metric</span><span>Failure</span><span>Recovery</span></div>
      {METRICS.map((metric) => {
        const before = failure[metric.key];
        const after = recovery?.[metric.key];
        const improved = recovery && (metric.better === "higher" ? after > before : after < before);
        return (
          <div className="metric-row" key={metric.key}>
            <span>{metric.label}</span><strong>{metric.format(before)}</strong>
            <strong className={improved ? "metric-good" : ""}>{recovery ? metric.format(after) : "-"}</strong>
          </div>
        );
      })}
    </div>
  );
}

export default MetricComparison;
