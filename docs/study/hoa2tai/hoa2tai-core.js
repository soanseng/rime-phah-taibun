// 華語→台語造句的純函式（無 DOM；tests/js/hoa2tai-core.test.mjs 直接試）。
import { tokenize, readingOf } from "../../try/practice-core.js?v=2";
import { seededShuffle } from "../../try/practice-sources.js?v=3";
import { pojToTl, addImplicitTones } from "../../thak/js/roman.js?v=26";

// 弱點複習卡：身份＝（漢羅原句, 正規化數字調 TL），華語仝款的無仝台語句袂合做一張
export function cardFor(item) {
  const numeric = item.slots
    .filter((s) => s.k != null)
    .map((s) => addImplicitTones(pojToTl(s.src.normalize("NFC"))))
    .join(" ");
  return {
    id: `hoa2tai:${item.text}|${numeric}`,
    kind: "hoa2tai",
    front: { hoa: item.gloss },
    back: { han: item.text, tl: item.slots.map((s) => readingOf(s, false)).filter(Boolean).join(" ") },
  };
}

// 參考答案佮使用者答案的對照：翻譯毋是唯一，所以毋評對錯，干焦標「仝款有出現」的格。
// 漢字格：家己的字有出現佇答案內底；羅馬字格：去調音節（sylKey）有出現佇答案的羅馬音節內底。
export function overlap(slots, userText) {
  const toks = tokenize(userText);
  const han = new Set(toks.filter((t) => t.h).map((t) => t.h));
  const keys = new Set(toks.filter((t) => t.k).map((t) => t.k));
  return slots.map((s) => (s.h != null && han.has(s.h)) || (s.k != null && keys.has(s.k)));
}

// 固定 seed 的洗牌順序：重整了後順序仝款，存落的進度（第幾句）才對會著。
export const seededOrder = (n, seed) => seededShuffle(Array.from({ length: n }, (_, i) => i), seed);

// 句長過濾（格數）：短 ≤6、中 7–12、長 13+。
export function matchesLength(n, filter) {
  if (filter === "short") return n <= 6;
  if (filter === "mid") return n >= 7 && n <= 12;
  if (filter === "long") return n >= 13;
  return true;
}
