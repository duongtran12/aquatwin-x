import assert from "node:assert/strict";
import test from "node:test";

import { resolveSystemStatus } from "./systemStatus.js";


test("system status does not claim online before health loads", () => {
  assert.equal(resolveSystemStatus(null, null).key, "checking");
});


test("system status reports an unavailable API", () => {
  const status = resolveSystemStatus({ status: "unavailable" }, null);
  assert.equal(status.key, "offline");
  assert.equal(status.title, "API unavailable");
});


test("system status distinguishes demo and real runtimes", () => {
  assert.equal(resolveSystemStatus({ status: "ok" }, { effective_mode: "demo" }).key, "demo");
  assert.equal(resolveSystemStatus({ status: "ok" }, { effective_mode: "real" }).key, "online");
});
