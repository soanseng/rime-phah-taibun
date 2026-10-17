// 讀文章：漢羅本文 → 台羅／白話字全文（括號註的官方讀音優先，其他用轉換詞典）。
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  officialNumeric,
  romanizeParagraph,
  READ_PROGRESS_KEY,
  READ_MODE_KEY,
  READ_MODES,
  loadReadProgress,
  saveReadProgress,
  markArticleRead,
  unmarkArticleRead,
  isArticleRead,
  loadTextMode,
  saveTextMode,
  articleIdFromHash,
  groupArticles,
  sourceLine,
  rubySegments,
} from "../../docs/read/read-core.js";

const DICT = {
  逐年: { r: ["tak8 ni5"] },
  咱人: { r: ["lan2 lang5"] },
  正月: { r: ["tsiann1 gueh8"] },
  落落來: { r: ["lak4 loh8 lai5"] },
  過: { r: ["kue3"] },
  放: { r: ["pang3"] },
  鳳: { r: ["hong7"] },
};

test("officialNumeric: 手冊台羅轉做詞典格式（數字調、空白分音節），輕聲 -- 保留、1/4 聲補數字", () => {
  assert.equal(officialNumeric("lán-lâng"), "lan2 lang5");
  assert.equal(officialNumeric("iam-ke thàn hong pue"), "iam1 ke1 than3 hong1 pue1");
  assert.equal(officialNumeric("lak--loh-lâi"), "lak4 --loh4 lai5");
  assert.equal(officialNumeric("Hōo-bué"), "hoo7 bue2");
});

test("romanizeParagraph: 官方讀音蓋過詞典，其他照詞典；詞單標 o=官方、miss=查無", () => {
  const out = romanizeParagraph("逐年咱人正月，放過落落來鮕", [{ han: "落落來", tl: "lak--loh-lâi", at: 9 }], DICT);
  assert.equal(out.tl.normalize("NFC"), "Ta̍k-nî lán-lâng tsiann-gue̍h，pàng kuè lak--loh-lâi ⟨鮕⟩".normalize("NFC"));
  assert.match(out.poj.normalize("NFC"), new RegExp("^" + "Ta̍k-nî lán-lâng chiaⁿ-goe̍h，pàng kòe lak--loh-lâi".normalize("NFC")));
  assert.deepEqual(out.words, [
    { h: "逐年", r: "tak8 ni5" },
    { h: "咱人", r: "lan2 lang5" },
    { h: "正月", r: "tsiann1 gueh8" },
    { h: "放", r: "pang3" },
    { h: "過", r: "kue3" },
    { h: "落落來", r: "lak4 --loh4 lai5", o: 1 },
    { h: "鮕", miss: 1 },
  ]);
});

test("romanizeParagraph: 官方讀音佮詞典無仝，以官方為準（鳳 hōng → 手冊寫 hong）", () => {
  const out = romanizeParagraph("鳳", [{ han: "鳳", tl: "hong", at: 0 }], DICT);
  assert.equal(out.tl, "Hong");
  assert.deepEqual(out.words, [{ h: "鳳", r: "hong1", o: 1 }]);
});

// ------- 本機記錄（已讀、顯示模式）：純函式，storage 用假物件 -------
const memStore = () => {
  const m = new Map();
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), _m: m };
};

test("已讀記錄：讀寫 localStorage（read-progress-v1），歹資料當做無讀過", () => {
  const s = memStore();
  assert.deepEqual(loadReadProgress(s), []);
  s.setItem(READ_PROGRESS_KEY, "歹 JSON");
  assert.deepEqual(loadReadProgress(s), []);
  saveReadProgress(s, ["0401-06", "0402-68"]);
  assert.equal(s.getItem(READ_PROGRESS_KEY), JSON.stringify(["0401-06", "0402-68"]));
  assert.deepEqual(loadReadProgress(s), ["0401-06", "0402-68"]);
  assert.equal(READ_PROGRESS_KEY, "read-progress-v1");
});

