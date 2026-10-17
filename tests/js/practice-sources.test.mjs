// 練習來源的純函式：維基網址解析、章節排序、單頁冊切章、《讀文章蓋趣味》文章佮詞彙。
import { test } from "node:test";
import assert from "node:assert/strict";
import { formatRomanization } from "../../docs/thak/js/roman.js?v=26";
import { grade, sylKey } from "../../docs/try/practice-core.js";
import {
  parseWikiInput, naturalCompare, splitChapters, WP_HOST, WS_HOST, seededShuffle, listenItems,
  articleItems, articleVocabItems, articleVocabSource,
} from "../../docs/try/practice-sources.js";

test("parseWikiInput: 兩个閩南語維基的網址解出主機佮標題；其他當做維基百科標題", () => {
  assert.deepEqual(parseWikiInput("https://zh-min-nan.wikisource.org/wiki/Cha%CC%8Dp-h%C4%81ng_Ko%C3%A1n-ki%C3%A0n"),
    { host: WS_HOST, title: "Cha̍p-hāng Koán-kiàn" });
  assert.deepEqual(parseWikiInput("https://zh-min-nan.wikipedia.org/wiki/Ai-ki%CC%8Dp#Le̍k-sú"),
    { host: WP_HOST, title: "Ai-ki̍p" }, "#段落愛拿掉");
  assert.deepEqual(parseWikiInput("Tâi-oân"), { host: WP_HOST, title: "Tâi-oân" });
  assert.equal(parseWikiInput("https://example.com/wiki/X").host, WP_HOST);
});

test("naturalCompare: 章節照數字排（Tē 2 佇 Tē 10 進前）", () => {
  const t = ["Tē 10 hāng", "Tē 1 hāng", "Tē 2 hāng"].sort(naturalCompare);
  assert.deepEqual(t, ["Tē 1 hāng", "Tē 2 hāng", "Tē 10 hāng"]);
});

test("splitChapters: 有 == 標題 == 照標題切；無標題每 30 句一段", () => {
  const ch = splitChapters("Thâu-sū sī án-ne.\n== Tē it Chiuⁿ ==\nKhîm ū chē-chē khoán.\n== Tē jī Chiuⁿ ==\nI lâi ah.\n");
  assert.deepEqual(ch.map((c) => c.name), ["第 1 段", "Tē it Chiuⁿ", "Tē jī Chiuⁿ"]);
  const plain = Array.from({ length: 65 }, (_, i) => `Góa sī ${i} hō.`).join(" ");
  assert.deepEqual(splitChapters(plain).map((c) => c.name), ["第 1 段", "第 2 段", "第 3 段"]);
});

test("seededShuffle: 仝 seed 仝順序（重整網頁進度才對會著），毋過毋是原本的順序", () => {
  const a = Array.from({ length: 50 }, (_, i) => i);
  const s1 = seededShuffle(a, 7);
  assert.deepEqual(s1, seededShuffle(a, 7));
  assert.notDeepEqual(s1, a);
  assert.deepEqual([...s1].sort((x, y) => x - y), a, "攏佇咧、無重複");
  assert.deepEqual(a[0], 0, "原陣列袂予改著");
});

test("listenItems: 聽寫題對齊漢字佮讀音、音檔網址照模組位置；對袂齊的毋收", () => {
  const base = "https://taigi.anatomind.com/try/practice-sources.js";
  const items = listenItems({
    items: [
      { id: "1-2-1", han: "紅嬰仔哭甲一身軀汗。", tl: "Âng-enn-á khàu kah tsi̍t sin-khu kuānn.", hoa: "小嬰兒哭得滿身大汗。", audio: "1-2-1.mp3" },
      { id: "9-9-9", han: "壞去。", tl: "Phāinn", hoa: "", audio: "9-9-9.mp3" },
    ],
  }, base);
  assert.equal(items.length, 1);
  assert.equal(items[0].slots.length, 9);
  assert.equal(items[0].gloss, "小嬰兒哭得滿身大汗。");
  assert.equal(items[0].audio, "https://taigi.anatomind.com/study/audio/1-2-1.mp3");
  assert.equal(items[0].id, "1-2-1");
});

