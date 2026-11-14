import { useEffect } from "react";
import MetricComparison from "./MetricComparison";


const RUN_LABELS = {
  failure: "Failure simulation",
  manual_recovery: "Manual recovery",
  optimization: "AI recovery",
};


function HistoryDetail({ item, onClose, jsonUrl, csvUrl }) {
  useEffect(() => {
    const closeOnEscape = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  if (!item) return null;
  const result = item.result || {};
  const candidate = result.best_candidate || {};
  const failure = result.summary || result.failure?.summary || result.failure_summary;
  const recovery = result.recovery?.summary || candidate.summary;
  const actions = result.actions || candidate.actions || [];
  const configuration = result.configuration || result.scenario || {};

  return (
    <div className="detail-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="detail-dialog" role="dialog" aria-modal="true" aria-labelledby="history-detail-title">
        <div className="detail-heading">
          <div>
            <p className="section-label">RUN DETAIL</p>
            <h2 id="history-detail-title">{RUN_LABELS[item.run_type] || item.run_type}</h2>
          </div>
          <button className="close-button" type="button" onClick={onClose} aria-label="Close detail">×</button>
        </div>

        <div className="detail-meta">
          <span><small>Run ID</small>{item.run_id.slice(0, 12)}</span>
          <span><small>Pipe</small>{item.pipe_id || "-"}</span>
          <span><small>Runtime</small><b className={`mode-tag mode-tag--${item.runtime_mode}`}>{item.runtime_mode}</b></span>
          <span><small>Created</small>{new Date(item.created_at).toLocaleString("vi-VN")}</span>
        </div>

        {item.runtime_mode === "demo" && <div className="detail-warning">Synthetic preview result — do not use this run as experimental evidence.</div>}

        <div className="detail-grid">
          <div><small>Leak area</small><strong>{configuration.leak_area != null ? `${configuration.leak_area} m²` : "-"}</strong></div>
          <div><small>Start</small><strong>{configuration.start_time != null ? `${configuration.start_time / 3600}h` : "-"}</strong></div>
          <div><small>End</small><strong>{configuration.end_time != null ? `${configuration.end_time / 3600}h` : "-"}</strong></div>
          <div><small>Best score</small><strong>{candidate.score != null ? Number(candidate.score).toFixed(2) : "-"}</strong></div>
        </div>

        <div className="detail-section">
          <p className="section-label">KPI COMPARISON</p>
          <MetricComparison failure={failure} recovery={recovery} />
        </div>

        <div className="detail-section">
          <p className="section-label">CONTROL ACTIONS</p>
          {actions.length ? <div className="detail-actions">{actions.map((action, index) => <span key={`${action.valve_id}-${index}`}>{action.status} {action.valve_id}</span>)}</div> : <p className="detail-empty">No valve action in this run.</p>}
        </div>

        <div className="detail-footer">
          <a className="secondary-button detail-download" href={jsonUrl}>Download JSON</a>
          <a className="secondary-button detail-download" href={csvUrl}>Download CSV</a>
          <button className="primary-button detail-close" type="button" onClick={onClose}>Close</button>
        </div>
      </section>
    </div>
  );
}


export default HistoryDetail;
