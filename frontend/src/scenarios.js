export const SCENARIO_PRESETS = [
  {
    id: "minor",
    label: "Small leak",
    description: "Localized six-hour incident",
    scenario: { leakArea: 0.0002, startHour: 2, endHour: 8 },
  },
  {
    id: "major",
    label: "Major leak",
    description: "Ten-hour operational disruption",
    scenario: { leakArea: 0.0005, startHour: 2, endHour: 12 },
  },
  {
    id: "burst",
    label: "Pipe burst",
    description: "Severe full-day failure",
    scenario: { leakArea: 0.001, startHour: 0, endHour: 24 },
  },
];


export function findScenarioPreset(scenario) {
  return SCENARIO_PRESETS.find((preset) => (
    Number(scenario.leakArea) === preset.scenario.leakArea
    && Number(scenario.startHour) === preset.scenario.startHour
    && Number(scenario.endHour) === preset.scenario.endHour
  ))?.id || null;
}
