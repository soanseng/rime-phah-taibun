// 練習來源的純函式：維基網址解析、章節排序、單頁冊切章。
import { test } from "node:test";
import assert from "node:assert/strict";
import { parseWikiInput, naturalCompare, splitChapters, WP_HOST, WS_HOST } from "../../docs/try/practice-sources.js";

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