// ---- 《讀文章蓋趣味》文章練習（articleItems）佮文章詞彙聽寫（articleVocabItems）----
// fixtures： struktur 佮 docs/read/data/{articles,roman}.json 仝款
const ART = {
  articles: [
    {
      id: "9901-01", book: 1, page: 6, category: "臺灣好𨑨迌", title: "試驗篇", audio: "audio/9901-01.mp3",
      paragraphs: [
        { text: "「阿公去看戲。伊真歡喜！Pas-taai是神的名。" },
        { text: "好天氣，逐家去𨑨迌，這馬真熱鬧，音樂真響，暗頭仔看天燈，逐擺攏真媠，大家的心情攏真快樂。" },
      ],
      vocab: [
        { n: 1, han: "看戲", tl: "khuànn-hì", hoa: "看戲", audio: "audio/9901-01-01.mp3" },
        { n: 2, han: "做法", tl: "", hoa: "做法", audio: "audio/9901-01-02.mp3" },
        { n: 3, han: "一箸", tl: "tsi̍t", hoa: "一雙筷子", audio: "audio/9901-01-03.mp3" },
      ],
    },
    {
      id: "9902-01", book: 2, page: 8, category: "臺灣心適代", title: "天燈篇", audio: "audio/9902-01.mp3",
      paragraphs: [{ text: "天燈真媠。" }],
      vocab: [{ n: 1, han: "天燈", tl: "thinn-ting", hoa: "孔明燈", audio: "audio/9902-01-01.mp3" }],
    },
  ],
};
const ROM = {
  articles: {
    "9901-01": [
      {
        tl: "", poj: "",
        w: [
          { h: "阿公", r: "a1 kong1" }, { h: "去", r: "khi3" }, { h: "看戲", r: "khuann3 hi3", o: 1 },
          { h: "伊", r: "i1" }, { h: "真", r: "tsin1" }, { h: "歡喜", r: "huann1 hi2" },
          { h: "是", r: "si7" }, { h: "神", r: "sin5" }, { h: "的", r: "e5" }, { h: "名", r: "mia7" },
        ],
      },
      {
        tl: "", poj: "",
        w: [
          { h: "好天氣", r: "ho2 thinn1 khi3" }, { h: "逐家", r: "tak8 ke1" }, { h: "去", r: "khi3" },
          { h: "𨑨迌", miss: 1 },
          { h: "這馬", r: "tsit4 ma2" }, { h: "真", r: "tsin1" }, { h: "熱鬧", r: "jiat8 lau7" },
          { h: "音樂", r: "im1 gak8" }, { h: "真", r: "tsin1" }, { h: "響", r: "hiang2" },
          { h: "暗頭仔", r: "am3 thau5 a2" }, { h: "看", r: "khuann3" }, { h: "天燈", r: "thinn1 ting1" },
          { h: "逐擺", r: "tak8 pai2" }, { h: "攏", r: "long2" }, { h: "真", r: "tsin1" }, { h: "媠", r: "sui2" },
          { h: "大家的", r: "tai7 ke1 e5" }, { h: "心情", r: "sim1 tsiann5" }, { h: "攏", r: "long2" },
          { h: "真", r: "tsin1" }, { h: "快樂", r: "khuai3 lok8" },
        ],
      },
    ],
  },
};

test("articleItems: 照。！？切句、引號黏對爿；來源資訊佮全文音檔", () => {
  const src = articleItems(ART, ROM, "9901-01");
  assert.equal(src.kind, "article");
  assert.equal(src.key, "article:9901-01");
  assert.equal(src.title, "《讀文章蓋趣味》試驗篇");
  assert.equal(src.url, "../read/#9901-01");
  assert.equal(src.license, "著作權屬教育部");
  assert.ok(src.audio.endsWith("/read/audio/9901-01.mp3"), `audio=${src.audio}`);
  // 第一段三句：前引號綴頭一句、後引號綴句尾、拉丁文名照排
  assert.deepEqual(src.items.slice(0, 3).map((x) => x.text), [
    "「阿公去看戲。", "伊真歡喜！", "Pas-taai是神的名。",
  ]);
  // roman.json 無這篇 → 無題目
  assert.deepEqual(articleItems(ART, ROM, "9902-01").items, []);
});

