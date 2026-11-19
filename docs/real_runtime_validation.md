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
7. Uploads the three JSON outputs as a 30-day GitHub Actions artifact.
8. Builds the React frontend independently on Node.js 22.

## Evidence boundary

A green `backend-real-runtime` job proves that WNTR loaded and executed on Linux. Only files produced by a real runtime may be used as hydraulic evidence. Demo-mode history remains suitable only for UI demonstrations.

## Downloading results

Open the repository on GitHub, select **Actions**, open the latest successful **AquaTwin-X CI** run, and download the `real-wntr-smoke-<commit>` artifact from the run summary.
