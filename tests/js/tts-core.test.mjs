// 轉換頁語音（docs/thak/js/tts-core.js）：任何輸入（漢羅／TL／POJ／數字調）→ 模型字母句。
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { segment, buildReverseIndex } from "../../docs/thak/js/dict.js";
import { render } from "../../docs/thak/js/dict.js";
import {
  speechSentences, encodeForModel, parseTokens, sentenceGroups, renderGroups, splitPhrases, splitAtSentenceEnds,
} from "../../docs/thak/js/tts-core.js";

const dict = JSON.parse(readFileSync(new URL("../../docs/thak/data-public/dict.json", import.meta.url), "utf8"));
const rev = buildReverseIndex(dict);
const tokens = parseTokens(readFileSync(new URL("../../docs/tts/tokens.txt", import.meta.url), "utf8"));
const say = (text, picks = new Map()) => speechSentences(segment(text, dict, rev), picks);

test("漢羅、TL、POJ、數字調：仝一句讀音送模型的字串仝款", () => {
  const want = say("góa sī tâi-oân-lâng").sentences;
  assert.deepEqual(want, ["góa sī tâi-oân-lâng"]);
  assert.deepEqual(say("guá sī tâi-uân-lâng").sentences, want);
  assert.deepEqual(say("goa2 si7 tai5-uan5-lang5").sentences, want);
  assert.deepEqual(say("Guá sī Tâi-uân-lâng").sentences, want, "大寫愛轉細寫");
});

test("漢字照詞典讀音轉做 POJ（本調，毋做變調）", () => {
  const { sentences } = say("我是台灣人");
  assert.equal(sentences.length, 1);
  assert.match(sentences[0], /^góa/);
  assert.match(sentences[0], /tâi-oân-lâng$/);
});

test("切句干焦看句尾標點（。？！；. ? ! ;、換行），逗號毋切", () => {
  const { sentences } = say("我是台灣人，我愛講台語。guá sī lâng! Lí hó? 好；好");
  assert.equal(sentences.length, 5);
  assert.match(sentences[0], /^góa-sī-tâi-oân-lâng, góa-ài/, "逗號留做句內停頓");
  for (const s of sentences) assert.doesNotMatch(s, /[，。！？；.!?;]/);
});

test("句內停頓：逗號、頓號、冒號 → 分做短語（合成時短停）", () => {
  assert.deepEqual(splitPhrases("góa, lí, i"), ["góa", "lí", "i"]);
  const { sentences } = say("我、你：伊。");
  assert.equal(sentences.length, 1);
  assert.equal(splitPhrases(sentences[0]).length, 3);
});

test("sentenceGroups：句界佇羅馬字段中央嘛切，組合起來佮規篇 render 仝款", () => {
  const text = "我是台灣人，我愛講台語。guá sī lâng! Lí hó? 好";
  const segs = segment(text, dict, rev);
  const groups = sentenceGroups(segs);
  assert.equal(groups.length, 4);
  for (const opts of [{}, { sandhi: true }]) {
    const whole = render(segs, new Map(), opts);
    const parts = renderGroups(groups, new Map(), opts);
    assert.equal(parts.map((p) => p.tl).join(""), whole.tl, JSON.stringify(opts));
    assert.equal(parts.map((p) => p.poj).join(""), whole.poj, JSON.stringify(opts));
  }
});

test("逐組唸的句佮規篇唸的句一對一（轉換區逐句 ▶ 對得著）", () => {
  const segs = segment("我是台灣人。我㘝。。guá sī lâng!", dict, rev);
  const groups = sentenceGroups(segs);
  const perGroup = groups.map((g) => speechSentences(g, new Map()).sentences);
  assert.deepEqual(perGroup.flat(), speechSentences(segs, new Map()).sentences);
  for (const s of perGroup) assert.ok(s.length <= 1, "一組上濟一句");
});

