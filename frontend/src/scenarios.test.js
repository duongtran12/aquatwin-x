import assert from "node:assert/strict";
import test from "node:test";

import { findScenarioPreset, SCENARIO_PRESETS } from "./scenarios.js";


test("scenario presets cover increasing incident severity", () => {
  assert.deepEqual(SCENARIO_PRESETS.map((preset) => preset.id), ["minor", "major", "burst"]);
  assert.deepEqual(SCENARIO_PRESETS.map((preset) => preset.scenario.leakArea), [0.0002, 0.0005, 0.001]);
  assert.ok(SCENARIO_PRESETS.every((preset) => preset.scenario.endHour > preset.scenario.startHour));
});


test("findScenarioPreset accepts numeric form values stored as strings", () => {
  assert.equal(findScenarioPreset({ leakArea: "0.0005", startHour: "2", endHour: "12" }), "major");
});


test("findScenarioPreset identifies a customized scenario", () => {
  assert.equal(findScenarioPreset({ leakArea: 0.0007, startHour: 3, endHour: 10 }), null);
});
