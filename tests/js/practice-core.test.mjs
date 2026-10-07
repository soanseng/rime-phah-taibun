// 網頁試拍練習核心：比對規則（TL/POJ 等價、漢字/羅馬字對位、評分）。
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  sylKey, tokenize, alignSentence, romanSlots, buildCharKeys, grade, readingOf, splitSentences,
} from "../../docs/try/practice-core.js";

const shape = (toks) => toks.map((t) => (t.h ? `h:${t.h}` : `k:${t.k}`));

test("sylKey: TL 佮 POJ 仝音節得著仝一个去調鍵", () => {
  const pairs = [
    ["tsia̍h", "chia̍h"], ["guá", "góa"], ["sing", "seng"], ["tshut", "chhut"],
    ["kuānn", "koāⁿ"], ["oo", "o͘"], ["ik", "ek"], ["tsi̍t", "chi̍t"],
  ];
  for (const [tl, poj] of pairs) assert.equal(sylKey(tl), sylKey(poj), `${tl} / ${poj}`);
  assert.equal(sylKey("tsia̍h"), "tsiah");
});

test("sylKey: 舊式 o· 中點、無點 ı、大寫攏正規化", () => {
  assert.equal(sylKey("kò·"), "koo");
  assert.equal(sylKey("sı̄"), "si");
  assert.equal(sylKey("Ukraina"), "ukraina");
});

test("tokenize: 漢字逐字、羅馬字照連字號切音節，標點數字略過", () => {
  assert.deepEqual(shape(tokenize("我是Tâi-oân人。")), ["h:我", "h:是", "k:tai", "k:uan", "h:人"]);
  assert.deepEqual(shape(tokenize("chhó--ê")), ["k:tsho", "k:e"]);
  assert.deepEqual(shape(tokenize("1918 nî")), ["k:ni"]);
  assert.equal(tokenize("Tâi-oân")[0].src, "Tâi");
});

test("alignSentence: 漢字對 TL 音節逐格對位，數量無合就 null", () => {
  const s = alignSentence("一蕊花", "tsi̍t luí hue");
  assert.deepEqual(s.map((x) => [x.h, x.k, x.src]), [["一", "tsit", "tsi̍t"], ["蕊", "lui", "luí"], ["花", "hue", "hue"]]);
  assert.equal(alignSentence("一蕊花", "tsi̍t luí"), null);
  const mixed = alignSentence("我ê冊", "guá ê tsheh");
  assert.deepEqual(mixed.map((x) => [x.h, x.k]), [["我", "gua"], [null, "e"], ["冊", "tsheh"]]);
  assert.equal(alignSentence("我a冊", "guá ê tsheh"), null, "漢羅內底羅馬字讀音愛合");
});

test("romanSlots: 羅馬字逐音節做格，夾佇內底的漢字（註解）做無讀音的漢字格", () => {
  const s = romanSlots("Chhùi-khí (喙齒)");
  assert.deepEqual(s.map((x) => [x.h, x.k]), [[null, "tshui"], [null, "khi"], ["喙", null], ["齒", null]]);
});

test("buildCharKeys: 字數＝音節數的詞條，逐字收去調讀音", () => {
  const ck = buildCharKeys({
    "食": { r: ["tsiah8"] }, "食飯": { r: ["tsiah8 png7"] }, "飯": { r: ["png7", "huan7"] },
    "阿婆仔": { r: ["a1 po5"] },
  });
  assert.deepEqual([...ck.get("飯")].sort(), ["huan", "png"]);
  assert.deepEqual([...ck.get("食")], ["tsiah"]);
  assert.equal(ck.has("婆"), false, "音節數無合的詞條毋收");
});

test("grade: 漢字愛仝字；羅馬字照讀音算對；多拍的另外算", () => {
  const slots = alignSentence("我是台灣人", "guá sī tâi-uân-lâng");
  assert.deepEqual(grade(slots, "我是台灣人"), { marks: ["ok", "ok", "ok", "ok", "ok"], extra: 0, done: true, correct: 5 });
  const roman = grade(slots, "我是tâi-uân人");
  assert.equal(roman.done, true, "漢字格拍羅馬字（全羅／漢羅輸出）照讀音算對");
  const wrong = grade(slots, "我是台彎");
  assert.deepEqual(wrong.marks, ["ok", "ok", "ok", "bad"]);
  assert.equal(wrong.done, false);
  const extra = grade(slots, "我是台灣人啦啦");
  assert.equal(extra.extra, 2);
  assert.equal(extra.done, false);
  assert.deepEqual(grade(slots, ""), { marks: [], extra: 0, done: false, correct: 0 });
});

test("grade: 羅馬字來源的格，漢字照讀音接受同音字；註解漢字格干焦仝字", () => {
  const ck = buildCharKeys({ "食": { r: ["tsiah8"] }, "飯": { r: ["png7"] }, "喙": { r: ["tshui3"] } });
  const slots = romanSlots("Chia̍h pn̄g (喙)");
  assert.equal(grade(slots, "食飯喙", ck).done, true);
  assert.deepEqual(grade(slots, "食飯嘴", ck).marks, ["ok", "ok", "bad"]);
  assert.deepEqual(grade(slots, "飯", ck).marks, ["bad"], "無收著讀音的字毋算對");
});

test("readingOf: 格的讀音照 TL／POJ 開關顯示；讀音不明就 null", () => {
  const [chiah] = romanSlots("chia̍h");
  assert.equal(readingOf(chiah, false), "tsia̍h");
  assert.equal(readingOf(chiah, true), "chia̍h");
  const [gua] = alignSentence("我", "guá");
  assert.equal(readingOf(gua, true), "góa");
  assert.equal(readingOf({ h: "喙", k: null, src: "喙" }, false), null);
});

test("splitSentences: 標題行拿掉、照句尾標點切、傷長的句照逗號切", () => {
  assert.deepEqual(splitSentences("== Tē it Chiuⁿ ==\nA sī B. C sī D."), ["A sī B.", "C sī D."]);
  const long = Array.from({ length: 4 }, () => "chi̍t nn̄g saⁿ sì gō͘ la̍k chhit peh káu cha̍p").join(", ") + ".";
  const parts = splitSentences(long);
  assert.ok(parts.length >= 2, "40 音節的句愛切開");
  assert.ok(parts.every((p) => romanSlots(p).length <= 30));
  assert.deepEqual(splitSentences("A.\n\nê"), [], "賰無兩格的句毋收");
  assert.deepEqual(splitSentences("我欲去學校。阮阿母咧煮飯！"), ["我欲去學校。", "阮阿母咧煮飯！"], "全形句號後壁無空白嘛愛切");
});
