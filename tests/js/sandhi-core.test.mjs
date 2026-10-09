// 變調練習核心：調組切分（標點、輕聲「--」、手動界線）佮變調小測驗出題。
import { test } from "node:test";
import assert from "node:assert/strict";
import { segment } from "../../docs/thak/js/dict.js?v=26";
import { sandhiSyllable } from "../../docs/thak/js/roman.js?v=26";
import {
  TONE_OPTIONS, analyzeRoman, analyzeHanlo, applySandhi, toggleEnd, toneOf, romanOf,
  sandhiPattern, sentencePool, makeQuestion, makeRound, cardId,
} from "../../docs/study/sandhi/sandhi-core.js";

const T2 = "\u0301"; // 2 聲
const T3 = "\u0300"; // 3 聲
const T7 = "\u0304"; // 7 聲
const T8 = "\u030D"; // 8 聲（教育部台羅）

test("analyzeRoman: 白話字／台羅輸入 → 本調音節，句尾一个調組", () => {
  const s = analyzeRoman("Guá beh khì Tâi-pak.");
  assert.equal(s.length, 5);
  assert.deepEqual(s.map((x) => x.base), ["gua2", "beh4", "khi3", "tai5", "pak4"]);
  assert.deepEqual(s.map((x) => x.autoEnd), [false, false, false, false, true]);
  assert.deepEqual(s.map((x) => x.han), [null, null, null, null, null]);
  assert.deepEqual(analyzeRoman("").map((x) => x.base), []);
});

test("applySandhi: 一个調組內底，上尾音節以外攏變調；入聲 -h 4→2", () => {
  const syls = analyzeRoman("Guá beh khì Tâi-pak.");
  const out = applySandhi(syls);
  assert.deepEqual(out.map((x) => x.out), ["gua1", "beh2", "khi2", "tai7", "pak4"]);
  assert.deepEqual(out.map((x) => x.changed), [true, true, true, true, false]);
  assert.deepEqual(out.map((x) => x.end), [false, false, false, false, true]);
  assert.deepEqual(out.map((x) => [x.baseTone, x.outTone]), [["2", "1"], ["4", "2"], ["3", "2"], ["5", "7"], ["4", "4"]]);
  assert.equal(syls[0].autoEnd, false, "applySandhi 袂當改著入來的音節");
});

test("applySandhi: 標點（全形／半形）切開調組，組尾保留本調", () => {
  const out = applySandhi(analyzeRoman("guá tsia̍h-pn̄g。lí tsia̍h-pn̄g."));
  assert.deepEqual(out.map((x) => x.out), ["gua1", "tsiah3", "png7", "li1", "tsiah3", "png7"]);
  assert.deepEqual(out.map((x) => x.end), [false, false, true, false, false, true]);
  for (const p of "，。！？、；：,.!?;:") {
    const s = analyzeRoman(`khi3${p}khi3`);
    assert.deepEqual(s.map((x) => x.autoEnd), [true, true], p);
  }
});

test("applySandhi: 輕聲「--」前的音節收調組；「--」後壁的音節是輕聲、無變調", () => {
  const syls = analyzeRoman("tshó--ê");
  assert.deepEqual(syls.map((x) => x.base), ["tsho2", "e5"]);
  assert.deepEqual(syls.map((x) => x.light), [false, true]);
  const out = applySandhi(syls);
  assert.deepEqual(out.map((x) => x.out), ["tsho2", null]);
  assert.deepEqual(out.map((x) => x.outTone), ["2", null]);
  const more = applySandhi(analyzeRoman("tshó--ê-sian"));
  assert.deepEqual(more.map((x) => x.light), [false, true, true]);
  assert.deepEqual(more.map((x) => x.out), ["tsho2", null, null]);
  const two = applySandhi(analyzeRoman("tshó--ê. guá khì"));
  assert.deepEqual(two.map((x) => x.out), ["tsho2", null, "gua1", "khi3"], "句讀了後回復正常變調");
});

test("toggleEnd/applySandhi: 手動切調組，切點保留本調", () => {
  const syls = analyzeRoman("guá khì Tâi-pak.");
  assert.deepEqual(toggleEnd([], 1), [1]);
  assert.deepEqual(toggleEnd([1], 1), []);
  assert.deepEqual(toggleEnd([1], 3), [1, 3]);
  assert.deepEqual(applySandhi(syls).map((x) => x.out), ["gua1", "khi2", "tai7", "pak4"]);
  const cut = applySandhi(syls, [1]);
  assert.deepEqual(cut.map((x) => x.out), ["gua1", "khi3", "tai7", "pak4"]);
  assert.equal(cut[1].changed, false);
  assert.deepEqual(applySandhi(syls, toggleEnd([1], 1)).map((x) => x.out), ["gua1", "khi2", "tai7", "pak4"]);
});

