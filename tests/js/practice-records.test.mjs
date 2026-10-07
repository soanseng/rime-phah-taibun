// 網頁試拍練習記錄：存佇瀏覽器 localStorage，記錄袂使漏、袂使無限大、壞去愛會自救。
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRecords, KEY } from "../../docs/try/practice-records.js";

const memStorage = (init = {}) => {
  const m = new Map(Object.entries(init));
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), _m: m };
};
const bank = { kind: "bank", title: "例句庫", url: null };

test("每句隨時寫入，換一个 records 物件（重新整理）嘛讀會著；統計正確率佮字/分", () => {
  const st = memStorage();
  const r = createRecords(st);
  const id = r.startSession("practice", bank);
  r.addSentence(id, { slots: 10, correct: 8, ms: 30000 });
  r.addSentence(id, { slots: 10, correct: 10, ms: 30000 });
  const again = createRecords(st);
  const [s] = again.list();
  assert.equal(s.sentences, 2);
  assert.equal(s.slots, 20);
  assert.equal(s.correct, 18);
  const sum = again.summary();
  assert.equal(sum.sessions, 1);
  assert.equal(sum.sentences, 2);
  assert.equal(sum.accuracy, 0.9);
  assert.equal(sum.cpm, 18, "18 格 / 1 分鐘");
});

test("歷史上濟 500 場，超過就丟上舊的；list 新的先", () => {
  const r = createRecords(memStorage());
  for (let i = 0; i < 505; i++) r.startSession("exam", { ...bank, title: `t${i}` });
  const list = r.list();
  assert.equal(list.length, 500);
  assert.equal(list[0].source.title, "t504");
  assert.equal(list.at(-1).source.title, "t5");
});

test("壞去的 JSON 當做空的，後一擺寫入就修好", () => {
  const st = memStorage({ [KEY]: "{oops" });
  const r = createRecords(st);
  assert.deepEqual(r.list(), []);
  r.setProgress("wikisource:A#一", 3, 12);
  assert.deepEqual(JSON.parse(st.getItem(KEY)).progress["wikisource:A#一"].i, 3);
});

test("讀到佗一句的進度會當存閣讀；clear 清空", () => {
  const st = memStorage();
  const r = createRecords(st);
  r.setProgress("wikipedia:X", 5, 9);
  assert.equal(createRecords(st).getProgress("wikipedia:X").i, 5);
  assert.equal(r.getProgress("nope"), null);
  const id = r.startSession("practice", bank);
  r.addSentence(id, { slots: 3, correct: 3, ms: 1000 });
  assert.match(r.exportJson(), /"history"/);
  r.clear();
  assert.deepEqual(r.list(), []);
  assert.equal(r.getProgress("wikipedia:X"), null);
});
