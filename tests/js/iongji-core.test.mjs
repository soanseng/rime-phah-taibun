// 推薦用字選擇題：題目產生（挖空、選項、無例句時的備用問法）＋LKK 用字表的過濾／搜尋。
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  buildQuestion, shuffle,
  tlKey, lkkKindLabel, lkkText, lkkHas, filterWords, lkkCounts,
} from "../../docs/study/iongji/iongji-core.js";

// 固定種子的 rng，順序才會當重現。
const seeded = (s) => () => {
  s = (s * 1664525 + 1013904223) >>> 0;
  return s / 4294967296;
};

test("shuffle: 仝一个種子得著仝一个順序，而且無加減元素", () => {
  const a = shuffle([1, 2, 3, 4, 5], seeded(7));
  const b = shuffle([1, 2, 3, 4, 5], seeded(7));
  assert.deepEqual(a, b);
  assert.deepEqual([...a].sort(), [1, 2, 3, 4, 5]);
});

test("buildQuestion: 挖句內面頭一个出現的詞，一个字一个 ＿", () => {
  const item = {
    word: "的",
    tl: "ê",
    hoa: "的",
    alts: ["个"],
    examples: ["我的冊"],
    sentences: [["我的冊佮你的筆", "guá ê tsheh kah lí ê pit"]],
  };
  const q = buildQuestion(item, seeded(1));
  assert.equal(q.prompt, "我＿冊佮你的筆");
  assert.deepEqual(q.blankedFrom, ["我的冊佮你的筆", "guá ê tsheh kah lí ê pit"]);
  assert.equal(q.answer, "的");
  assert.equal(q.item, item);
});

test("buildQuestion: 多字詞挖空，字數个 ＿", () => {
  const item = {
    word: "抑是",
    tl: "a̍h-sī",
    hoa: "或是、或者",
    alts: ["益是"],
    examples: ["好抑是毋好"],
    sentences: [["你欲啉咖啡抑是欲啉茶？", "Lí beh lim ka-pi ia̍h-sī beh lim-tê?"]],
  };
  const q = buildQuestion(item, seeded(2));
  assert.equal(q.prompt, "你欲啉咖啡＿＿欲啉茶？");
  assert.deepEqual(q.blankedFrom, ["你欲啉咖啡抑是欲啉茶？", "Lí beh lim ka-pi ia̍h-sī beh lim-tê?"]);
});

test("buildQuestion: 一句內面拄著兩擺，干焦挖頭一个", () => {
  const item = {
    word: "人", tl: "lâng", hoa: "人", alts: ["儂"],
    sentences: [["台灣人講台灣人的話", "Tâi-uân-lâng kóng Tâi-uân-lâng ê uē"]],
  };
  const q = buildQuestion(item, seeded(3));
  assert.equal(q.prompt, "台灣＿講台灣人的話");
});

test("buildQuestion: 無句仔（抑是句仔內面無彼个詞）用備用問法", () => {
  const item = { word: "壓霸", tl: "ah-pà", hoa: "霸道", alts: ["惡霸"], examples: ["真壓霸"], sentences: [] };
  const q = buildQuestion(item, seeded(4));
  assert.equal(q.prompt, "「霸道」，台語讀做 ah-pà，推薦寫法是？");
  assert.equal(q.blankedFrom, undefined);
  assert.ok(q.options.includes("壓霸"));

  const noHit = buildQuestion(
    { ...item, sentences: [["無關係的句", "bô koan-hē ê kù"]] },
    seeded(4),
  );
  assert.equal(noHit.blankedFrom, undefined);
  assert.equal(noHit.prompt, "「霸道」，台語讀做 ah-pà，推薦寫法是？");
});

