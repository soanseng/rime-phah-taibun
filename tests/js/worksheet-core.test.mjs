// 學習單核心：揀句（有華語的優先）、版型資料結構（對照／寫羅馬字／寫漢字／華語→台語）。
import { test } from "node:test";
import assert from "node:assert/strict";
import { alignSentence } from "../../docs/try/practice-core.js";
import { buildSheet, pickBankItems } from "../../docs/study/worksheet/worksheet-core.js";

const mulberry = (seed) => () => {
  seed = (seed + 0x6d2b79f5) >>> 0;
  let t = seed;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};

test("pickBankItems: 有華語的句優先、無重複、數量無夠就全部提", () => {
  const glossed = Array.from({ length: 12 }, (_, i) => ({ text: `G${i}`, slots: [], gloss: `華${i}` }));
  const bare = Array.from({ length: 12 }, (_, i) => ({ text: `B${i}`, slots: [], gloss: "" }));
  const picked = pickBankItems([...bare, ...glossed], 5, mulberry(42));
  assert.equal(picked.length, 5);
  assert.ok(picked.every((it) => it.gloss), "有華語的句優先");
  assert.equal(new Set(picked).size, 5, "無重複");
  const onlyBare = pickBankItems(bare, 3, mulberry(1));
  assert.equal(onlyBare.length, 3);
  assert.ok(onlyBare.every((it) => !it.gloss));
  assert.equal(pickBankItems(bare, 99).length, bare.length, "庫比句數細就全提");
});

test("buildSheet 對照：一格一字，TL 讀音佇下腳，無答案頁", () => {
  const slots = alignSentence("我食飯", "guá tsia̍h pn̄g");
  const sheet = buildSheet([{ text: "我食飯", slots, gloss: "我吃飯" }], { type: "pair" });
  assert.equal(sheet.type, "pair");
  assert.equal(sheet.rows.length, 1);
  assert.deepEqual(sheet.rows[0].cells.map((c) => c.top), ["我", "食", "飯"]);
  assert.deepEqual(sheet.rows[0].cells.map((c) => c.reading), ["guá", "tsia̍h", "pn̄g"]);
  assert.deepEqual(sheet.answers, []);
});

test("buildSheet 對照：POJ 開關", () => {
  const slots = alignSentence("我食飯", "guá tsia̍h pn̄g");
  const sheet = buildSheet([{ text: "我食飯", slots }], { type: "pair", poj: true });
  assert.deepEqual(sheet.rows[0].cells.map((c) => c.reading), ["góa", "chia̍h", "pn̄g"]);
});

test("buildSheet 寫羅馬字：顯示漢羅、一條書寫線", () => {
  const sheet = buildSheet([{ text: "我欲去學校。", slots: alignSentence("我欲去學校", "guá beh khì ha̍k-hāu"), gloss: "我要去學校。" }], { type: "roman" });
  assert.deepEqual(sheet.rows[0], { kind: "roman", han: "我欲去學校。", lines: 1 });
});

test("buildSheet 寫漢字：顯示讀音、漢字格數，標點無算格", () => {
  const slots = alignSentence("我食飯", "guá tsia̍h pn̄g");
  const sheet = buildSheet([{ text: "我食飯", slots }], { type: "hanji" });
  assert.equal(sheet.rows[0].kind, "hanji");
  assert.equal(sheet.rows[0].boxes, 3);
  assert.equal(sheet.rows[0].roman, "guá tsia̍h pn̄g");
  const punct = buildSheet(
    [{ text: "食飯。", slots: [...slots.slice(1), { h: "。", k: null, src: "。" }] }],
    { type: "hanji" },
  );
  assert.equal(punct.rows[0].boxes, 2, "標點無算漢字格");
  assert.equal(punct.rows[0].roman, "tsia̍h pn̄g。", "標點綴佇讀音後壁，免空白");
});

test("buildSheet 寫漢字：讀音無明的字佇題目顯示＿＿、答案頁才顯示本字", () => {
  const item = { text: "仝款", slots: [{ h: "仝", k: null, src: "仝" }, { h: "款", k: "khoan", src: "khoán" }] };
  const sheet = buildSheet([item], { type: "hanji" });
  assert.equal(sheet.rows[0].boxes, 2);
  assert.equal(sheet.rows[0].roman, "＿＿ khuán");
  const withAnswers = buildSheet([item], { type: "hanji", answers: true });
  assert.equal(withAnswers.answers[0].roman, "仝 khuán", "答案頁會使看");
});

test("buildSheet 華語→台語：干焦華語佮兩條線，無露出台語", () => {
  const sheet = buildSheet([{ text: "我食飯", slots: [], gloss: "我吃飯。" }], { type: "gloss" });
  assert.deepEqual(sheet.rows[0], { kind: "gloss", gloss: "我吃飯。", lines: 2 });
  assert.ok(!("han" in sheet.rows[0]) && !("roman" in sheet.rows[0]), "袂使洘底");
});

test("buildSheet 答案頁：逐句漢羅佮讀音", () => {
  const a = { text: "我食飯", slots: alignSentence("我食飯", "guá tsia̍h pn̄g"), gloss: "我吃飯" };
  const b = { text: "看冊", slots: alignSentence("看冊", "khuànn tsheh") };
  const sheet = buildSheet([a, b], { type: "pair", answers: true });
  assert.deepEqual(sheet.answers, [
    { han: "我食飯", roman: "guá tsia̍h pn̄g" },
    { han: "看冊", roman: "khuànn tsheh" },
  ]);
});

test("buildSheet: 無句就回空的", () => {
  assert.deepEqual(buildSheet([], { type: "pair" }), { type: "pair", rows: [], answers: [] });
});
