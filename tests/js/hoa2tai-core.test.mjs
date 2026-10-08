// 華語→台語造句的純函式：答案對照（overlap）、固定順序（seededOrder）、句長過濾（matchesLength）。
import { test } from "node:test";
import assert from "node:assert/strict";
import { overlap, seededOrder, matchesLength, cardFor } from "../../docs/study/hoa2tai/hoa2tai-core.js";
import { alignSentence } from "../../docs/try/practice-core.js";

test("cardFor: 複習卡身份＝漢字＋正規化讀音；仝華語無仝台語毋通合做一張，仝字無仝音嘛分開", () => {
  const item = (han, tl, gloss) => ({ text: han, gloss, slots: alignSentence(han, tl) });
  const a = cardFor(item("一陣人", "tsi̍t tīn lâng", "一群人"));
  const b = cardFor(item("一篷人", "tsi̍t phâng lâng", "一群人"));
  const c = cardFor(item("重", "tîng", "重複"));
  const d = cardFor(item("重", "tāng", "重量"));
  assert.notEqual(a.id, b.id);
  assert.notEqual(c.id, d.id);
  assert.equal(a.id, cardFor(item("一陣人", "Tsi̍t-tīn lâng", "一群人")).id, "大細字、連字符袂影響身份");
  assert.deepEqual(a.front, { hoa: "一群人" });
  assert.equal(a.back.han, "一陣人");
  assert.equal(a.back.tl, "tsi̍t tīn lâng");
});

test("overlap: 漢字格看使用者答案內底有仝字（位置無拘）", () => {
  const slots = [
    { h: "我", k: "gua", src: "guá" },
    { h: "食", k: "tsiah", src: "tsia̍h" },
    { h: "飯", k: "png", src: "pn̄g" },
  ];
  assert.deepEqual(overlap(slots, "我食飯"), [true, true, true]);
  assert.deepEqual(overlap(slots, "我愛蘋果"), [true, false, false], "無仝字就袂著");
  assert.deepEqual(overlap(slots, "飯我食"), [true, true, true], "位置顛倒嘛算有出現");
});

test("overlap: 羅馬字格照無調音節比，TL 抑是 POJ、有調無調攏會使", () => {
  const slots = [
    { h: null, k: "gua", src: "guá" },
    { h: null, k: "tsiah", src: "tsia̍h" },
  ];
  assert.deepEqual(overlap(slots, "goa tsiah"), [true, true]);
  assert.deepEqual(overlap(slots, "góa tsia̍h"), [true, true], "調符無拘");
  assert.deepEqual(overlap(slots, "goa2 chiah8"), [true, true], "POJ 佮調數字嘛會使");
  assert.deepEqual(overlap(slots, "goa tshe"), [true, false], "無仝音節袂使硬湊");
});

test("overlap: 漢羅混合答案、漢字格嘛會當用羅馬字拍", () => {
  const slots = [
    { h: "我", k: "gua", src: "guá" },
    { h: null, k: "e", src: "ê" },
    { h: "冊", k: "tsheh", src: "tsheh" },
  ];
  assert.deepEqual(overlap(slots, "我ê冊"), [true, true, true]);
  assert.deepEqual(overlap(slots, "góa ê tsheh"), [true, true, true], "全羅嘛算");
  assert.deepEqual(overlap(slots, "我 e tsheh"), [true, true, true], "漢羅嘛算");
});

test("overlap: 讀音不明的漢字格（k=null）干焦看字", () => {
  const slots = [{ h: "喙", k: null, src: "喙" }];
  assert.deepEqual(overlap(slots, "我ê喙齒"), [true]);
  assert.deepEqual(overlap(slots, "tshui-khi"), [false], "無讀音通比，羅馬字袂使算");
});

test("overlap: 空答案逐格攏無著；標點數字無算", () => {
  const slots = [
    { h: "我", k: "gua", src: "guá" },
    { h: "飯", k: "png", src: "pn̄g" },
  ];
  assert.deepEqual(overlap(slots, ""), [false, false]);
  assert.deepEqual(overlap(slots, "。、「」1918"), [false, false]);
});

test("seededOrder: 仝 seed 仝順序、是 0..n-1 的排列、無改著輸入", () => {
  const a = seededOrder(50, 7);
  assert.deepEqual(a, seededOrder(50, 7), "重整了後順序仝款");
  assert.deepEqual([...a].sort((x, y) => x - y), Array.from({ length: 50 }, (_, i) => i), "無重複、無漏");
  assert.notDeepEqual(a, Array.from({ length: 50 }, (_, i) => i), "有洗牌");
  assert.deepEqual(seededOrder(0, 5), []);
  assert.deepEqual(seededOrder(1, 9), [0]);
});

test("seededOrder: 無仝 seed 給無仝順序；seed 0 嘛會使", () => {
  assert.notDeepEqual(seededOrder(50, 7), seededOrder(50, 8));
  const b = seededOrder(50, 0);
  assert.deepEqual([...b].sort((x, y) => x - y), Array.from({ length: 50 }, (_, i) => i));
});

test("matchesLength: 短 ≤6、中 7–12、長 13+、全部", () => {
  assert.equal(matchesLength(3, "short"), true);
  assert.equal(matchesLength(6, "short"), true);
  assert.equal(matchesLength(7, "short"), false);
  assert.equal(matchesLength(7, "mid"), true);
  assert.equal(matchesLength(12, "mid"), true);
  assert.equal(matchesLength(13, "mid"), false);
  assert.equal(matchesLength(13, "long"), true);
  assert.equal(matchesLength(20, "long"), true);
  assert.equal(matchesLength(3, "long"), false);
  assert.equal(matchesLength(3, "all"), true);
  assert.equal(matchesLength(18, "all"), true);
});
