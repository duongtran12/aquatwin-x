# AquaTwin-X Experiments

This module runs the Week 8 quantitative benchmark. The default configuration contains 12 leak scenarios (six pipes and two leak areas) and evaluates the Genetic Algorithm with three random seeds per scenario.

## Methods compared

- Isolation baseline: close the two virtual valves nearest to the failed pipe.
- Exhaustive search: evaluate every feasible combination with at most two actions.
- Genetic Algorithm: population 20, 20 generations and seeds 7, 42 and 101.

## Run

From the project root:

```powershell
python -m experiments.cli
```

The complete benchmark performs 12 exhaustive searches and 36 GA runs, so it can take several minutes. Output files are written to:

```text
data/benchmark/week8_demo/benchmark_results.json
data/benchmark/week8_demo/benchmark_runs.csv
```

The CSV is ready to import into Excel, pandas or report charts. Each row includes the failure KPI, recovery KPI, objective score, valve actions, evaluated candidate count, computation time and score gap to the exhaustive optimum.

Use another reproducible configuration with:

```powershell
python -m experiments.cli --config path/to/config.json --output-dir data/benchmark/my_run
```
