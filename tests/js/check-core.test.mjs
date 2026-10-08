// 寫作檢查核心：拼音系統、數字調、調號/韻尾、調符位置、詞典音節、連字符、推薦用字、華語直譯。
// 純函式（無 DOM），資料（詞典、segments、hints）攏是注入的。
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  scanRomanWords, wordSystem, convertWord,
  checkSystemMixing, checkNumericTones, checkToneFinals, checkMarkPosition, checkSpelling,
  buildSyllableSet, checkSyllables, buildMultiReadings, checkHyphens,
  buildAltMap, checkHanji, checkCalqueLighttone, runChecks, CATS, buildLkkMap, checkLkk,
} from "../../docs/check/check-core.js";
import { segment, buildReverseIndex } from "../../docs/thak/js/dict.js?v=26";

test("scanRomanWords: 詞位置準確、數字連字號算內底、-- 無算做詞", () => {
  const text = "我 tsia̍h-pn̄g。";
  const words = scanRomanWords(text);
  assert.equal(words.length, 1);
  assert.deepEqual([words[0].start, words[0].end, words[0].text], [2, 13, "tsia̍h-pn̄g"]);
  assert.equal(text.slice(words[0].start, words[0].end), "tsia̍h-pn̄g");
  assert.deepEqual(
    scanRomanWords("1918 nî, chhó--ê").map((w) => w.text),
    ["nî", "chhó", "ê"],
    "數字毋是詞；-- 隔開兩个詞",
  );
  const w = scanRomanWords(text)[0];
  assert.deepEqual(w.syls.map((s) => s.s), ["tsia̍h", "pn̄g"]);
  assert.deepEqual(w.syls.map((s) => text.slice(s.start, s.end)), ["tsia̍h", "pn̄g"]);
});

test("wordSystem: 標記音節判系統，模糊/無記號算 null", () => {
  assert.equal(wordSystem("tsia̍h"), "tl", "ts");
  assert.equal(wordSystem("tshia"), "tl", "tsh");
  assert.equal(wordSystem("koo"), "tl", "oo");
  assert.equal(wordSystem("kānn"), "tl", "nn");
  assert.equal(wordSystem("guá"), "tl", "ua");
  assert.equal(wordSystem("tsia̍h-pn̄g"), "tl", "ts 標記");
  assert.equal(wordSystem("chheng"), "poj", "ch + eng");
  assert.equal(wordSystem("chhia"), "poj", "chh");
  assert.equal(wordSystem("ko͘"), "poj", "o͘");
  assert.equal(wordSystem("kiaⁿ"), "poj", "ⁿ");
  assert.equal(wordSystem("chôan"), "poj", "oa");
  assert.equal(wordSystem("chia̍h-pn̄g"), "poj", "ch 標記、pn̄g 中性");
  assert.equal(wordSystem("lo̍h"), null, "無特殊記號");
  assert.equal(wordSystem("tsia̍h-chheng"), null, "TL 佮 POJ 標記相沗→模糊");
});

test("convertWord: chia̍h↔tsia̍h、góa↔guá、o͘↔oo、大寫佮連字號有保持", () => {
  assert.equal(convertWord("chia̍h", "tl"), "tsia̍h");
  assert.equal(convertWord("tsia̍h", "poj"), "chia̍h");
  assert.equal(convertWord("góa", "tl"), "guá");
  assert.equal(convertWord("guá", "poj"), "góa");
  assert.equal(convertWord("o͘", "tl"), "oo");
  assert.equal(convertWord("oo", "poj"), "o͘");
  assert.equal(convertWord("kuānn", "poj"), "k\u014Da\u207F", "koāⁿ");
  assert.equal(convertWord("Goá", "tl"), "Guá", "頭字大寫保持");
  assert.equal(convertWord("tsit8-e7", "tl"), "tsi̍t-ē", "數字調抑會轉做調符");
  assert.equal(convertWord("tsiah8-png7", "poj"), "chia̍h-pn̄g");
  assert.equal(convertWord("chheng", "tl"), "tshing");
  assert.equal(convertWord("tshia", "poj"), "chhia");
});