test("buildQuestion: 選項上濟 4 个、一定含答案、無重複", () => {
  const item = {
    word: "雜", tl: "tsa̍p", hoa: "雜", examples: ["雜"],
    alts: ["a", "b", "c", "d", "e"],
    sentences: [["真雜", "tsin tsa̍p"]],
  };
  for (let s = 1; s <= 20; s++) {
    const q = buildQuestion(item, seeded(s));
    assert.equal(q.options.length, 4);
    assert.ok(q.options.includes("雜"));
    assert.equal(new Set(q.options).size, q.options.length);
  }
  const two = buildQuestion(
    { ...item, alts: ["gg"] },
    seeded(5),
  );
  assert.equal(two.options.length, 2);
  assert.deepEqual([...two.options].sort(), ["gg", "雜"]);
});

test("buildQuestion: 仝一个種子得著仝一个題目", () => {
  const item = {
    word: "袂", tl: "bē", hoa: "不會", alts: ["𣍐", "未"],
    sentences: [["我袂去", "guá bē khì"], ["你袂來", "lí bē lâi"]],
  };
  const a = buildQuestion(item, seeded(11));
  const b = buildQuestion(item, seeded(11));
  assert.deepEqual(a, b);
  assert.ok(item.sentences.some((s) => s[0] === a.blankedFrom?.[0]));
});

test("buildQuestion: 真實資料 229 項攏生會出合法的題目", () => {
  const { items } = JSON.parse(
    readFileSync(new URL("../../docs/study/data/iongji.json", import.meta.url), "utf8"),
  );
  assert.equal(items.length, 229);
  for (const item of items) {
    const q = buildQuestion(item, seeded(item.word.charCodeAt(0) + 1));
    assert.ok(typeof q.prompt === "string" && q.prompt.length > 0, item.word);
    assert.equal(q.answer, item.word);
    assert.ok(q.options.includes(item.word), item.word);
    assert.ok(q.options.length <= 4 && q.options.length >= 1);
    assert.equal(q.item, item);
    assert.ok(!q.prompt.includes("undefined"), item.word);
    if (q.blankedFrom) {
      const han = q.blankedFrom[0];
      const idx = han.indexOf(item.word);
      assert.ok(idx >= 0, item.word);
      assert.equal(
        q.prompt,
        han.slice(0, idx) + "＿".repeat([...item.word].length) + han.slice(idx + item.word.length),
        item.word,
      );
    } else {
      assert.equal(q.prompt, `「${item.hoa}」，台語讀做 ${item.tl}，推薦寫法是？`, item.word);
    }
  }
});

test("tlKey: 台羅／白話字／調號數字攏揣會著", () => {
  assert.equal(tlKey("tshuì-phué"), "tshuiphue");
  assert.equal(tlKey("tshui-phue"), "tshuiphue");
  assert.equal(tlKey("chhui-phoe"), "tshuiphue"); // POJ 拼寫
  assert.equal(tlKey("tshui-phue7"), "tshuiphue"); // 調號數字
  assert.equal(tlKey("hia--ê"), "hiae"); // 輕聲連字號
  assert.equal(tlKey(""), "");
  assert.equal(tlKey(null), "");
});

test("lkkKindLabel: 主分類照 LKK type（漢羅混算 ◆ 寫漢字）", () => {
  assert.ok(lkkKindLabel("mix").startsWith("◆"));
  assert.ok(lkkKindLabel("han").startsWith("◆"));
  assert.ok(lkkKindLabel("lo").startsWith("★"));
});

test("lkkText: 仝一種寫法的 form 鬥做伙，無收就 null", () => {
  assert.equal(lkkText({ lkk: [{ form: "a̍h", kind: "lo" }] }), "a̍h（★ 寫羅馬字）");
  assert.equal(
    lkkText({ lkk: [{ form: "阿", kind: "han" }, { form: "仔", kind: "han" }] }),
    "阿、仔（◆ 寫漢字）",
  );
  assert.equal(
    lkkText({ lkk: [{ form: "leh/teh", kind: "lo" }, { form: "--leh", kind: "lo" }] }),
    "leh/teh、--leh（★ 寫羅馬字）",
  );
  assert.equal(lkkText({ lkk: [{ form: "iah是", kind: "mix" }] }), "iah是（◆ 寫漢字，漢羅混寫）");
  assert.equal(lkkText({ lkk: [] }), null);
  assert.equal(lkkText({}), null);
});

