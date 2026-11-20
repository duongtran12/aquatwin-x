import assert from "node:assert/strict";
import test from "node:test";

import { extractRunOutcome, formatComparisonValue, metricWinner } from "./historyComparison.js";


test("extractRunOutcome uses the recovered state for an optimization", () => {
  const outcome = extractRunOutcome({
    run_type: "optimization",
    result: {
      best_candidate: {
        score: 93.25,
        summary: {
          minimum_service_availability: 0.96,
          maximum_pressure_violations: 1,
          maximum_affected_nodes: 2,
          total_leakage_volume: 12.5,
        },
        actions: [{ valve_id: "V1", status: "CLOSED" }],
      },
    },
  });

  assert.equal(outcome.score, 93.25);
  assert.equal(outcome.service, 96);
  assert.equal(outcome.leakage, 12.5);
  assert.equal(outcome.actions.length, 1);
});


test("extractRunOutcome uses recovery metrics for a manual run", () => {
  const outcome = extractRunOutcome({
    run_type: "manual_recovery",
    result: { recovery: { summary: { minimum_service_availability: 0.8 } } },
  });

  assert.equal(outcome.service, 80);
});


test("metricWinner follows the metric direction", () => {
  assert.equal(metricWinner(95, 90, "higher"), "first");
  assert.equal(metricWinner(10, 8, "lower"), "second");
  assert.equal(metricWinner(10, 10, "lower"), null);
  assert.equal(metricWinner(null, 10, "lower"), null);
});


test("formatComparisonValue applies precision and units", () => {
  assert.equal(formatComparisonValue(92.345, { digits: 2, suffix: "" }), "92.34");
  assert.equal(formatComparisonValue(98.24, { digits: 1, suffix: "%" }), "98.2%");
  assert.equal(formatComparisonValue(null, { digits: 1, suffix: "%" }), "-");
});
