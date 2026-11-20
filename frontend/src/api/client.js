const API_URL = import.meta.env?.VITE_API_URL || "http://localhost:8000";


async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(payload.detail)
      ? payload.detail.map((item) => item.msg || String(item)).join("; ")
      : payload.detail;
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return payload;
}


export function getSystemHealth() {
  return request("/api/health");
}


export function getNetwork(networkId = "aquatwin_demo") {
  return request(`/api/networks/${networkId}`);
}


export function getNetworks() {
  return request("/api/networks");
}


export function importNetwork(file) {
  const body = new FormData();
  body.append("file", file);
  return request("/api/networks/import", { method: "POST", body });
}


export function importValveRegistry(networkId, file) {
  const body = new FormData();
  body.append("file", file);
  return request(`/api/networks/${networkId}/valves/import`, { method: "POST", body });
}


export function deleteNetwork(networkId) {
  return request(`/api/networks/${networkId}`, { method: "DELETE" });
}


export function getHistory(limit = 20, filters = {}) {
  const query = new URLSearchParams({ limit: String(limit) });
  if (filters.networkId && filters.networkId !== "all") query.set("network_id", filters.networkId);
  if (filters.runType && filters.runType !== "all") query.set("run_type", filters.runType);
  if (filters.runtimeMode && filters.runtimeMode !== "all") query.set("runtime_mode", filters.runtimeMode);
  return request(`/api/history?${query}`);
}


export function getHistoryItem(runId) {
  return request(`/api/history/${runId}`);
}


export function getHistoryAnalytics(runtimeMode = "all") {
  const query = runtimeMode === "all" ? "" : `?runtime_mode=${runtimeMode}`;
  return request(`/api/history/analytics${query}`);
}


export function historyDownloadUrl(runId, format) {
  return `${API_URL}/api/history/${runId}/download?format=${format}`;
}


export function simulateFailure(networkId, scenario) {
  return request("/api/simulations/failure", {
    method: "POST",
    body: JSON.stringify({ network_id: networkId, scenario }),
  });
}


export function simulateWhatIf(networkId, scenario, actions) {
  return request("/api/simulations/what-if", {
    method: "POST",
    body: JSON.stringify({ network_id: networkId, scenario, actions }),
  });
}


export function startOptimization(networkId, scenario, config = {}) {
  return request("/api/recovery/optimize", {
    method: "POST",
    body: JSON.stringify({
      network_id: networkId,
      scenario,
      algorithm: "ga",
      max_actions: config.maxActions ?? 2,
      top_k: 5,
      population_size: config.populationSize ?? 20,
      generations: config.generations ?? 20,
      crossover_rate: 0.8,
      mutation_rate: 0.1,
      tournament_size: 3,
      elite_count: 2,
      seed: config.seed ?? 42,
    }),
  });
}


export async function waitForOptimization(jobId, onStatus) {
  for (let attempt = 0; attempt < 180; attempt += 1) {
    const job = await request(`/api/jobs/${jobId}`);
    onStatus?.(job);
    if (job.status === "completed") {
      return request(`/api/results/${jobId}`);
    }
    if (job.status === "failed") {
      throw new Error(job.error || "Optimization failed");
    }
    if (job.status === "cancelled") {
      throw new Error("AI recovery cancelled");
    }
    await new Promise((resolve) => window.setTimeout(resolve, 1000));
  }
  throw new Error("Optimization timed out after 3 minutes");
}


export function cancelJob(jobId) {
  return request(`/api/jobs/${jobId}`, { method: "DELETE" });
}


export function startBatchExperiment(payload) {
  return request("/api/experiments/batch", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}


export function getBatchExperiments(limit = 12) {
  return request(`/api/experiments?limit=${limit}`);
}


export function getBatchExperiment(experimentId) {
  return request(`/api/experiments/${experimentId}`);
}


export async function waitForBatchExperiment(jobId, onStatus) {
  for (let attempt = 0; attempt < 720; attempt += 1) {
    const job = await request(`/api/jobs/${jobId}`);
    onStatus?.(job);
    if (job.status === "completed") return request(`/api/results/${jobId}`);
    if (job.status === "failed") throw new Error(job.error || "Batch experiment failed");
    if (job.status === "cancelled") throw new Error("Batch experiment cancelled");
    await new Promise((resolve) => window.setTimeout(resolve, 1000));
  }
  throw new Error("Batch experiment timed out after 12 minutes");
}


export function experimentDownloadUrl(jobId, format) {
  return `${API_URL}/api/experiments/${jobId}/download?format=${format}`;
}

