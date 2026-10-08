// 檢定練習的進度：弱點卡（間隔複習）、各工具統計、錯誤分類、備份還原。
// 攏存佇瀏覽器 localStorage；換電腦靠匯出／匯入。
import { test } from "node:test";
import assert from "node:assert/strict";
import { createStudy, STUDY_KEY, backupAll, restoreAll, INTERVAL_DAYS } from "../../docs/study/study-store.js";
import { KEY as PRACTICE_KEY } from "../../docs/try/practice-records.js";

const DAY = 86400000;
const memStorage = (init = {}) => {
  const m = new Map(Object.entries(init));
  return {
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => m.set(k, String(v)),
    removeItem: (k) => m.delete(k),
    dump: () => Object.fromEntries(m),
  };
};
const clock = (t0 = Date.UTC(2026, 0, 1)) => {
  let t = t0;
  const now = () => t;
  now.add = (ms) => { t += ms; };
  return now;
};
const card = (id, extra = {}) => ({ id, kind: "reading", front: { h: "飯" }, back: { tl: "pn̄g" }, ...extra });

test("addCard: 新卡今仔日就到期；仝 id 閣錯 → 退轉第一格、錯誤數加一，袂重複", () => {
  const now = clock();
  const st = createStudy(memStorage(), now);
  st.addCard(card("reading:飯|png7"));
  now.add(DAY * 10);
  st.answer("reading:飯|png7", true); // 升到第二格
  st.addCard(card("reading:飯|png7"));
  const all = st.allCards();
  assert.equal(all.length, 1);
  assert.equal(all[0].box, 1);
  assert.equal(all[0].wrong, 2);
  assert.equal(st.dueCards().length, 1);
});

test("answer 著：照格數延後（1、2、4…工）；錯：退第一格、十分鐘後閣出", () => {
  const now = clock();
  const st = createStudy(memStorage(), now);
  st.addCard(card("a"));
  st.answer("a", true);
  assert.equal(st.dueCards().length, 0);
  now.add(INTERVAL_DAYS[0] * DAY - 1);
  assert.equal(st.dueCards().length, 0, "期限未到");
  now.add(1);
  assert.equal(st.dueCards().length, 1);
  assert.equal(st.allCards()[0].last, now() - INTERVAL_DAYS[0] * DAY, "記上尾一擺答的時間（複習頁「7 工內複習過」用）");
  st.answer("a", true);
  assert.equal(st.allCards()[0].box, 3);
  now.add(INTERVAL_DAYS[1] * DAY);
  assert.equal(st.dueCards().length, 1, "第二格等兩工");
  st.answer("a", false);
  const c = st.allCards()[0];
  assert.equal(c.box, 1);
  assert.equal(st.dueCards().length, 0);
  now.add(10 * 60000);
  assert.equal(st.dueCards().length, 1);
});

test("答著上懸到最後一格，袂超過", () => {
  const now = clock();
  const st = createStudy(memStorage(), now);
  st.addCard(card("a"));
  for (let i = 0; i < 20; i++) { st.answer("a", true); now.add(400 * DAY); }
  assert.equal(st.allCards()[0].box, INTERVAL_DAYS.length + 1);
});

test("dueCards 照到期時間排，先到期先出；limit 有效", () => {
  const now = clock();
  const st = createStudy(memStorage(), now);
  st.addCard(card("old"));
  now.add(1000);
  st.addCard(card("new"));
  assert.deepEqual(st.dueCards().map((c) => c.id), ["old", "new"]);
  assert.deepEqual(st.dueCards(1).map((c) => c.id), ["old"]);
});

test("record：各工具題數、答著數累加；logMistake 錯誤分類計數", () => {
  const st = createStudy(memStorage(), clock());
  st.record("iongji", { n: 1, correct: 1 });
  st.record("iongji", { n: 1, correct: 0 });
  st.logMistake("tone");
  st.logMistake("tone");
  st.logMistake("aspiration");
  assert.deepEqual({ ...st.stats().iongji, at: undefined }, { n: 2, correct: 1, at: undefined });
  assert.deepEqual(st.mistakes(), { tone: 2, aspiration: 1 });
});

test("setPos/getPos：各工具讀到佗", () => {
  const st = createStudy(memStorage(), clock());
  assert.equal(st.getPos("hoa2tai"), null);
  st.setPos("hoa2tai", { seed: 7, i: 3 });
  assert.deepEqual(st.getPos("hoa2tai"), { seed: 7, i: 3 });
});

test("壞去的資料當做空的，寫入就修好", () => {
  const storage = memStorage({ [STUDY_KEY]: "{oops" });
  const st = createStudy(storage, clock());
  assert.deepEqual(st.allCards(), []);
  st.addCard(card("a"));
  assert.equal(JSON.parse(storage.getItem(STUDY_KEY)).cards.a.box, 1);
});

test("backupAll／restoreAll：檢定進度、打字練習記錄、自訂文章做伙搬；格式毋著袂蓋掉現有資料", () => {
  const src = memStorage();
  createStudy(src, clock()).addCard(card("a"));
  src.setItem(PRACTICE_KEY, JSON.stringify({ history: [{ id: "x" }], progress: {} }));
  src.setItem("phahtaibun.practice.custom", "我欲去學校。");
  const text = backupAll(src);

  const dst = memStorage({ [STUDY_KEY]: JSON.stringify({ cards: { keep: {} } }) });
  assert.throws(() => restoreAll(dst, "{\"format\":\"other\"}"), /格式/);
  assert.throws(() => restoreAll(dst, "not json"), /格式/);
  assert.ok(JSON.parse(dst.getItem(STUDY_KEY)).cards.keep, "失敗袂動著原本的");

  restoreAll(dst, text);
  assert.equal(createStudy(dst, clock()).allCards()[0].id, "a");
  assert.equal(JSON.parse(dst.getItem(PRACTICE_KEY)).history[0].id, "x");
  assert.equal(dst.getItem("phahtaibun.practice.custom"), "我欲去學校。");
});

test("clear 干焦清檢定進度", () => {
  const storage = memStorage({ [PRACTICE_KEY]: "{}" });
  const st = createStudy(storage, clock());
  st.addCard(card("a"));
  st.clear();
  assert.deepEqual(st.allCards(), []);
  assert.equal(storage.getItem(PRACTICE_KEY), "{}");
});
