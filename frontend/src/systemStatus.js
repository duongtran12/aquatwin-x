export function resolveSystemStatus(health, runtime) {
  if (health?.status === "unavailable") {
    return { key: "offline", title: "API unavailable", detail: "Check backend connection" };
  }
  if (!health) {
    return { key: "checking", title: "Checking digital twin", detail: "Connecting to API" };
  }
  if (runtime?.effective_mode === "demo") {
    return { key: "demo", title: "Demo twin active", detail: "Synthetic preview data" };
  }
  if (runtime?.effective_mode === "real") {
    return { key: "online", title: "Digital twin online", detail: "WNTR / PDD model" };
  }
  return { key: "checking", title: "Loading network model", detail: "API connected" };
}
