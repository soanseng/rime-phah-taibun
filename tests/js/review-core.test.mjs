// 弱點複習核心：讀音答案比對（normalize 佮錯誤分類）。
import { test } from "node:test";
import assert from "node:assert/strict";
import { gradeReading } from "../../docs/study/review/review-core.js";

test("gradeReading: 標調符的 TL 原音過關", () => {
  assert.deepEqual(gradeReading("png7", "pn̄g"), { ok: true, categories: [] });
});

test("gradeReading: POJ 輸入嘛過關（tsiah8 ⇄ chia̍h）", () => {
  assert.deepEqual(gradeReading("tsiah8", "chia̍h"), { ok: true, categories: [] });
  assert.deepEqual(gradeReading("tshuann3", "chhòaⁿ"), { ok: true, categories: [] });
});

test("gradeReading: 數字調直接過關，大小寫無拘", () => {
  assert.deepEqual(gradeReading("tsiah8", "tsiah8"), { ok: true, categories: [] });
  assert.deepEqual(gradeReading("tsiah8", "TSIAH8"), { ok: true, categories: [] });
});

test("gradeReading: 無標調用內建隱含調（1，入聲 4）", () => {
  assert.deepEqual(gradeReading("khi1", "khi"), { ok: true, categories: [] });
  assert.deepEqual(gradeReading("sit4", "sit"), { ok: true, categories: [] });
  assert.deepEqual(gradeReading("png7", "png"), { ok: false, categories: ["tone"] });
});

test("gradeReading: 干焦聲調無合 → tone", () => {
  assert.deepEqual(gradeReading("sann1", "sann7"), { ok: false, categories: ["tone"] });
  assert.deepEqual(gradeReading("hue1", "hue7"), { ok: false, categories: ["tone"] });
});

test("gradeReading: 干焦送氣無合 → aspiration（tsiah 拍做 tshiah）", () => {
  assert.deepEqual(gradeReading("tsiah8", "tshiah"), { ok: false, categories: ["aspiration"] });
  assert.deepEqual(gradeReading("phing5", "ping5"), { ok: false, categories: ["aspiration"] });
});

test("gradeReading: 鼻化無合 → nasal（sann1 拍做 sa1）", () => {
  assert.deepEqual(gradeReading("sann1", "sa1"), { ok: false, categories: ["nasal"] });
  assert.deepEqual(gradeReading("khiann2", "khia2"), { ok: false, categories: ["nasal"] });
});

test("gradeReading: 聲母無合 → initial；韻母無合 → final；兩个攏無合 → other", () => {
  assert.deepEqual(gradeReading("bo5", "mo5"), { ok: false, categories: ["initial"] });
  assert.deepEqual(gradeReading("thai5", "than5"), { ok: false, categories: ["final"] });
  assert.deepEqual(gradeReading("tsai2", "bo5"), { ok: false, categories: ["other"] });
});

test("gradeReading: 多音節詞，連字號佮空白仝款看待", () => {
  assert.deepEqual(gradeReading("tsiah8 png7", "tsia̍h pn̄g"), { ok: true, categories: [] });
  assert.deepEqual(gradeReading("tsiah8 png7", "tsiah8-png7"), { ok: true, categories: [] });
  assert.deepEqual(gradeReading("tsiah8 png7", "tsiah png7"), { ok: false, categories: ["tone"] });
  assert.deepEqual(gradeReading("tsiah8 png7", "png7 tsiah8"), { ok: false, categories: ["other"] });
});

test("gradeReading: 音節數無合、空輸入 → other", () => {
  assert.deepEqual(gradeReading("tsiah8 png7", "pn̄g"), { ok: false, categories: ["other"] });
  assert.deepEqual(gradeReading("tsiah8", ""), { ok: false, categories: ["other"] });
});

test("gradeReading: 仝款錯誤出現規詞，分類干焦記一擺", () => {
  assert.deepEqual(gradeReading("kin1 kin1", "kin7 kin7"), { ok: false, categories: ["tone"] });
});