test("pojToTl 路徑：chia̍h-pn̄g → tsiah8 png7；變調照 sandhiSyllable（-h 8→3）", () => {
  const out = applySandhi(analyzeRoman("chia̍h-pn̄g"));
  assert.deepEqual(out.map((x) => x.base), ["tsiah8", "png7"]);
  assert.equal(out[0].out, sandhiSyllable("tsiah8"));
  assert.equal(out[0].out, "tsiah3");
  assert.equal(out[1].out, "png7");
});

test("analyzeRoman: 無標調音節照入聲／舒聲補 4／1 調；ⁿ、o͘ 正常轉", () => {
  assert.deepEqual(analyzeRoman("chiah-png").map((x) => x.base), ["tsiah4", "png1"]);
  assert.deepEqual(analyzeRoman("Khòaⁿ--ê").map((x) => x.base), ["khuann3", "e5"]);
});

test("analyzeHanlo: 詞典分詞、頭一个讀音逐字對位；無收著／音節無合→不明；內底羅馬字照算", () => {
  const dict = { 食飯: { r: ["tsiah8 png7", "tsiah8 puinn7"], h: "吃飯" }, 好: { r: ["ho2"], h: "好" } };
  const syls = analyzeHanlo(segment("食飯，好。", dict));
  assert.deepEqual(syls.map((x) => [x.han, x.base]), [["食", "tsiah8"], ["飯", "png7"], ["好", "ho2"]]);
  assert.deepEqual(applySandhi(syls).map((x) => x.out), ["tsiah3", "png7", "ho2"]);
  const miss = analyzeHanlo(segment("食飯𠀾好", dict));
  assert.deepEqual(miss.map((x) => [x.han, x.base]), [["食", "tsiah8"], ["飯", "png7"], ["𠀾", null], ["好", "ho2"]]);
  assert.equal(applySandhi(miss)[2].out, null);
  const bad = analyzeHanlo(segment("食飯", { 食飯: { r: ["tsiah8 png7 png7"] } }));
  assert.deepEqual(bad.map((x) => x.base), [null, null], "音節數佮字數無合就標不明");
  const mixed = analyzeHanlo(segment("我ê冊", { 我: { r: ["gua2"] }, 冊: { r: ["tsheh4"] } }));
  assert.deepEqual(mixed.map((x) => x.base), ["gua2", "e5", "tsheh4"]);
  assert.deepEqual(mixed.map((x) => x.han), ["我", null, "冊"]);
});

test("romanOf/toneOf/sandhiPattern: 顯示用 TL／POJ 調符佮數字", () => {
  assert.equal(romanOf("tsiah8", false), `tsia${T8}h`);
  assert.equal(romanOf("tsiah8", true), `chia${T8}h`);
  assert.equal(romanOf("tsiah3", true), `chia${T3}h`);
  assert.equal(romanOf("png7", false), `pn${T7}g`);
  assert.equal(romanOf("tsiah3 png7", false), `tsia${T3}h-pn${T7}g`);
  assert.equal(romanOf("gua2", false), `gua${T2}`);
  assert.equal(romanOf(null, false), null);
  assert.equal(toneOf("tsiah8"), "8");
  assert.equal(toneOf("tsiah"), null);
  assert.equal(toneOf(null), null);
  assert.equal(sandhiPattern("tsiah8 png7"), "tsiah3 png7");
  assert.equal(sandhiPattern("ho2 tsiah8"), "ho1 tsiah8");
});

const LEKU = [
  { han: "紅嬰仔哭甲一身軀汗。", tl: "Âng-enn-á khàu kah tsi̍t sin-khu kuānn.", hoa: "小嬰兒哭得滿身大汗。" },
  { han: "伊佮我的看法並無一致。", tl: "I kah guá ê khuànn-huat pīng bô it-tì.", hoa: "他跟我的看法並不一致。" },
];