test("checkSystemMixing: 多數 TL、少數 POJ 詞受建議轉 TL；指定目標就反轉；模糊詞毋受點", () => {
  const clean = "guá tshia khì hia";
  assert.deepEqual(checkSystemMixing(clean, "tl"), []);
  assert.deepEqual(checkSystemMixing(clean, null), []);

  const mixed = "guá tshia khì hia chheng";
  const auto = checkSystemMixing(mixed, null);
  assert.equal(auto.length, 1);
  assert.equal(auto[0].start, mixed.indexOf("chheng"));
  assert.equal(auto[0].end, auto[0].start + "chheng".length);
  assert.equal(auto[0].cat, "spelling");
  assert.equal(auto[0].fix, "tshing");
  assert.ok(auto[0].msg.includes("建議"));

  const toPoj = checkSystemMixing(mixed, "poj");
  assert.equal(toPoj.length, 2);
  assert.deepEqual(toPoj.map((i) => i.fix), ["góa", "chhia"]);

  assert.deepEqual(checkSystemMixing("góa chia̍h-pn̄g", null), [], "干焦一種系統就免");
});

test("checkNumericTones: 數字調建議改調符；已經調符就免", () => {
  const iss = checkNumericTones("tsiah8 png7", "tl");
  assert.equal(iss.length, 2);
  assert.deepEqual(iss.map((i) => i.fix), ["tsia̍h", "pn̄g"]);
  assert.equal(iss[0].cat, "spelling");
  assert.ok(iss[0].msg.includes("建議"));

  assert.deepEqual(checkNumericTones("tsia̍h-pn̄g", "tl"), []);
  assert.deepEqual(checkNumericTones("Góa beh khì ha̍k-hāu", "tl"), []);
  const hyph = checkNumericTones("tsit8-e7", "tl");
  assert.equal(hyph.length, 1);
  assert.equal(hyph[0].fix, "tsi̍t-ē");
  const poj = checkNumericTones("tsiah8", "poj");
  assert.equal(poj[0].fix, "chia̍h");
});

test("checkToneFinals: 入聲韻尾配 2/3/5/7/9、無韻尾標第8調攏受點；無 auto-fix", () => {
  const text = "pháh sîk tsiah\u030B kia̍ⁿ o̍o";
  const iss = checkToneFinals(text);
  assert.deepEqual(
    iss.map((i) => text.slice(i.start, i.end)),
    ["pháh", "sîk", "tsiah\u030B", "kia̍ⁿ", "o̍o"],
  );
  for (const i of iss) {
    assert.equal(i.fix, undefined, "無機械改法");
    assert.equal(i.cat, "spelling");
    assert.ok(i.msg.includes("建議"));
  }
  assert.deepEqual(checkToneFinals("phah phah8 sik lo̍h bô tsia̍h mi̍h tsiànn"), []);
});

test("checkMarkPosition: 字母合標準毋過調符囥毋著位→有 fix；已標準/數字調免", () => {
  const iss = checkMarkPosition("tsìah");
  assert.equal(iss.length, 1);
  assert.equal(iss[0].fix, "tsi\u00E0h");
  assert.equal(iss[0].cat, "spelling");
  assert.ok(iss[0].msg.includes("建議"));

  assert.deepEqual(checkMarkPosition("tsi\u00E0h"), []);
  assert.deepEqual(checkMarkPosition("tsia̍h"), []);
  assert.deepEqual(checkMarkPosition("tsuànn"), []);
  assert.deepEqual(checkMarkPosition("Tâi-pak"), [], "大寫專有名詞免");
  const cap = checkMarkPosition("Tsìah");
  assert.equal(cap.length, 1);
  assert.equal(cap[0].fix, "Tsi\u00E0h", "fix 保持頭字大寫");
  const poj = checkMarkPosition("ch\u00F4an");
  assert.equal(poj.length, 1, "POJ 調符位置照管線標準");
  assert.equal(poj[0].fix, "cho\u00E2n");
});

test("checkSpelling: 1–4 合起來、仝 span 照優先權留一條", () => {
  const iss = checkSpelling("guá chhia chheng", "tl");
  assert.deepEqual(iss.map((i) => i.fix), ["tshia", "tshing"]);
  assert.ok(iss.every((i) => i.cat === "spelling"));
  const overlap = checkSpelling("chhia5", "tl");
  assert.equal(overlap.length, 1, "系統+數字調仝詞干焦留一條");
  assert.equal(overlap[0].fix, "tshiâ");
});

const FIXTURE_DICT = {
  "食飯": { r: ["tsiah8 png7"], h: "吃飯" },
  "飯": { r: ["png7", "huan7"], h: "飯" },
  "車": { r: ["tshia1", "ku1"], h: "車" },
};

