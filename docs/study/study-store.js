// 檢定練習的進度：攏存佇使用者家己的瀏覽器（localStorage），無傳去伺服器。
// ① 弱點卡：練習拍毋著、揀毋著的，用間隔複習（Leitner 格仔）閣出題。
//    卡 id 用詞身份（漢字＋正規化讀音），仝一个詞袂重複。
// ② 各工具的題數／答著數、讀到佗（setPos）、錯誤分類計數。
// ③ 備份：檢定進度＋打字練習記錄＋自訂文章做伙匯出，換電腦匯入。
import { KEY as PRACTICE_KEY } from "../try/practice-records.js?v=2";

export const STUDY_KEY = "phahtaibun.study.v1";
const CUSTOM_KEY = "phahtaibun.practice.custom";
const BACKUP_KEYS = [STUDY_KEY, PRACTICE_KEY, CUSTOM_KEY];
// 答著一擺升一格；第 n 格（n≥2）等 INTERVAL_DAYS[n-2] 工才閣出
export const INTERVAL_DAYS = [1, 2, 4, 8, 16, 32];
const MAX_BOX = INTERVAL_DAYS.length + 1;
const DAY = 86400000;
const RETRY_MS = 10 * 60000;

const empty = () => ({ cards: {}, stats: {}, pos: {}, mistakes: {} });

export function createStudy(storage = globalThis.localStorage, now = () => Date.now()) {
  const load = () => {
    try {
      const d = JSON.parse(storage.getItem(STUDY_KEY) ?? "null");
      if (d && typeof d === "object" && d.cards && typeof d.cards === "object") return { ...empty(), ...d };
    } catch {
      // 壞去的 JSON：當做空的，後一擺寫入覆蓋
    }
    return empty();
  };
  const update = (fn) => {
    const d = load();
    const r = fn(d);
    storage.setItem(STUDY_KEY, JSON.stringify(d));
    return r;
  };

  return {
    // card = {id, kind, front, back, src?}；已經有的卡閣錯：退轉第一格
    addCard({ id, kind, front, back, src = null }) {
      update((d) => {
        const t = now();
        const c = d.cards[id];
        if (c) Object.assign(c, { kind, front, back, src: src ?? c.src, box: 1, due: t, wrong: c.wrong + 1 });
        else d.cards[id] = { id, kind, front, back, src, box: 1, due: t, wrong: 1, right: 0, added: t };
      });
    },
    answer(id, ok) {
      update((d) => {
        const c = d.cards[id];
        if (!c) return;
        const t = now();
        c.last = t;
        if (ok) {
          c.box = Math.min(c.box + 1, MAX_BOX);
          c.due = t + INTERVAL_DAYS[c.box - 2] * DAY;
          c.right += 1;
        } else {
          c.box = 1;
          c.due = t + RETRY_MS;
          c.wrong += 1;
        }
      });
    },
    removeCard: (id) => update((d) => { delete d.cards[id]; }),
    allCards: () => Object.values(load().cards),
    dueCards(limit = Infinity) {
      const t = now();
      return Object.values(load().cards)
        .filter((c) => c.due <= t)
        .sort((a, b) => a.due - b.due)
        .slice(0, limit);
    },
    record(tool, { n = 1, correct = 0 } = {}) {
      update((d) => {
        const s = (d.stats[tool] ??= { n: 0, correct: 0, at: null });
        s.n += n;
        s.correct += correct;
        s.at = new Date(now()).toISOString();
      });
    },
    stats: () => load().stats,
    logMistake: (category) => update((d) => { d.mistakes[category] = (d.mistakes[category] ?? 0) + 1; }),
    mistakes: () => load().mistakes,
    setPos: (key, value) => update((d) => { d.pos[key] = value; }),
    getPos: (key) => load().pos[key] ?? null,
    clear: () => storage.setItem(STUDY_KEY, JSON.stringify(empty())),
  };
}

export function backupAll(storage = globalThis.localStorage) {
  const data = {};
  for (const k of BACKUP_KEYS) {
    const v = storage.getItem(k);
    if (v !== null) data[k] = v;
  }
  return JSON.stringify({ format: "phahtaibun-backup", version: 1, at: new Date().toISOString(), data }, null, 2);
}

// 先檢查完才寫：格式毋著就擲錯，原本的資料袂動
export function restoreAll(storage, text) {
  let b;
  try {
    b = JSON.parse(text);
  } catch {
    throw new Error("備份檔格式毋著");
  }
  if (!b || b.format !== "phahtaibun-backup" || !b.data || typeof b.data !== "object") {
    throw new Error("備份檔格式毋著");
  }
  for (const k of BACKUP_KEYS) {
    if (typeof b.data[k] === "string") storage.setItem(k, b.data[k]);
  }
}
