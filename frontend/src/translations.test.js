import assert from "node:assert/strict";
import test from "node:test";
import { LANGUAGE_STORAGE_KEY, localizeStatus, readLanguage, translate } from "./translations.js";

test("defaults to Vietnamese and restores valid language selections", () => {
  for (const [saved, expected] of [[null, "vi"], ["fr", "vi"], ["constructor", "vi"], ["vi", "vi"], ["en", "en"]]) {
    const storage = () => ({
      getItem(key) {
        assert.equal(key, LANGUAGE_STORAGE_KEY);
        return saved;
      },
    });
    assert.equal(readLanguage(storage), expected);
  }
  assert.equal(readLanguage(() => { throw new Error("Storage blocked"); }), "vi");
});

test("translates dashboard copy and preserves dynamic values in both languages", () => {
  assert.equal(translate("vi", "Overview"), "Tổng quan");
  assert.equal(translate("en", "Overview"), "Overview");
  assert.equal(translate("vi", "Selected: {pipe}", { pipe: "P3" }), "Ống đã chọn: P3");
  assert.equal(translate("en", "Selected: {pipe}", { pipe: "P3" }), "Selected: P3");
  assert.equal(translate("vi", "aquatwin_demo"), "aquatwin_demo");
});

test("localizes known job progress while preserving backend diagnostics", () => {
  const t = (message, values) => translate("vi", message, values);
  assert.equal(localizeStatus(t, "Generation 2 of 20"), "Thế hệ 2/20");
  assert.equal(localizeStatus(t, "Completed GA seed -7 for case-1"), "Đã chạy GA với hạt giống -7 cho case-1");
  assert.equal(localizeStatus(t, "Could not load network P3"), "Could not load network P3");
});
