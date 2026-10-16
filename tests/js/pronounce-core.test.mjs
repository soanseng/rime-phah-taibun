// 拼音發音教學核心：聽音揀答案出題、對錯、本機進度。
import { test } from "node:test";
import assert from "node:assert/strict";
import { makeQuestion, isCorrect, loadProgress, recordResult, audioUrl } from "../../docs/pronounce/pronounce-core.js";

const seq = (...xs) => { let i = 0; return () => xs[i++ % xs.length]; };
const pool = ["a", "i", "u", "e", "o", "oo"].map((v) => ({ audio: `${v}.mp3`, answer: v }));

test("makeQuestion: 選項有正確答案、無重複、上濟 n 个", () => {
  for (let k = 0; k < 30; k++) {
    const q = makeQuestion({ pool }, Math.random, 4);
    assert.equal(q.options.length, 4);
    assert.equal(new Set(q.options).size, 4);
    assert.ok(q.options.includes(q.item.answer));
  }
});

test("makeQuestion: 答案款數比 n 少就全部列出", () => {
  const small = pool.slice(0, 3);
  const q = makeQuestion({ pool: small }, seq(0.1, 0.5, 0.9), 4);
  assert.deepEqual([...q.options].sort(), ["a", "i", "u"]);
});

test("makeQuestion: 有固定選項（變調）就用固定選項，答案定著佇內底", () => {
  const quiz = { pool: [{ audio: "x.mp3", answer: "第 7 調" }], options: ["第 1 調", "第 2 調", "第 3 調", "第 7 調"] };
  const q = makeQuestion(quiz, Math.random, 4);
  assert.deepEqual([...q.options].sort(), [...quiz.options].sort());
});

test("makeQuestion: 音節表的干擾項先揀仝一張表的", () => {
  const tpool = [
    { audio: "1", answer: "pa", group: "A" }, { audio: "2", answer: "pi", group: "A" },
    { audio: "3", answer: "pu", group: "A" }, { audio: "4", answer: "pe", group: "A" },
    { audio: "5", answer: "pat", group: "B" }, { audio: "6", answer: "pak", group: "B" },
  ];
  for (let k = 0; k < 20; k++) {
    const q = makeQuestion({ pool: tpool }, Math.random, 4);
    const groups = new Set(q.options.map((o) => tpool.find((p) => p.answer === o).group));
    assert.equal(groups.size, 1, q.options.join());
  }
});

test("isCorrect: 只有正確答案算著", () => {
  const q = { item: { answer: "oo" }, options: ["o", "oo"] };
  assert.equal(isCorrect(q, "oo"), true);
  assert.equal(isCorrect(q, "o"), false);
});

test("recordResult: 存上好的成績，換課袂相蓋；壞 JSON 當做無進度", () => {
  const mem = new Map();
  const storage = { getItem: (k) => mem.get(k) ?? null, setItem: (k, v) => mem.set(k, v) };
  recordResult(storage, "vowels", 3, 5);
  recordResult(storage, "vowels", 2, 5);
  recordResult(storage, "tones", 5, 5);
  const p = loadProgress(storage);
  assert.deepEqual(p.vowels, { best: 3, total: 5, done: false });
  assert.deepEqual(p.tones, { best: 5, total: 5, done: true });
  mem.set([...mem.keys()][0], "{壞去");
  assert.deepEqual(loadProgress(storage), {});
});

test("audioUrl: 檔名接佇官方網址後壁", () => {
  assert.equal(audioUrl("https://x/y/", "0101-04-01.mp3"), "https://x/y/0101-04-01.mp3");
});
