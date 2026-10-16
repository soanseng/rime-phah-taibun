// 拼音發音教學核心（無 DOM）：聽音揀答案出題、對錯、本機進度。
const KEY = "pronounce-progress-v1";

const pick = (arr, rng) => arr[Math.floor(rng() * arr.length) % arr.length];

function shuffle(arr, rng) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1)) % (i + 1);
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/** 對練習題庫揀一題；選項 = 正確答案 + 干擾項（音節表先揀仝一張表的）。 */
export function makeQuestion(quiz, rng = Math.random, n = 4) {
  const item = pick(quiz.pool, rng);
  if (quiz.options) return { item, options: shuffle(quiz.options, rng) };
  const same = item.group ? quiz.pool.filter((p) => p.group === item.group) : quiz.pool;
  const others = [...new Set(same.map((p) => p.answer))].filter((a) => a !== item.answer);
  return { item, options: shuffle([item.answer, ...shuffle(others, rng).slice(0, n - 1)], rng) };
}

export const isCorrect = (q, choice) => choice === q.item.answer;

export function loadProgress(storage) {
  try {
    const p = JSON.parse(storage.getItem(KEY) || "{}");
    return p && typeof p === "object" ? p : {};
  } catch {
    return {};
  }
}

/** 記一課的成績：保留上好的，全對算完成。 */
export function recordResult(storage, lessonId, score, total) {
  const p = loadProgress(storage);
  const prev = p[lessonId];
  if (!prev || score / total >= prev.best / prev.total) {
    p[lessonId] = { best: score, total, done: score === total || Boolean(prev?.done) };
  }
  storage.setItem(KEY, JSON.stringify(p));
  return p;
}

export const audioUrl = (base, name) => base + name;