test("已讀記錄：標記會重號、愛提會掉，isArticleRead 查有查無", () => {
  const s = memStore();
  assert.deepEqual(markArticleRead(s, "0401-06"), ["0401-06"]);
  assert.deepEqual(markArticleRead(s, "0401-06"), ["0401-06"]);
  assert.deepEqual(markArticleRead(s, "0402-68"), ["0401-06", "0402-68"]);
  assert.ok(isArticleRead(loadReadProgress(s), "0401-06"));
  assert.ok(!isArticleRead(loadReadProgress(s), "0401-08"));
  assert.deepEqual(unmarkArticleRead(s, "0401-06"), ["0402-68"]);
  assert.deepEqual(unmarkArticleRead(s, "0402-68"), []);
});

test("顯示模式：預設漢羅，歹值鉤做預設，干焦合法的模式會存", () => {
  const s = memStore();
  assert.equal(loadTextMode(s), "hanlo");
  s.setItem(READ_MODE_KEY, "poj");
  assert.equal(loadTextMode(s), "poj");
  s.setItem(READ_MODE_KEY, "html");
  assert.equal(loadTextMode(s), "hanlo");
  saveTextMode(s, "align");
  assert.equal(loadTextMode(s), "align");
  saveTextMode(s, "xyz");
  assert.equal(loadTextMode(s), "align");
  assert.deepEqual(READ_MODES, ["hanlo", "tl", "poj", "align"]);
});

test("articleIdFromHash：#0401-06 提著 id，其他攏 null", () => {
  assert.equal(articleIdFromHash("#0401-06"), "0401-06");
  assert.equal(articleIdFromHash("#0402-68"), "0402-68");
  for (const bad of ["", "#", "0401-06", "#0401", "#abc-06", "#0401-6x", "#0401-06-x"]) {
    assert.equal(articleIdFromHash(bad), null, bad);
  }
});

test("groupArticles：冊 01 → 02，類照出現順，篇照原順", () => {
  const out = groupArticles([
    { id: "0401-06", book: 1, category: "臺灣好𨑨迌" },
    { id: "0401-08", book: 1, category: "臺灣好食物" },
    { id: "0401-10", book: 1, category: "臺灣好𨑨迌" },
    { id: "0402-42", book: 2, category: "臺灣人情味" },
  ]);
  assert.deepEqual(out.map((b) => b.book), [1, 2]);
  assert.deepEqual(out[0].categories.map((c) => c.name), ["臺灣好𨑨迌", "臺灣好食物"]);
  assert.deepEqual(out[0].categories[0].articles.map((a) => a.id), ["0401-06", "0401-10"]);
  assert.deepEqual(out[1].categories[0].articles.map((a) => a.id), ["0402-42"]);
});

test("sourceLine：教育部電子報—期數（日期）；無日期就莫括號", () => {
  assert.equal(
    sourceLine({ source: { paper: "閱讀越懂閩客語", issue: 571, date: "2013-07-11" } }),
    "教育部電子報—閱讀越懂閩客語571期（2013-07-11）"
  );
  assert.equal(
    sourceLine({ source: { paper: "臺灣閩南語我嘛會", issue: 850, date: null } }),
    "教育部電子報—臺灣閩南語我嘛會850期"
  );
});

test("rubySegments：官方讀音照 codepoint 位置切做 ruby 段，位置歹的跳過", () => {
  assert.deepEqual(rubySegments("逐年咱人正月", [{ han: "咱人", tl: "lán-lâng", at: 2 }]), [
    { t: "text", s: "逐年" },
    { t: "ruby", han: "咱人", tl: "lán-lâng" },
    { t: "text", s: "正月" },
  ]);
  // 𨑨 是 4 位元組字：at 愛照 codepoint 算，毋是 UTF-16
  assert.deepEqual(rubySegments("臺灣好𨑨迌", [{ han: "𨑨迌", tl: "tshit-thô", at: 3 }]), [
    { t: "text", s: "臺灣好" },
    { t: "ruby", han: "𨑨迌", tl: "tshit-thô" },
  ]);
  // 位置無倚（字對袂牢）佮重疊的註解跳過，毋害整段
  assert.deepEqual(
    rubySegments("正月十五", [
      { han: "月", tl: "gue̍h", at: 9 },
      { han: "十五", tl: "tsa̍p-gōo", at: 2 },
    ]),
    [{ t: "text", s: "正月" }, { t: "ruby", han: "十五", tl: "tsa̍p-gōo" }]
  );
});
