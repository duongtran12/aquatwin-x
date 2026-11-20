# Run History and Export

AquaTwin-X stores dashboard runs in a local SQLite database at `data/aquatwin_history.db`. The database is generated at runtime and is excluded from Git.

## Recorded run types

- `failure`: pipe leak impact simulation.
- `manual_recovery`: user-selected valve actions.
- `optimization`: AI recovery result.

Each record contains the network and pipe identifiers, creation time, runtime mode, KPI summary and complete API result. The runtime mode remains visible so demo data cannot be mistaken for real WNTR output.

## API

```text
GET /api/history?limit=20
GET /api/history?network_id=aquatwin_demo&run_type=optimization&runtime_mode=real
GET /api/history?archive=archived
GET /api/history/{run_id}
PATCH /api/history/{run_id}/archive
PATCH /api/history/{run_id}/restore
GET /api/history/{run_id}/download?format=json
GET /api/history/{run_id}/download?format=csv
GET /api/history/{run_id}/download?format=html
```

Archive filters can be combined and are also available in the dashboard. Archiving is reversible and never deletes result evidence; archived runs are excluded from analytics by default. JSON exports include the complete result, CSV exports contain metadata and main KPI fields for spreadsheet analysis, and HTML opens a printable decision report.
