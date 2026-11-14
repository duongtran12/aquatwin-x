const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";


async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `Request failed with status ${response.status}`);
  }
  return payload;
}


export function getNetwork(networkId = "aquatwin_demo") {
  return request(`/api/networks/${networkId}`);
}


export function getHistory(limit = 12) {
  return request(`/api/history?limit=${limit}`);
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


export function startOptimization(networkId, scenario, algorithm = "ga") {
  return request("/api/recovery/optimize", {
    method: "POST",
    body: JSON.stringify({
      network_id: networkId,
      scenario,
      algorithm,
      max_actions: 2,
      top_k: 5,
      population_size: 20,
      generations: 20,
      crossover_rate: 0.8,
      mutation_rate: 0.1,
      tournament_size: 3,
      elite_count: 2,
      seed: 42,
    }),
  });
}


export async function waitForOptimization(jobId, onStatus) {
  for (let attempt = 0; attempt < 180; attempt += 1) {
    const job = await request(`/api/jobs/${jobId}`);
    onStatus?.(job.status);
    if (job.status === "completed") {
      return request(`/api/results/${jobId}`);
    }
    if (job.status === "failed") {
      throw new Error(job.error || "Optimization failed");
    }
    await new Promise((resolve) => window.setTimeout(resolve, 1000));
  }
  throw new Error("Optimization timed out after 3 minutes");
}

