# Incident and recovery reports

Every archived failure, manual-recovery or optimization run can be opened as a standalone HTML report from **History > Report** or **Run detail > Open report**.

The report contains:

- run, network, pipe, timestamp and runtime provenance;
- a prominent warning when the result uses synthetic demo data;
- incident configuration, objective score and action count;
- failure-versus-recovery KPI comparison and calculated improvement;
- the recommended valve-operation sequence.

Use the browser print dialog and select **Save as PDF** when a PDF copy is required for the project report or presentation. The print stylesheet removes the application background and fits the report to standard pages.

The HTML is generated from the immutable archived run rather than current dashboard state, so exported evidence remains traceable to its run ID. Real WNTR runs should be used for experimental evidence; demo reports are clearly labeled as synthetic previews.

## API

```text
GET /api/history/{run_id}/download?format=html
```

The endpoint returns UTF-8 HTML with `Content-Disposition: inline`. Existing `json` and `csv` formats remain available for machine-readable evidence.
