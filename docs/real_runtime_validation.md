# Real WNTR Runtime Validation

AquaTwin-X uses GitHub Actions on Ubuntu as the reproducible reference environment for real hydraulic evidence. This avoids Windows Application Control blocking WNTR's unsigned native `.pyd` modules.

## Automatic validation

The workflow `.github/workflows/ci.yml` runs on every push and pull request to `main`. It performs the following checks:

1. Installs Python 3.12 and the pinned backend dependency ranges.
2. Requires `AQUATWIN_RUNTIME_MODE=real`.
3. Confirms that WNTR is available and synthetic fallback is disabled.
4. Runs the complete Python test suite.
5. Executes real baseline, pipe-leak and manual-recovery hydraulic simulations.
6. Validates the generated KPI data.
7. Runs a bounded two-scenario GA-versus-exhaustive benchmark in real WNTR.
8. Uploads hydraulic smoke JSON and benchmark JSON, CSV and Markdown evidence as 30-day artifacts.
9. Builds the React frontend independently on Node.js 22.

## Evidence boundary

A green `backend-real-runtime` job proves that WNTR loaded and executed on Linux. Only files produced by a real runtime may be used as hydraulic evidence. Demo-mode history remains suitable only for UI demonstrations.

## Downloading results

Open the repository on GitHub, select **Actions**, open the latest successful **AquaTwin-X CI** run, and download the `real-wntr-smoke-<commit>` artifact from the run summary.

The same run also publishes `real-wntr-benchmark-<commit>`. It is a small continuous-validation matrix, not the final experimental dataset.

## Full experimental benchmark

Open **Actions > AquaTwin-X Full Benchmark > Run workflow** and choose:

- `demo`: the complete six-pipe demonstration matrix.
- `extended`: the seven-pipe matrix on the 12-junction benchmark network.

The workflow requires real WNTR, validates every evidence file and retains the downloadable artifact for 90 days. Use the full artifact, rather than demo-mode dashboard values, for experimental tables and conclusions.