test("buildSyllableSet/checkSyllables: 詞典外的音節受點、有提 3 个建議", () => {
  const set = buildSyllableSet(FIXTURE_DICT);
  for (const k of ["tsiah", "png", "huan", "tshia", "ku"]) assert.ok(set.has(k), k);
  assert.ok(!set.has("tsiah8"), "存去調鍵");

  const iss = checkSyllables("txiah png7", set);
  assert.equal(iss.length, 1);
  assert.equal(iss[0].cat, "syllable");
  assert.equal(iss[0].fix, undefined);
  assert.ok(iss[0].msg.includes("詞典"));
  assert.ok(iss[0].msg.includes("tsiah"), "建議有距離 1 的合法音節");
  assert.ok(iss[0].msg.split("、").length - 1 <= 2, "頂懸 3 个");
  assert.deepEqual(checkSyllables("tsia̍h png7", set), []);
});

test("buildMultiReadings/checkHyphens: 隔空音節正妙合詞典多音節讀音→建議連字符", () => {
  const multi = buildMultiReadings(FIXTURE_DICT);
  assert.ok(multi.has("tsiah8 png7"));
  assert.ok(![...multi].some((r) => r.split(" ").length < 2), "干焦 2–4 音節");

  const iss = checkHyphens("góa tsia̍h png7", multi);
  assert.equal(iss.length, 1);
  assert.equal(iss[0].cat, "hyphen");
  assert.equal(iss[0].start, "góa tsia̍h png7".indexOf("tsia̍h"));
  assert.equal(iss[0].fix, "tsia̍h-png7", "用原本字串隔連字符");
  assert.ok(iss[0].msg.includes("建議"));

  assert.deepEqual(checkHyphens("tsia̍h-pn̄g", multi), [], "已經有連字符");
  assert.deepEqual(checkHyphens("png7 tsia̍h", multi), [], "顛倒無合");
  assert.deepEqual(checkHyphens("góa tsiah png7", multi), [], "無調無合（照字面比）");

  const m2 = new Set(["sit8 e7"]);
  const iss2 = checkHyphens("sit8 e7 png7", m2);
  assert.deepEqual(iss2.map((i) => i.fix), ["sit8-e7"], "食久向尾掃，毋食落 png7");

  const m4 = new Set(["giu2 giong7 peh8 hang5"]);
  const iss4 = checkHyphens("góa giu2 giong7 peh8 hang5", m4);
  assert.equal(iss4.length, 1);
  assert.equal(iss4[0].fix, "giu2-giong7-peh8-hang5");
});

test("buildAltMap/checkHanji: 干焦獨立出現的異用字受點；重要內底的要免；recAlts 免", () => {
  const items = [
    { word: "袂", tl: "bē", alts: ["𣍐"], recAlts: [] },
    { word: "愛", tl: "ài", alts: ["要"], recAlts: [] },
    { word: "峇", tl: "ba̍t", alts: ["密"], recAlts: ["密"] },
  ];
  const altMap = buildAltMap(items);
  assert.equal(altMap.has("密"), false, "recAlts 毋入去");
  assert.equal(altMap.get("要").word, "愛");
  assert.equal(altMap.get("𣍐").tl, "bē");

  const dict = {
    "重要": { r: ["tiong7 iau3"] }, "要": { r: ["iau3"] }, "我": { r: ["gua2"] },
    "毋過": { r: ["m7 ko3"] }, "去": { r: ["khi3"] },
  };
  const rev = buildReverseIndex(dict);
  const text = "我重要，毋過要去。";
  const segs = segment(text, dict, rev);
  const iss = checkHanji(text, segs, altMap);
  assert.equal(iss.length, 1, "重要 內底的 要 毋受點");
  assert.deepEqual([iss[0].start, iss[0].end], [text.lastIndexOf("要"), text.lastIndexOf("要") + 1]);
  assert.equal(iss[0].cat, "hanji");
  assert.equal(iss[0].fix, "愛");
  assert.equal(iss[0].msg, "教育部推薦用字：愛（ài）");

  const loveDict = { "愛": { r: ["ai3"] } };
  const missSegs = segment("我愛去", loveDict, buildReverseIndex(loveDict));
  assert.equal(checkHanji("我愛去", missSegs, altMap).length, 0, "推薦字本身免");

  const goDict = { "去": { r: ["khi3"] } };
  const segs2 = segment("我要去", goDict, buildReverseIndex(goDict));
  const iss2 = checkHanji("我要去", segs2, altMap);
  assert.equal(iss2.length, 1, "miss seg 嘛算");
  assert.equal(iss2[0].fix, "愛");
});

