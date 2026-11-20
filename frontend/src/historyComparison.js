export const COMPARISON_METRICS = [
  { key: "score", label: "Decision score", direction: "higher", digits: 2, suffix: "" },
  { key: "service", label: "Service availability", direction: "higher", digits: 1, suffix: "%" },
  { key: "violations", label: "Pressure violations", direction: "lower", digits: 0, suffix: "" },
  { key: "affected", label: "Affected nodes", direction: "lower", digits: 0, suffix: "" },
  { key: "leakage", label: "Leakage volume", direction: "lower", digits: 2, suffix: " m³" },
];


export function extractRunOutcome(item) {
  const result = item?.result || {};
  const candidate = result.best_candidate || {};
  const summary = item?.run_type === "manual_recovery"
    ? result.recovery?.summary
    : item?.run_type === "optimization"
      ? candidate.summary
      : result.summary;
  const effective = summary || item?.summary || {};

  return {
    score: candidate.score ?? effective.score ?? item?.summary?.score ?? null,
    service: effective.minimum_service_availability == null
      ? null
      : Number(effective.minimum_service_availability) * 100,
    violations: effective.maximum_pressure_violations ?? null,
    affected: effective.maximum_affected_nodes ?? null,
    leakage: effective.total_leakage_volume ?? null,
    actions: result.actions || candidate.actions || [],
  };
}


export function metricWinner(firstValue, secondValue, direction) {
  if (firstValue == null || secondValue == null || Number(firstValue) === Number(secondValue)) return null;
  const firstWins = direction === "higher"
    ? Number(firstValue) > Number(secondValue)
    : Number(firstValue) < Number(secondValue);
  return firstWins ? "first" : "second";
}


export function formatComparisonValue(value, metric) {
  if (value == null) return "-";
  return `${Number(value).toFixed(metric.digits)}${metric.suffix}`;
}
