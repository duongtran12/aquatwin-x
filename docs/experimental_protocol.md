# AquaTwin-X Experimental Protocol

## Objective

Evaluate whether the Genetic Algorithm can find recovery actions close to the global optimum while evaluating fewer candidates and using less computation time than exhaustive search.

## Test matrix

| Variable | Values |
|---|---|
| Network | `aquatwin_demo` |
| Failed pipes | P1, P2, P3, P4, P5, P6 |
| Leak areas | 0.0003 m², 0.0007 m² |
| Incident period | 02:00–12:00 |
| Maximum valve actions | 2 |
| GA random seeds | 7, 42, 101 |
| GA population | 20 |
| GA generations | 20 |

This produces 12 distinct failure scenarios and 36 GA runs.

## Compared methods

1. Isolation baseline: close both virtual endpoint valves of the failed pipe.
2. Exhaustive search: global reference over all candidates containing at most two actions.
3. Genetic Algorithm: stochastic optimization repeated with three seeds.

## Recorded indicators

- Objective score from 0 to 100.
- Minimum service availability.
- Maximum pressure violations.
- Maximum affected nodes.
- Total leakage volume.
- Number and identity of valve actions.
- Number of candidates evaluated.
- Computation time.
- GA score gap to exhaustive search.
- GA global-optimum hit rate.

## Reproduction

```powershell
python -m experiments.cli
```

Keep the generated JSON as the machine-readable evidence and use the CSV for tables and charts in the report. Do not manually alter either file after a run; change the configuration and rerun instead.

## Extended benchmark network

`aquatwin_benchmark` contains 12 demand junctions, one reservoir, 21 pipes and 42 virtual isolation valves. It provides a larger multi-loop search space than the four-junction demonstration network.

Run its predefined seven-pipe test matrix from the command line:

```powershell
python -m experiments.cli --config experiments/configs/benchmark_12node.json --output-dir data/benchmark/benchmark_12node
```

The same batch can be configured in the dashboard under **Batch Experiments**. The API runs it as a background job, exposes progress, and provides immutable JSON and CSV downloads. Results labeled `demo` are synthetic interface checks and must not be cited as hydraulic evidence.
