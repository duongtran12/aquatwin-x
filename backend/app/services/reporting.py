from __future__ import annotations

from html import escape
from typing import Any


REPORT_STYLE = """
:root { color-scheme: light; font-family: Arial, Helvetica, sans-serif; color: #17333d; }
* { box-sizing: border-box; }
body { margin: 0; background: #edf3f4; }
.report { width: min(1000px, calc(100% - 32px)); margin: 28px auto; background: white; box-shadow: 0 18px 50px rgba(14, 43, 52, .12); }
header { padding: 34px 40px 28px; border-bottom: 5px solid #42cbd0; background: #082630; color: white; }
.eyebrow { margin: 0 0 8px; color: #65dce0; font-size: 11px; font-weight: 700; letter-spacing: .18em; }
h1 { margin: 0; font-size: 28px; }
.subtitle { margin: 8px 0 0; color: #9fbcc3; font-size: 13px; }
main { padding: 30px 40px 42px; }
.warning { margin-bottom: 24px; padding: 13px 16px; border-left: 4px solid #e49a36; background: #fff2db; color: #805415; font-size: 13px; font-weight: 700; }
.meta, .cards, .settings { display: grid; gap: 10px; }
.meta { grid-template-columns: repeat(4, 1fr); margin-bottom: 28px; }
.meta div, .card { padding: 13px; border: 1px solid #d8e4e6; background: #f8fbfb; }
small { display: block; margin-bottom: 5px; color: #6e8a91; font-size: 10px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.meta strong { font-size: 12px; overflow-wrap: anywhere; }
h2 { margin: 28px 0 12px; color: #153b46; font-size: 17px; }
.cards { grid-template-columns: repeat(3, 1fr); }
.card strong { display: block; color: #0b5663; font-size: 21px; }
.card span { display: block; margin-top: 5px; color: #668187; font-size: 11px; }
.settings { grid-template-columns: repeat(4, 1fr); }
.setting { padding: 11px 13px; border: 1px solid #d8e4e6; background: #f8fbfb; }
.setting strong { display: block; color: #174d58; font-size: 13px; overflow-wrap: anywhere; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { padding: 11px 10px; border-bottom: 1px solid #dce7e9; text-align: right; }
th:first-child, td:first-child { text-align: left; }
th { background: #edf6f7; color: #4e6d74; font-size: 10px; letter-spacing: .07em; text-transform: uppercase; }
.actions { display: grid; gap: 8px; }
.action { display: grid; grid-template-columns: 36px 1fr auto; align-items: center; gap: 12px; padding: 12px 14px; border: 1px solid #d9e5e7; }
.action b { display: grid; width: 28px; height: 28px; place-items: center; background: #0b6472; color: white; }
.action span { font-size: 12px; font-weight: 700; }
.action em { color: #668187; font-size: 11px; font-style: normal; }
.empty { padding: 16px; border: 1px dashed #cbdadd; color: #70878c; font-size: 12px; }
footer { padding: 18px 40px; border-top: 1px solid #dce7e9; color: #789096; font-size: 10px; }
@media (max-width: 700px) { .meta, .cards, .settings { grid-template-columns: 1fr 1fr; } main, header { padding-inline: 22px; } }
@media print { body { background: white; } .report { width: 100%; margin: 0; box-shadow: none; } @page { margin: 12mm; } }
"""


def _text(value: Any, fallback: str = "-") -> str:
    return escape(fallback if value is None else str(value))


def _number(value: Any, digits: int = 2, suffix: str = "") -> str:
    if value is None:
        return "-"
    return f"{float(value):.{digits}f}{suffix}"


def _metric_value(name: str, value: Any) -> str:
    if value is None:
        return "-"
    if name == "minimum_service_availability":
        return _number(float(value) * 100, 1, "%")
    if name == "total_leakage_volume":
        return _number(value, 2, " m³")
    return _number(value, 0)


def _delta_value(name: str, failure: Any, recovery: Any) -> str:
    if failure is None or recovery is None:
        return "-"
    if name == "minimum_service_availability":
        return _number((float(recovery) - float(failure)) * 100, 1, " pp")
    if name == "total_leakage_volume":
        return _number(float(failure) - float(recovery), 2, " m³ reduced")
    return _number(float(failure) - float(recovery), 0, " reduced")


