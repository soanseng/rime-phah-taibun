// 轉換頁語音（docs/thak/js/tts-core.js）：任何輸入（漢羅／TL／POJ／數字調）→ 模型字母句。
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { segment, buildReverseIndex } from "../../docs/thak/js/dict.js";
import { render } from "../../docs/thak/js/dict.js";
import {
  speechSentences, encodeForModel, parseTokens, sentenceGroups, renderGroups, splitPhrases, splitAtSentenceEnds,
  wordTimeline, displayTokens,
} from "../../docs/thak/js/tts-core.js";

const dict = JSON.parse(readFileSync(new URL("../../docs/thak/data-public/dict.json", import.meta.url), "utf8"));
const rev = buildReverseIndex(dict);
const tokens = parseTokens(readFileSync(new URL("../../docs/tts/tokens.txt", import.meta.url), "utf8"));
const say = (text, picks = new Map()) => speechSentences(segment(text, dict, rev), picks);
const wordCount = (text) => displayTokens(text).filter((t) => t.word).length;

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

test("wordTimeline：短語聲音長度照字母數分予逐詞，接續無空縫，短語中央是停頓", () => {
  const s = "guá sī tâi-oân-lâng, lí hó";
  const t = wordTimeline(s, [2.0, 0.6], 0.15);
  assert.equal(t.length, 5, "一个講話的詞一格");
  assert.equal(t[0].start, 0);
  assert.ok(Math.abs(t[2].end - 2.0) < 1e-9, "頭一短語收佇伊的聲音長度");
  for (const i of [1, 2]) assert.ok(Math.abs(t[i].start - t[i - 1].end) < 1e-9, "短語內詞接詞");
  assert.ok(t[2].end - t[2].start > t[1].end - t[1].start, "字母較濟的詞時間較長");
  assert.ok(Math.abs(t[3].start - 2.15) < 1e-9, "第二短語佇停頓後開始（逐短語重新對齊）");
  assert.ok(Math.abs(t[4].end - 2.75) < 1e-9);
});

test("wordTimeline：無合成的短語（null）伊的詞無時間，後壁照常（佮 synthSentence 仝款無加停頓）", () => {
  const t = wordTimeline("a, guá sī", [null, 1.0], 0.15);
  assert.equal(t[0], null);
  assert.equal(t[1].start, 0);
  assert.ok(Math.abs(t[2].end - 1.0) < 1e-9);
});

test("speechSentences 回報逐句對應的句組（無讀音的組略過，輸出區的句才對得著）", () => {
  const { sentences, groupOf } = say("Guá sī tâi-uân-lâng. 123! Lí hó?");
  assert.equal(sentences.length, 2);
  assert.deepEqual(groupOf, [0, 2]);
});

test("詞光對位：輸出顯示的詞數佮唸的詞數仝款（漢→羅 TL／POJ，羅→漢使用者例句）", async () => {
  const { tlToHan } = await import("../../docs/thak/js/dict.js");
  for (const text of ["我是台灣人，我欲講台語。", "Guá sī tâi-uân-lâng, guá ài kóng tâi-gí."]) {
    const segs = segment(text, dict, rev);
    const groups = sentenceGroups(segs);
    const shown = renderGroups(groups);
    const { sentences } = speechSentences(segs);
    groups.forEach((g, i) => {
      const n = wordTimeline(sentences[i], splitPhrases(sentences[i]).map(() => 1), 0).length;
      assert.equal(wordCount(shown[i].tl), n, shown[i].tl);
      assert.equal(wordCount(shown[i].poj), n, shown[i].poj);
    });
  }
  const text = "Lán Tâi-ôan ê tē khoah-tōa bô chhin-chhiūⁿ Tiong-kok, Ìn-tō͘ hit khóan, m̄ iông-ún soaⁿ-khîm iá-siù ê pháu-cháu";
  const [s] = speechSentences(segment(text, dict, rev)).sentences;
  const han = tlToHan(text, rev).han;
  assert.equal(wordCount(han), 17);
  assert.equal(wordTimeline(s, [1, 1, 1], 0).length, 17);
});

test("displayTokens：照空白切，有字的才算詞（標點綴詞），接起來佮原文仝款", () => {
  const text = "咱 臺灣, — 印度 彼 款.";
  const tokens = displayTokens(text);
  assert.deepEqual(tokens.filter((t) => t.word).map((t) => t.text), ["咱", "臺灣,", "印度", "彼", "款."]);
  assert.equal(tokens.map((t) => t.text).join(""), text, "複製的文字袂變");
});