test("點過的讀音（picks）愛照用：詞身份 = 漢字＋讀音", () => {
  const segs = segment("重", dict, rev);
  const w = segs.find((s) => s.t === "w");
  assert.ok(w && w.readings.length > 1, "測試前提：『重』有多讀音");
  const a = speechSentences(segs, new Map()).sentences[0];
  const b = speechSentences(segs, new Map([[w.si, 1]])).sentences[0];
  assert.notEqual(a, b);
});

test("詞典揣無的字：列入 unread，毋送 ⟨⟩ 佔位符", () => {
  const { sentences, unread } = say("我㘝");
  assert.ok(unread.length > 0, "應該有揣無讀音的字");
  for (const s of sentences) assert.doesNotMatch(s, /[⟨⟩]/);
});

test("encodeForModel：add_blank 交錯、ⁿ 照模型規範略過、其他 OOV 報出來", () => {
  const { ids, oov } = encodeForModel("thiⁿ", tokens);
  // t h i 三字 → [0,t,0,h,0,i,0]；ⁿ 模型字母表無，照 MMS normalize 略過、毋算 OOV
  assert.equal(ids.length, 7);
  assert.equal(ids[0], 0);
  assert.equal(ids.at(-1), 0);
  assert.deepEqual(oov, []);
  assert.deepEqual(encodeForModel("ab5", tokens).oov, ["5"]);
});

test("POJ 調符組字：o͘ 佮第八聲 ̍ 攏是模型認得的字元", () => {
  const { oov } = encodeForModel("o͘ chia̍h pn̄g", tokens);
  assert.deepEqual(oov, []);
});

test("鼻化 ⁿ：speechSentences 保留（UI 靠伊提醒），encodeForModel 略過毋算 OOV", () => {
  const { sentences } = say("thiⁿ-khì");
  assert.ok(sentences[0].includes("\u207F"), "句內愛保留 ⁿ，UI 才會提醒鼻化無支援");
  const withN = encodeForModel(sentences[0], tokens);
  const withoutN = encodeForModel(sentences[0].replace("\u207F", ""), tokens);
  assert.deepEqual(withN.ids, withoutN.ids);
  assert.deepEqual(withN.oov, []);
});

test("羅→漢：輸出漢字照句尾標點切的句數，佮輸入羅馬字的句組一對一", async () => {
  const { tlToHan } = await import("../../docs/thak/js/dict.js");
  const inputs = [
    "Guá sī tâi-uân-lâng, guá ài kóng tâi-gí. Lí hó? Tsia̍h-pn̄g!",
    "Góa sī Tâi-oân-lâng.\nKin-á-ji̍t thiⁿ-khì chin hó, lán lâi-khì chia̍h-pn̄g.",
    "tsia̍h-pn̄g",
  ];
  for (const text of inputs) {
    const groups = sentenceGroups(segment(text, dict, rev));
    const pieces = splitAtSentenceEnds(tlToHan(text, rev).han);
    assert.equal(pieces.length, groups.length, text);
    assert.equal(pieces.join(""), tlToHan(text, rev).han, "切開閣接起來愛佮原文仝款");
  }
});

test("使用者例句（舊式 POJ 調符、o͘、ⁿ、m̄、句內逗號）：一句三短語，羅→漢一對一", () => {
  const text = "Lán Tâi-ôan ê tē khoah-tōa bô chhin-chhiūⁿ Tiong-kok, Ìn-tō͘ hit khóan, m̄ iông-ún soaⁿ-khîm iá-siù ê pháu-cháu";
  const segs = segment(text, dict, rev);
  const { sentences, unread } = speechSentences(segs);
  assert.deepEqual(unread, []);
  assert.equal(sentences.length, 1, "逗號毋切句");
  const [s] = sentences;
  assert.match(s, /tâi-oân/, "舊式 Tâi-ôan → 現代 tâi-oân");
  assert.match(s, /hit khoán/, "舊式 khóan → khoán");
  assert.match(s, /ìn-tō͘/);
  const phrases = splitPhrases(s);
  assert.equal(phrases.length, 3);
  for (const p of phrases) assert.deepEqual(encodeForModel(p, tokens).oov, [], p);
  assert.equal(sentenceGroups(segs).length, 1);
});
