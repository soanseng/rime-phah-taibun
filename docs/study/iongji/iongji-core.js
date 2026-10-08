// 推薦用字選擇題的題目產生＋LKK 用字表的過濾／搜尋（無 DOM，會當獨立測試）。
// 700 字詞表是 CC BY-NC-ND：干焦新北市900例句（MIT）會當挖空出題；
// 表內的「用例」一律原文顯示（答了後才出現），無挖空。
import { pojToTl, stripTones } from "../../thak/js/roman.js?v=26";
const BLANK = "＿";

// Fisher–Yates：注入 rng 會當固定順序。
export function shuffle(arr, rng = Math.random) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// 共句中頭一个出現的詞挖空：一个字一个 ＿。
function blankSentence(han, word) {
  const i = han.indexOf(word);
  if (i < 0) return han;
  return han.slice(0, i) + BLANK.repeat([...word].length) + han.slice(i + word.length);
}

// item = {word, tl, hoa, alts, examples, sentences}
export function buildQuestion(item, rng = Math.random) {
  const word = item.word;
  // 詞佇頭前，切 4 个一定留著答案
  const options = shuffle([...new Set([word, ...(item.alts ?? [])].filter(Boolean))].slice(0, 4), rng);
  const sents = (item.sentences ?? []).filter((s) => typeof s?.[0] === "string" && s[0].includes(word));
  if (sents.length) {
    const [han, tl] = sents[Math.min(sents.length - 1, Math.floor(rng() * sents.length))];
    return { prompt: blankSentence(han, word), blankedFrom: [han, tl], options, answer: word, item };
  }
  return { prompt: `「${item.hoa}」，台語讀做 ${item.tl}，推薦寫法是？`, options, answer: word, item };
}

// 搜尋鍵：台羅／白話字／調號數字攏會著（揣讀音用）。
export function tlKey(s) {
  if (!s) return "";
  return stripTones(pojToTl(String(s)))
    .toLowerCase()
    .replace(/[0-9]/g, "")
    .replace(/[-\s]+/g, "");
}

// 徽章：主分類照 LKK type（◆ 寫漢字＝type: han，含漢羅混；★ 寫羅馬字＝type: lo）
export function lkkKindLabel(kind) {
  return { han: "◆ 漢字", lo: "★ 羅馬字", mix: "◆ 漢羅混" }[kind] ?? kind;
}

// 予選擇題回饋顯示：「a̍h（寫羅馬字）」；仝款寫法的 form 鬥做伙。
export function lkkText(item) {
  const forms = item?.lkk ?? [];
  if (!forms.length) return null;
  const parts = [];
  for (const f of forms) {
    const label = f.kind === "han" ? "（◆ 寫漢字）" : f.kind === "lo" ? "（★ 寫羅馬字）" : "（◆ 寫漢字，漢羅混寫）";
    const last = parts[parts.length - 1];
    if (last && last.label === label) last.forms.push(f.form);
    else parts.push({ label, forms: [f.form] });
  }
  return parts.map((p) => `${p.forms.join("、")}${p.label}`).join("、");
}

// kind：han／lo／mix 是 LKK 寫法的字面樣式；hantype＝LKK 表的 type: han（有漢字就算，
// 寫漢字＋漢羅混），佮輸入法候選的 ◆ 範圍仝款
export function lkkHas(item, kind) {
  if (kind === "all") return true;
  const kinds = kind === "hantype" ? ["han", "mix"] : [kind];
  return (item?.lkk ?? []).some((f) => kinds.includes(f.kind));
}

function textMatch(item, query) {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return (
    item.word.toLowerCase().includes(q) ||
    (item.hoa ?? "").toLowerCase().includes(q) ||
    tlKey(item.tl).includes(tlKey(q))
  );
}

export function filterWords(items, { kind = "all", query = "" } = {}) {
  return items.filter((it) => lkkHas(it, kind) && textMatch(it, query));
}

export function lkkCounts(items, query = "") {
  const hit = items.filter((it) => textMatch(it, query));
  return {
    all: hit.length,
    han: hit.filter((it) => lkkHas(it, "han")).length,
    lo: hit.filter((it) => lkkHas(it, "lo")).length,
    mix: hit.filter((it) => lkkHas(it, "mix")).length,
    hantype: hit.filter((it) => lkkHas(it, "hantype")).length,
  };
}
