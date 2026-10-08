// 學習單核心（無 DOM）：揀句佮版型資料結構，畫圖佇 worksheet.js。
// import 指定字串佮練習頁仝款（?v=2／?v=26），模組才袂載兩擺。
import { readingOf } from "../../try/practice-core.js?v=2";
import { isHan } from "../../thak/js/dict.js?v=26";

// 揀 n 句：有華語釋義的優先（華語→台語版型佮老師改攏愛）；部分 Fisher–Yates 免重複。
export function pickBankItems(items, n, rng = Math.random) {
  const glossed = items.filter((it) => it.gloss);
  const pool = glossed.length >= n ? glossed : items;
  const take = Math.min(n, pool.length);
  const arr = pool.slice();
  for (let i = 0; i < take; i++) {
    const j = i + Math.floor(rng() * (arr.length - i));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr.slice(0, take);
}

// 讀音行：逐格 readingOf；讀音無明的漢字格毋通洘底（＿＿），答案頁（reveal）才看會著。
// 標點綴佇前一音後壁，免空白。
const NO_SPACE_BEFORE = /^[.,;:!?…、。！？；：%）》」』]/u;
function lineReading(slots, poj, reveal) {
  let out = "";
  for (const s of slots) {
    const part = readingOf(s, poj) ?? (s.h && isHan(s.h) && !reveal ? "＿＿" : s.src);
    if (!out || NO_SPACE_BEFORE.test(part)) out += part;
    else out += ` ${part}`;
  }
  return out;
}

// 版型：pair 對照（漢羅上、讀音下）、roman 顯示漢羅寫羅馬字、
// hanji 顯示讀音寫漢字、gloss 華語→台語（干焦例句庫有華語）。
export function buildSheet(items, { type = "pair", poj = false, answers = false } = {}) {
  const rows = [];
  const answerRows = [];
  for (const it of items ?? []) {
    const slots = it.slots ?? [];
    if (type === "roman") rows.push({ kind: "roman", han: it.text, lines: 1 });
    else if (type === "hanji") {
      rows.push({
        kind: "hanji",
        roman: lineReading(slots, poj, false),
        boxes: slots.filter((s) => s.h && isHan(s.h)).length,
      });
    } else if (type === "gloss") rows.push({ kind: "gloss", gloss: it.gloss ?? "", lines: 2 });
    else {
      rows.push({ kind: "pair", cells: slots.map((s) => ({ top: s.h ?? s.src, reading: readingOf(s, poj) })) });
    }
    if (answers) answerRows.push({ han: it.text, roman: lineReading(slots, poj, true) });
  }
  return { type, rows, answers: answerRows };
}
