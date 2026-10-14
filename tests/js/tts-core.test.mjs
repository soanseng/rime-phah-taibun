// 轉換頁語音（docs/thak/js/tts-core.js）：任何輸入（漢羅／TL／POJ／數字調）→ 模型字母句。
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { segment, buildReverseIndex } from "../../docs/thak/js/dict.js";
import { speechSentences, encodeForModel, parseTokens } from "../../docs/thak/js/tts-core.js";

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

test("句讀切句：全形、半形標點攏是句界，毋送入模型", () => {
  const { sentences } = say("我是台灣人，我愛講台語。guá sī lâng!");
  assert.equal(sentences.length, 3);
  for (const s of sentences) assert.doesNotMatch(s, /[，。!,.]/);
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