def render_history_report(item: dict[str, Any]) -> str:
    result = item.get("result") or {}
    candidate = result.get("best_candidate") or {}
    failure = (
        result.get("summary")
        or result.get("failure", {}).get("summary")
        or result.get("failure_summary")
        or item.get("summary")
        or {}
    )
    recovery = result.get("recovery", {}).get("summary") or candidate.get("summary") or {}
    actions = result.get("actions") or candidate.get("actions") or []
    configuration = result.get("configuration") or result.get("scenario") or {}
    if not isinstance(configuration, dict):
        configuration = {}
    optimization_config = result.get("config") or {}
    if not isinstance(optimization_config, dict):
        optimization_config = {}
    labels = {
        "failure": "Failure simulation",
        "manual_recovery": "Manual recovery evaluation",
        "optimization": "AI recovery recommendation",
    }
    metrics = (
        ("minimum_service_availability", "Service availability"),
        ("maximum_pressure_violations", "Pressure violations"),
        ("maximum_affected_nodes", "Affected nodes"),
        ("total_leakage_volume", "Leakage volume"),
    )
    metric_rows = "".join(
        f"<tr><td>{escape(label)}</td>"
        f"<td>{_metric_value(name, failure.get(name))}</td>"
        f"<td>{_metric_value(name, recovery.get(name))}</td>"
        f"<td>{_delta_value(name, failure.get(name), recovery.get(name))}</td></tr>"
        for name, label in metrics
    )
    action_rows = "".join(
        f'<div class="action"><b>{index:02d}</b>'
        f"<span>{_text(action.get('status'))} {_text(action.get('valve_id'))}</span>"
        f"<em>{_text(action.get('link_id'), 'Mapped isolation valve')}</em></div>"
        for index, action in enumerate(actions, 1)
    ) or '<div class="empty">No valve action was recorded for this run.</div>'
    setting_values = (
        ("Algorithm", result.get("algorithm")),
        ("Population", optimization_config.get("population_size")),
        ("Generations", optimization_config.get("generations")),
        ("Action limit", optimization_config.get("max_actions")),
        ("Random seed", optimization_config.get("seed")),
        ("Crossover rate", optimization_config.get("crossover_rate")),
        ("Mutation rate", optimization_config.get("mutation_rate")),
    )
    setting_rows = "".join(
        f'<div class="setting"><small>{escape(label)}</small><strong>{_text(value)}</strong></div>'
        for label, value in setting_values
        if value is not None
    )
    settings_section = (
        f'<h2>Optimization settings</h2><section class="settings">{setting_rows}</section>'
        if setting_rows
        else ""
    )
    demo_warning = (
        '<div class="warning">Synthetic demo result. Do not use these values as hydraulic or experimental evidence.</div>'
        if item.get("runtime_mode") == "demo"
        else ""
    )
    score = candidate.get("score", item.get("summary", {}).get("score"))
    leak_area = configuration.get("leak_area")
    start_time = configuration.get("start_time")
    end_time = configuration.get("end_time")
    title = labels.get(str(item.get("run_type")), str(item.get("run_type", "Run report")))
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AquaTwin-X | {_text(title)}</title><style>{REPORT_STYLE}</style></head>
<body><article class="report">
<header><p class="eyebrow">AQUATWIN-X DECISION EVIDENCE</p><h1>{_text(title)}</h1>
<p class="subtitle">Water-network incident and recovery report</p></header>
<main>{demo_warning}
<section class="meta">
<div><small>Run ID</small><strong>{_text(item.get('run_id'))}</strong></div>
<div><small>Network</small><strong>{_text(item.get('network_id'))}</strong></div>
<div><small>Failed pipe</small><strong>{_text(item.get('pipe_id'))}</strong></div>
<div><small>Created (UTC)</small><strong>{_text(item.get('created_at'))}</strong></div>
</section>
<h2>Scenario and outcome</h2><section class="cards">
<div class="card"><small>Runtime</small><strong>{_text(item.get('runtime_mode')).upper()}</strong><span>Execution provenance</span></div>
<div class="card"><small>Leak area</small><strong>{_number(leak_area, 6, ' m²')}</strong><span>Configured incident size</span></div>
<div class="card"><small>Incident window</small><strong>{_number(float(start_time) / 3600, 1, 'h') if start_time is not None else '-'} - {_number(float(end_time) / 3600, 1, 'h') if end_time is not None else '-'}</strong><span>Simulation interval</span></div>
<div class="card"><small>Best score</small><strong>{_number(score, 2)}</strong><span>Recovery objective / 100</span></div>
<div class="card"><small>Actions</small><strong>{len(actions)}</strong><span>Recommended valve operations</span></div>
<div class="card"><small>Result type</small><strong>{_text(item.get('run_type'))}</strong><span>Archived immutable run</span></div>
</section>
{settings_section}
<h2>KPI comparison</h2><table><thead><tr><th>Indicator</th><th>Failure</th><th>Recovery</th><th>Improvement</th></tr></thead>
<tbody>{metric_rows}</tbody></table>
<h2>Control actions</h2><section class="actions">{action_rows}</section>
</main><footer>Generated from the archived AquaTwin-X run. Verify runtime mode and input provenance before operational use.</footer>
</article></body></html>"""