test("lkkHas: all 攏有；無收的干焦 all 會著", () => {
  const item = { lkk: [{ form: "a̍h", kind: "lo" }] };
  assert.equal(lkkHas(item, "all"), true);
  assert.equal(lkkHas(item, "lo"), true);
  assert.equal(lkkHas(item, "han"), false);
  assert.equal(lkkHas({ lkk: [] }, "all"), true);
  assert.equal(lkkHas({ lkk: [] }, "han"), false);
  assert.equal(lkkHas({}, "lo"), false);
});

test("filterWords: 揀 kind 閣會當照漢字／讀音／華語揣", () => {
  const items = [
    { word: "喙䫌", tl: "tshuì-phué", hoa: "臉頰", lkk: [{ form: "喙䫌", kind: "han" }] },
    { word: "按呢", tl: "án-ne", hoa: "這樣", lkk: [{ form: "án-ne", kind: "lo" }] },
    { word: "紅kì-kì", tl: "âng-kì-kì", hoa: "紅通通", lkk: [{ form: "紅kì-kì", kind: "mix" }] },
    { word: "無收的", tl: "bô", hoa: "—", lkk: [] },
  ];
  assert.equal(filterWords(items).length, 4);
  assert.equal(filterWords(items, { kind: "lo" }).length, 1);
  assert.equal(filterWords(items, { kind: "lo" })[0].word, "按呢");
  assert.deepEqual(
    filterWords(items, { query: "臉頰" }).map((x) => x.word),
    ["喙䫌"],
  );
  assert.deepEqual(filterWords(items, { query: "an-ne" }).map((x) => x.word), ["按呢"]); // 調號無要緊
  assert.deepEqual(filterWords(items, { query: "án-ne" }).map((x) => x.word), ["按呢"]);
  assert.equal(filterWords(items, { query: "  " }).length, 4); // 空白當做無條件
  assert.deepEqual(
    filterWords(items, { kind: "mix", query: "紅通通" }).map((x) => x.word),
    ["紅kì-kì"],
  );
  // 「含漢字」＝LKK type: han（輸入法 ◆ 的範圍）：寫漢字佮漢羅混攏算
  assert.deepEqual(filterWords(items, { kind: "hantype" }).map((x) => x.word), ["喙䫌", "紅kì-kì"]);
});

test("lkkCounts: 照搜尋字算各種寫法的數量", () => {
  const items = [
    { word: "a", tl: "a", hoa: "", lkk: [{ form: "a", kind: "han" }] },
    { word: "b", tl: "b", hoa: "", lkk: [{ form: "b", kind: "lo" }] },
    { word: "c", tl: "c", hoa: "", lkk: [{ form: "c", kind: "lo" }] },
    { word: "d", tl: "d", hoa: "", lkk: [] },
  ];
  assert.deepEqual(lkkCounts(items, ""), { all: 4, han: 1, lo: 2, mix: 0, hantype: 1 });
  assert.deepEqual(lkkCounts(items, "a"), { all: 1, han: 1, lo: 0, mix: 0, hantype: 1 });
});

test("yongji 真實資料：700 字攏會當揣著，數量佇表一致", () => {
  const { items } = JSON.parse(
    readFileSync(new URL("../../docs/study/data/yongji.json", import.meta.url), "utf8"),
  );
  assert.equal(items.length, 700);
  for (const it of items) {
    assert.ok(typeof it.word === "string" && it.word.length > 0);
    assert.ok(typeof it.tl === "string");
    for (const f of it.lkk) assert.ok(["han", "lo", "mix"].includes(f.kind), `${it.word} ${f.kind}`);
  }
  // 229 个練習題的詞攏佇表內
  const bank = JSON.parse(
    readFileSync(new URL("../../docs/study/data/iongji.json", import.meta.url), "utf8"),
  );
  const words = new Set(items.map((x) => x.word));
  for (const it of bank.items) assert.ok(words.has(it.word), it.word);
});
