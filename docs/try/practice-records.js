// 練習記錄：攏存佇使用者家己的瀏覽器（localStorage），無傳去伺服器。
// 每句完成就寫入，關分頁袂漏；歷史上濟 500 場；壞去的資料當做空的。
export const KEY = "phahtaibun.practice.v1";
const MAX_HISTORY = 500;

export function createRecords(storage = globalThis.localStorage) {
  const load = () => {
    try {
      const d = JSON.parse(storage.getItem(KEY) ?? "null");
      if (d && Array.isArray(d.history) && d.progress && typeof d.progress === "object") return d;
    } catch {
      // 壞去的 JSON：當做空的，後一擺寫入覆蓋
    }
    return { history: [], progress: {} };
  };
  const save = (d) => storage.setItem(KEY, JSON.stringify(d));
  const update = (fn) => {
    const d = load();
    fn(d);
    save(d);
  };

  return {
    startSession(mode, source) {
      const id = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
      update((d) => {
        d.history.push({ id, at: new Date().toISOString(), mode, source, sentences: 0, slots: 0, correct: 0, ms: 0 });
        if (d.history.length > MAX_HISTORY) d.history.splice(0, d.history.length - MAX_HISTORY);
      });
      return id;
    },
    addSentence(id, { slots, correct, ms }) {
      update((d) => {
        const s = d.history.find((x) => x.id === id);
        if (!s) return;
        s.sentences += 1;
        s.slots += slots;
        s.correct += correct;
        s.ms += ms;
      });
    },
    list: () => load().history.slice().reverse(),
    summary() {
      const h = load().history;
      const sum = (f) => h.reduce((a, s) => a + s[f], 0);
      const slots = sum("slots");
      const ms = sum("ms");
      return {
        sessions: h.length,
        sentences: sum("sentences"),
        accuracy: slots ? sum("correct") / slots : 0,
        cpm: ms ? sum("correct") / (ms / 60000) : 0,
      };
    },
    setProgress(key, i, n) {
      update((d) => {
        d.progress[key] = { i, n, at: new Date().toISOString() };
      });
    },
    getProgress: (key) => load().progress[key] ?? null,
    exportJson: () => JSON.stringify(load(), null, 2),
    clear: () => save({ history: [], progress: {} }),
  };
}
