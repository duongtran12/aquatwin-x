import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

import {
  experimentDownloadUrl,
  getHistory,
  getNetwork,
  getSystemHealth,
  historyDownloadUrl,
  importNetwork,
  simulateFailure,
  startOptimization,
  waitForOptimization,
} from "./client.js";

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

test("getHistory serializes only active filters", async () => {
  let requestUrl;
  globalThis.fetch = async (url) => {
    requestUrl = url;
    return jsonResponse([{ run_id: "run-1" }]);
  };

  const result = await getHistory(8, {
    networkId: "aquatwin_demo",
    runType: "optimization",
    runtimeMode: "all",
  });

  assert.equal(
    requestUrl,
    "http://localhost:8000/api/history?limit=8&network_id=aquatwin_demo&run_type=optimization",
  );
  assert.deepEqual(result, [{ run_id: "run-1" }]);
});

test("getSystemHealth reads release metadata", async () => {
  globalThis.fetch = async () => jsonResponse({
    status: "ok",
    version: "0.1.0",
    build_commit: "abc1234",
  });

  const health = await getSystemHealth();

  assert.equal(health.version, "0.1.0");
  assert.equal(health.build_commit, "abc1234");
});

test("simulateFailure sends JSON with the expected content type", async () => {
  let captured;
  globalThis.fetch = async (url, options) => {
    captured = { url, options };
    return jsonResponse({ status: "completed" });
  };
  const scenario = { pipe_id: "P3", leak_area: 0.0005 };

  await simulateFailure("aquatwin_demo", scenario);

  assert.equal(captured.url, "http://localhost:8000/api/simulations/failure");
  assert.equal(captured.options.method, "POST");
  assert.equal(captured.options.headers.get("Content-Type"), "application/json");
  assert.deepEqual(JSON.parse(captured.options.body), {
    network_id: "aquatwin_demo",
    scenario,
  });
});

test("importNetwork leaves multipart content type to the runtime", async () => {
  let captured;
  globalThis.fetch = async (url, options) => {
    captured = { url, options };
    return jsonResponse({ network: { name: "district_a" } }, 201);
  };
  const file = new Blob(["[JUNCTIONS]"], { type: "text/plain" });

  await importNetwork(file);

  assert.equal(captured.url, "http://localhost:8000/api/networks/import");
  assert.equal(captured.options.headers.has("Content-Type"), false);
  assert.equal(captured.options.body instanceof FormData, true);
  assert.equal(captured.options.body.get("file").size, file.size);
});

test("API validation details become one readable error", async () => {
  globalThis.fetch = async () => jsonResponse({
    detail: [{ msg: "Pipe is required" }, { msg: "Leak area must be positive" }],
  }, 422);

  await assert.rejects(
    getNetwork("invalid"),
    /Pipe is required; Leak area must be positive/,
  );
});

test("startOptimization maps dashboard settings to the API schema", async () => {
  let body;
  globalThis.fetch = async (_url, options) => {
    body = JSON.parse(options.body);
    return jsonResponse({ job_id: "job-1", status: "queued" }, 202);
  };

  await startOptimization(
    "aquatwin_demo",
    { pipe_id: "P2" },
    { maxActions: 3, populationSize: 24, generations: 30, seed: 7 },
  );

  assert.equal(body.algorithm, "ga");
  assert.equal(body.max_actions, 3);
  assert.equal(body.population_size, 24);
  assert.equal(body.generations, 30);
  assert.equal(body.seed, 7);
});

test("waitForOptimization returns the completed result without another delay", async () => {
  const requested = [];
  globalThis.fetch = async (url) => {
    requested.push(url);
    if (url.endsWith("/api/jobs/job-2")) {
      return jsonResponse({ job_id: "job-2", status: "completed" });
    }
    return jsonResponse({ best_score: 94.2 });
  };

  const result = await waitForOptimization("job-2");

  assert.deepEqual(result, { best_score: 94.2 });
  assert.deepEqual(requested, [
    "http://localhost:8000/api/jobs/job-2",
    "http://localhost:8000/api/results/job-2",
  ]);
});

test("download helpers produce stable evidence URLs", () => {
  assert.equal(
    historyDownloadUrl("run 1", "json"),
    "http://localhost:8000/api/history/run 1/download?format=json",
  );
  assert.equal(
    experimentDownloadUrl("exp-1", "zip"),
    "http://localhost:8000/api/experiments/exp-1/download?format=zip",
  );
});
