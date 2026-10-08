// 練習來源的純函式：維基網址解析、章節排序、單頁冊切章。
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  parseWikiInput, naturalCompare, splitChapters, WP_HOST, WS_HOST, seededShuffle, listenItems,
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