test("checkCalqueLighttone: 華語直譯長先、無 auto-fix；輕聲有 fix、已標--就免", () => {
  const hints = {
    calque: [
      { han: "時候", suggest: "sî-tsūn" },
      { han: "的時候", suggest: "的時陣（ê sî-tsūn）" },
    ],
    lighttone: [{ han: "轉來", marked: "轉--來", reading: "tng2--lai5" }],
  };
  const iss = checkCalqueLighttone("伊來的時候", hints);
  assert.equal(iss.length, 1, "長的先、重疊免");
  assert.equal(iss[0].cat, "calque");
  assert.deepEqual([iss[0].start, iss[0].end], [2, 5]);
  assert.equal(iss[0].fix, undefined, "直譯干焦建議");
  assert.ok(iss[0].msg.includes("的時陣"));

  assert.deepEqual(checkCalqueLighttone("我轉--來啊。", hints), [], "已經標--");
  const lt = checkCalqueLighttone("我欲轉來啊。", hints);
  assert.equal(lt.length, 1);
  assert.equal(lt[0].cat, "calque");
  assert.equal(lt[0].fix, "轉--來");
  assert.ok(lt[0].msg.includes("輕聲"));
});

test("runChecks: 5–8 干焦佇資料有予的時出現；重疊 span 留頭先那條", () => {
  const text = "guá tsia̍h png7 chheng";
  const bare = runChecks(text, { target: "tl" });
  assert.deepEqual([...new Set(bare.map((i) => i.cat))], ["spelling"], "無詞典干焦拼寫");
  assert.equal(bare.length, 2, "chheng 是 POJ、png7 是數字調");

  const full = runChecks(text, {
    target: "tl",
    syllableSet: buildSyllableSet(FIXTURE_DICT),
    multiReadings: buildMultiReadings(FIXTURE_DICT),
    altMap: new Map(),
    hints: { calque: [], lighttone: [] },
    segments: [],
  });
  assert.ok(full.some((i) => i.cat === "hyphen"), "tsia̍h png7 有連字符建議");
  assert.ok(full.every((i) => i.cat === "hanji" || i.msg.includes("建議")), "語氣干焦建議");

  const overlap = runChecks("tsia̍h png7", {
    target: "tl",
    multiReadings: buildMultiReadings(FIXTURE_DICT),
  });
  assert.ok(overlap.some((i) => i.cat === "hyphen"), "頭先開始的連字符留落來");
  assert.ok(!overlap.some((i) => i.msg.includes("數字調")), "重疊的數字調被 dedupe");

  const cats = new Set(CATS.map(([k]) => k));
  for (const i of full) assert.ok(cats.has(i.cat), `cat ${i.cat} 有佇 CATS`);
});

// ---------- 用字規範 LKK 漢羅（rule 9 ＋ rule 7 的 LKK 講法） ----------
const YONGJI_ITEMS = [
  { word: "按呢", tl: "án-ne", alts: [], lkk: [{ form: "án-ne", kind: "lo" }] },
  { word: "抑是", tl: "a̍h-sī", alts: [], lkk: [{ form: "iah是", kind: "mix" }] },
  { word: "袂", tl: "bē", alts: ["𣍐"], lkk: [{ form: "bē", kind: "lo" }] },
  { word: "遐的", tl: "hia--ê", alts: [], lkk: [{ form: "hia ê", kind: "lo" }, { form: "hia--ê", kind: "lo" }, { form: "hia-ê", kind: "lo" }] },
  { word: "重要", tl: "tiōng-iàu", alts: [], lkk: [{ form: "重要", kind: "han" }] },
];
const LKK_DICT = {
  "伊": { r: ["i1"] }, "按呢": { r: ["an2 ne1"] }, "講": { r: ["kong2"] },
  "按呢生": { r: ["an2 ne1 senn1"] },
  "抑是": { r: ["iah8 si7"] }, "袂": { r: ["be7"] }, "記得": { r: ["ki3 tit8"] },
  "遐的": { r: ["hia1 e5"] }, "冊": { r: ["tsheh4"] }, "重要": { r: ["tiong7 iau3"] },
};
const lkkSeg = (t) => segment(t, LKK_DICT, buildReverseIndex(LKK_DICT));

