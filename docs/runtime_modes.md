# AquaTwin-X Runtime Modes

AquaTwin-X separates the presentation runtime from scientific experiments. Demo results are synthetic and must never be included in benchmark tables or conclusions.

## Modes

| Mode | Behavior | Intended use |
|---|---|---|
| `auto` | Run WNTR when available; otherwise fall back to labeled demo data | Local development and presentation |
| `real` | Require WNTR; return an error if its native dependencies cannot load | Experiments and final validation |
| `demo` | Always use deterministic synthetic results | UI demonstration only |

The default mode is `auto`. To select a mode, copy `.env.example` to `.env` and change:

```env
AQUATWIN_RUNTIME_MODE=auto
```

Restart the FastAPI backend after changing the value.

## Safety boundary

Every demo response contains:

```json
{
  "runtime": {
    "mode": "demo",
    "synthetic_data": true,
    "warning": "Synthetic demo data ..."
  }
}
```

The dashboard also displays a visible `DEMO MODE` warning. The experiment runner in `experiments/` does not use this fallback and continues to require a working WNTR installation.

## Recommended commands

Presentation on the current Windows machine:

```powershell
$env:AQUATWIN_RUNTIME_MODE="auto"
python -m uvicorn backend.app.main:app --reload
```

Scientific benchmark on a WNTR-compatible environment:

```powershell
$env:AQUATWIN_RUNTIME_MODE="real"
python -m experiments.cli
```