test("articleItems: 格的讀音對 roman.json 的 w（官方詞嘛有）、拍台羅抑是漢字攏著", () => {
  const src = articleItems(ART, ROM, "9901-01");
  const s0 = src.items[0];
  assert.deepEqual(s0.slots.map((x) => x.h), ["阿", "公", "去", "看", "戲"]);
  assert.deepEqual(s0.slots.map((x) => x.k), ["a", "kong", "khi", "khuann", "hi"].map(sylKey));
  assert.equal(s0.slots[3].k, sylKey("khuann3"), "官方詞（o:1）的讀音嘛收入");
  assert.deepEqual(s0.slots.map((x) => x.src), ["a1", "kong1", "khi3", "khuann3", "hi3"].map(formatRomanization));
  assert.ok(s0.autoReading, "自動標音：漢字同音字嘛接受");
  assert.ok(grade(s0.slots, "a kong khi khuann hi").done, "拍去調台羅");
  assert.ok(grade(s0.slots, "阿公去看戲").done, "拍漢字");
  // 漢羅內底的拉丁文（族語名）做羅馬字格
  const s2 = src.items[2];
  assert.deepEqual(s2.slots.slice(0, 2).map((x) => x.h), [null, null]);
  assert.equal(s2.slots[0].k, sylKey("Pas"));
  assert.ok(grade(s2.slots, "Pas taai si sin e mia").done);
});

test("articleItems: 無讀音的詞（miss）逐字無讀音、拍漢字會著；長句照逗號貪婪湊做 ≤30 格", () => {
  const src = articleItems(ART, ROM, "9901-01");
  // 第二段 36 格 > 30 → 湊做兩句（28＋8），照原順序
  const longs = src.items.slice(3);
  assert.equal(longs.length, 2);
  assert.ok(longs[0].text.startsWith("好天氣，") && longs[0].text.endsWith("逐擺攏真媠，"));
  assert.equal(longs[0].text, "好天氣，逐家去𨑨迌，這馬真熱鬧，音樂真響，暗頭仔看天燈，逐擺攏真媠，");
  assert.equal(longs[1].text, "大家的心情攏真快樂。");
  assert.ok(longs[0].slots.length <= 30);
  const tshit = longs[0].slots.filter((x) => x.h === "𨑨" || x.h === "迌");
  assert.equal(tshit.length, 2);
  assert.ok(tshit.every((x) => x.k === null && x.src === x.h), "miss 詞：無讀音、會當拍漢字");
  assert.ok(grade(longs[1].slots, "tai ke e sim tsiann long tsin khuai lok").done);
  assert.ok(grade(longs[0].slots, "好天氣逐家去𨑨迌這馬真熱鬧音樂真響暗頭仔看天燈逐擺攏真媠").done, "拍規句漢字（含 miss 詞）");
});

test("articleVocabItems: 干焦收有台羅、漢字對會齊的詞；音檔照 /read/ 底址；id 有指定干焦彼篇", () => {
  const base = "https://taigi.anatomind.com/read/";
  const all = articleVocabItems(ART, base);
  assert.deepEqual(all.map((x) => x.text), ["看戲", "天燈"]);
  assert.equal(all[0].id, "9901-01-1");
  assert.equal(all[0].gloss, "看戲");
  assert.equal(all[0].audio, "https://taigi.anatomind.com/read/audio/9901-01-01.mp3");
  assert.deepEqual(all[0].slots.map((x) => x.k), [sylKey("khuann3"), sylKey("hi3")]);
  assert.deepEqual(articleVocabItems(ART, base, "9901-01").map((x) => x.text), ["看戲"]);
  assert.deepEqual(articleVocabItems(ART, base, "9902-01").map((x) => x.text), ["天燈"]);
});

// articleVocabSource 的包裝：id 有指定干焦彼篇的詞、title 帶篇名；無指定收規篇（fetch 換做 fixture）
test("articleVocabSource: id 有指定干焦彼篇的詞、title 帶篇名；無指定收兩篇", async () => {
  const real = globalThis.fetch;
  globalThis.fetch = (url) => {
    const u = String(url);
    const json = u.endsWith("articles.json") ? ART : u.endsWith("roman.json") ? ROM : null;
    if (!json) return Promise.reject(new Error(`莫名的 URL：${u}`));
    return Promise.resolve({ ok: true, json: () => Promise.resolve(json) });
  };
  try {
    const one = await articleVocabSource("9901-01");
    assert.equal(one.kind, "listen");
    assert.equal(one.key, "listen-article:9901-01");
    assert.equal(one.title, "《讀文章蓋趣味》詞彙聽寫・試驗篇");
    assert.deepEqual(one.items.map((x) => x.text), ["看戲"]);
    const all = await articleVocabSource();
    assert.equal(all.key, "listen-articles");
    assert.equal(all.items.length, 2);
  } finally {
    globalThis.fetch = real;
  }
});