test("buildLkkMap: 同字的重複項目愛合併、{form,kind} 去重", () => {
  const m = buildLkkMap([...YONGJI_ITEMS,
    { word: "遐的", tl: "hia ê", alts: [], lkk: [{ form: "hia ê", kind: "lo" }, { form: "hia-ê", kind: "lo" }] },
    { word: "漚", tl: "au", alts: [], lkk: [{ form: "au", kind: "lo" }] },
    { word: "漚", tl: "àu", alts: [], lkk: [{ form: "àu", kind: "lo" }] },
  ]);
  assert.equal(m.get("按呢").length, 1);
  assert.equal(m.get("遐的").length, 3, "homograph 項目合併了後猶是 3 个無仝寫法");
  assert.deepEqual(m.get("漚").map((e) => e.form), ["au", "àu"], "無仝讀音的 form 攏收");
});

test("checkLkk: LKK 寫羅馬字／漢羅混的推薦字獨立成詞→建議；長詞內底、han 類免", () => {
  const map = buildLkkMap(YONGJI_ITEMS);
  const t1 = "伊按呢講。";
  const iss = checkLkk(t1, lkkSeg(t1), map);
  assert.equal(iss.length, 1);
  assert.deepEqual([iss[0].start, iss[0].end], [t1.indexOf("按呢"), t1.indexOf("按呢") + 2]);
  assert.equal(iss[0].cat, "hanji");
  assert.equal(iss[0].msg, "LKK 漢羅表建議寫羅馬字：án-ne（教育部推薦漢字：按呢）");
  assert.equal(iss[0].fix, "án-ne");

  const t2 = "抑是按呢？";
  const iss2 = checkLkk(t2, lkkSeg(t2), map);
  assert.equal(iss2.length, 2);
  assert.equal(iss2[0].fix, "iah是");
  assert.equal(iss2[0].msg, "LKK 漢羅表建議漢羅混寫：iah是（教育部推薦漢字：抑是）");

  assert.deepEqual(checkLkk("按呢生", lkkSeg("按呢生"), map), [], "長詞內底毋受點");
  assert.deepEqual(checkLkk("重要", lkkSeg("重要"), map), [], "LKK 寫漢字免");
});

test("checkLkk: 幾若種寫法→列出來、無 auto-fix", () => {
  const map = buildLkkMap(YONGJI_ITEMS);
  const iss = checkLkk("遐的冊", lkkSeg("遐的冊"), map);
  assert.equal(iss.length, 1);
  assert.equal(iss[0].fix, undefined);
  assert.ok(iss[0].msg.includes("hia ê") && iss[0].msg.includes("hia--ê") && iss[0].msg.includes("hia-ê"));
  assert.ok(iss[0].msg.includes("LKK"));
});

test("checkHanji: LKK 模式推薦字愛用 LKK 寫法；預設模式照舊", () => {
  const altMap = buildAltMap([{ word: "袂", tl: "bē", alts: ["𣍐"], recAlts: [] }]);
  const lkkMap = buildLkkMap(YONGJI_ITEMS);
  const t = "我𣍐記得。";
  const segs = lkkSeg(t);
  const moe = checkHanji(t, segs, altMap);
  assert.equal(moe[0].fix, "袂");
  assert.equal(moe[0].msg, "教育部推薦用字：袂（bē）");
  const lkk = checkHanji(t, segs, altMap, { mode: "lkk", lkkMap });
  assert.equal(lkk[0].fix, "bē", "推薦字 LKK 寫羅馬字→直接建議 bē");
  assert.ok(lkk[0].msg.includes("教育部推薦用字：袂（bē）"));
  assert.ok(lkk[0].msg.includes("LKK 漢羅表建議寫「bē」"));
});

test("runChecks: mode 無設／moe→無 LKK 建議；lkk→有", () => {
  const t = "伊按呢講。";
  const base = {
    segments: lkkSeg(t),
    lkkMap: buildLkkMap(YONGJI_ITEMS),
    altMap: new Map(),
    hints: { calque: [], lighttone: [] },
  };
  assert.ok(!runChecks(t, base).some((i) => i.msg.includes("LKK")), "預設模式無 LKK");
  assert.ok(!runChecks(t, { ...base, mode: "moe" }).some((i) => i.msg.includes("LKK")));
  const lkkIss = runChecks(t, { ...base, mode: "lkk" });
  assert.ok(lkkIss.some((i) => i.fix === "án-ne"));
  assert.ok(lkkIss.every((i) => i.cat === "hanji" || i.msg.includes("建議")));
});