test("sentencePool: 教典例句的連字號詞（2–3 音節、全漢、無輕聲）→ 詞池，帶原句", () => {
  const pool = sentencePool(LEKU);
  const byHan = Object.fromEntries(pool.map((x) => [x.han, x]));
  // Âng-enn-á 用單連字號，歸个詞是「紅嬰仔」——詞內有 仔，整詞免
  assert.deepEqual(Object.keys(byHan).sort(), ["一致", "看法", "身軀"]);
  assert.equal(byHan.身軀.numeric, "sin1 khu1");
  assert.equal(byHan.身軀.sent, LEKU[0].han, "帶出例句做語境");
  assert.equal(byHan.一致.numeric, "it4 ti3", "調符轉數字調");
  assert.ok(!pool.some((x) => x.han.includes("仔")), "詞內有 仔 免（連讀變調無固定）");
});

test("sentencePool: 仝詞第二个例句袂重複；單音節、三疊音、標點干焦的 token 免", () => {
  const dup = sentencePool([
    ...LEKU,
    { han: "身軀愛洗浴。", tl: "Sin-khu ài sé-i̍k.", hoa: "身體要洗澡。" },
    { han: "伊食飯。", tl: "I tsia̍h--pn̄g.", hoa: "他吃飯。" },
  ]);
  assert.equal(dup.filter((x) => x.han === "身軀").length, 1);
  const noTriple = sentencePool([{ han: "伊食食食。", tl: "I tsiah8-tsiah8-tsiah8.", hoa: "x" }]);
  assert.deepEqual(noTriple, [], "三疊音免");
  assert.deepEqual(sentencePool([]), []);
  assert.deepEqual(sentencePool([{ han: "喔。", tl: "Ooh." }]), [], "單音節／標點免");
});

test("sentencePool: 逗號後壁的詞嘛愛對位著（標點毋算漢字 slot）", () => {
  const real = sentencePool([
    { han: "你著較拍拚咧，毋通做了尾仔囝。", tl: "Lí tio̍h khah phah-piànn--leh, m̄-thang tsò liáu-bué-á-kiánn.", hoa: "你要更努力，別做吊車尾的。" },
  ]);
  const byHan = Object.fromEntries(real.map((x) => [x.han, x]));
  assert.equal(byHan.毋通?.numeric, "m7 thang1", "逗號後 詞佮字對位著");
  assert.ok(!real.some((x) => x.han.includes("仔")), "尾仔囝 免");
  const mini = sentencePool([
    { han: "我看電影，食便當。", tl: "Guá khuànn tiān-iánn, tsia̍h piān-tong.", hoa: "x" },
  ]);
  assert.deepEqual(mini.map((x) => x.han), ["電影", "便當"]);
  assert.deepEqual(sentencePool([{ han: "tsit8 e5 好。", tl: "tsit8 e5 hó." }]), [], "漢羅例句無收");
});
test("makeQuestion/makeRound/cardId: 揀一个非尾音節，答案＝sandhiSyllable 的調；題帶例句", () => {
  const q = makeQuestion({ han: "食飯", numeric: "tsiah8 png7", sent: "我食飯。", sentTl: "Guá tsia̍h-pn̄g.", hoa: "我吃飯。" }, () => 0);
  assert.equal(q.i, 0);
  assert.equal(q.correct, "3");
  assert.equal(q.numeric, "tsiah8 png7");
  assert.equal(q.pattern, "tsiah3 png7");
  assert.equal(q.sent, "我食飯。");
  assert.deepEqual(q.options, TONE_OPTIONS);
  assert.deepEqual(TONE_OPTIONS, ["1", "2", "3", "4", "5", "7", "8"]);
  const q2 = makeQuestion({ han: "食飽飯", numeric: "tsiah8 pa2 png7" }, () => 0.99);
  assert.equal(q2.i, 1);
  assert.equal(q2.correct, "1");
  assert.equal(cardId(q2), "sandhi:食飽飯|tsiah8 pa2 png7|1");
  assert.equal(cardId(q), "sandhi:食飯|tsiah8 png7|0");
  const pool = ["食飯", "好食", "拍球"].map((han) => ({ han, numeric: "tsiah8 png7" }));
  const qs = makeRound(pool, 10, () => 0);
  assert.equal(qs.length, 3, "池仔細就出甲了");
  assert.deepEqual(qs.map((x) => x.han), ["食飯", "好食", "拍球"]);
  assert.equal(makeRound(pool, 2, () => 0).length, 2);
});
