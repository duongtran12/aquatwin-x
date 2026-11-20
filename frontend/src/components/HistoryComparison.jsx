import { useEffect } from "react";
import { COMPARISON_METRICS, extractRunOutcome, formatComparisonValue, metricWinner } from "../historyComparison";


const RUN_LABELS = {
  failure: "Failure",
  manual_recovery: "Manual recovery",
  optimization: "AI recovery",
};


function HistoryComparison({ items, onClose }) {
  useEffect(() => {
    const closeOnEscape = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  if (!items || items.length !== 2) return null;
  const [first, second] = items;
  const outcomes = [extractRunOutcome(first), extractRunOutcome(second)];
  const incompatible = first.network_id !== second.network_id || first.runtime_mode !== second.runtime_mode;

  return (
    <div className="detail-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="detail-dialog comparison-dialog" role="dialog" aria-modal="true" aria-labelledby="comparison-title">
        <div className="detail-heading">
          <div><p className="section-label">DECISION COMPARISON</p><h2 id="comparison-title">Run-to-run evidence</h2></div>
          <button className="close-button" type="button" onClick={onClose} aria-label="Close comparison">×</button>
        </div>

        {incompatible && <div className="detail-warning">These runs use different networks or runtime modes. Values are shown for review but should not be treated as a controlled experiment.</div>}

        <div className="comparison-head">
          <span>Metric</span>
          {[first, second].map((item, index) => <div key={item.run_id}><strong>Run {index + 1}</strong><small>{RUN_LABELS[item.run_type] || item.run_type} · {item.pipe_id || "-"} · {item.runtime_mode}</small></div>)}
        </div>

        <div className="comparison-table">
          {COMPARISON_METRICS.map((metric) => {
            const winner = metricWinner(outcomes[0][metric.key], outcomes[1][metric.key], metric.direction);
            return (
              <div className="comparison-row" key={metric.key}>
                <span>{metric.label}<small>{metric.direction === "higher" ? "Higher is better" : "Lower is better"}</small></span>
                <strong className={winner === "first" ? "comparison-best" : ""}>{formatComparisonValue(outcomes[0][metric.key], metric)}</strong>
                <strong className={winner === "second" ? "comparison-best" : ""}>{formatComparisonValue(outcomes[1][metric.key], metric)}</strong>
              </div>
            );
          })}
        </div>

        <div className="comparison-actions">
          {outcomes.map((outcome, index) => <div key={items[index].run_id}><small>Run {index + 1} control actions</small><strong>{outcome.actions.length ? outcome.actions.map((action) => `${action.status} ${action.valve_id}`).join(", ") : "No valve actions"}</strong></div>)}
        </div>

        <button className="primary-button comparison-close" type="button" onClick={onClose}>Close comparison</button>
      </section>
    </div>
  );
}


export default HistoryComparison;
