// 寫作檢查 規則 10：華語句式 → 台語講法（建議性質）。逐條連去文法筆記（note＝grammar-notes id）。
// 毋是語法解析：干焦收「機械判斷會穩」的句式。規則：
// - re 內底的 (?<k>…) 是受點的字（無 k 就是規个 match）；k 若落佇詞典長詞內底
//   （記得 的 得、實在 的 在、酒吧 的 吧）就袂報——由 check-core 用 segment 結果把關。
// - when(ctx) 會使閣加條件；ctx = { text, start, end, clause }（clause＝k 頭前到句讀的一節）。
// - 語義才判會出的（阮／咱 包無包含聽者、話題句）毋做規則，留佇文法筆記。
const END = "(?=[，。！？、；：,.!?;:」』）)]|\\s*$)"; // 句讀抑是文尾

export const GRAMMAR_RULES = [
  // ---- 疑問句（gi-mun-ku／q-final）----
  {
    note: "q-final",
    re: `(?<k>嗎)${END}`,
    msg: ({ clause }) =>
      /了$/.test(clause) ? "華語「…了嗎？」台語講「…矣未？」（…ah--buē?）。"
      : /有/.test(clause) ? "華語「有…嗎？」台語講「有…無？」（ū…--bô?）抑是「敢有…？」（kám ū）。"
      : "華語句尾「嗎」台語無這个字：講「敢…？」（kám）抑是句尾「…無？」（--bô）。",
  },
  // 「呢？」無做規則：教典台文嘛有句尾「呢」（你袂曉聽呢？ neh），判袂出是華語。
  {
    note: "lah-leh-hoo",
    re: `(?<k>吧)${END}`,
    msg: "華語句尾「吧」台語講「…乎？」（--hooh）、「…啦」（--lah）抑是「…好無？」。",
  },
  { note: "gi-mun-ku", re: "(?<k>誰)", msg: "「誰」台語講「啥人」（siánn-lâng）。", fix: "啥人" },
  { note: "gi-mun-ku", re: "(?<k>哪個|哪一個)", msg: "「哪個」台語講「佗一个」（tó tsi̍t ê）。", fix: "佗一个" },
  { note: "numerals", re: "(?<k>多少)", msg: "「多少」台語講「偌濟」（guā-tsē）。", fix: "偌濟" },
  // ---- 否定、能願（geng-teng-su／e-bue）----
  { note: "e-bue", re: "(?<k>不可以|不能)", msg: "「不能／不可以」台語講「袂使」（bē-sái）抑是「袂當」（bē-tàng）。", fix: "袂使" },
  { note: "e-bue", re: "(?<k>可以)", msg: "「可以」台語講「會使」（ē-sái）抑是「會當」（ē-tàng）。", fix: "會使" },
  { note: "e-bue", re: "(?<k>不會)", msg: "「不會」台語講「袂」（bē）。", fix: "袂" },
  { note: "geng-teng-su", re: "(?<k>不要|別)(?=[\\p{Script=Han}])", msg: "「不要／別」台語講「莫」（mài）抑是「毋通」（m̄-thang）。", fix: "莫" },
  { note: "geng-teng-su", re: "(?<k>不用)", msg: "「不用」台語講「免」（bián）。", fix: "免" },
  { note: "u-bo", re: "(?<k>還沒有|還沒)", msg: "「還沒」台語講「猶未」（iáu-buē）。", fix: "猶未" },
  { note: "u-bo", re: "(?<k>沒有)", msg: "「沒有」台語講「無」（bô）。", fix: "無" },
  { note: "e-bue", re: "(?<k>必須)", msg: "「必須」台語講「著」（tio̍h）抑是「愛」（ài）。" },
  // ---- 時貌（leh-ah-bat／tng-teh）----
  { note: "tng-teh", re: "(?<k>正在)", msg: "「正在」台語講「當咧」（tng-teh）抑是「咧」（leh）。", fix: "當咧" },
  { note: "leh-ah-bat", re: "(?<k>曾經|曾)(?=[\\p{Script=Han}])", msg: "「曾經」台語講「bat」（捌）：我 bat 去過。" },
  // ---- 補語（comp-after）：V得＋補語 → V甲 ----
  {
    note: "comp-after",
    re: "(?<=[\\p{Script=Han}])(?<k>得)(?=[\\p{Script=Han}])",
    msg: "華語「V得…」（跑得很快）台語講「V甲…」（kah）：走甲真緊。",
    fix: "甲",
  },
  // ---- 比較（khah-compare）----
  { note: "khah-compare", re: "(?<k>更)(?=[\\p{Script=Han}])", msg: "「更」台語講「閣較」（koh-khah）。", fix: "閣較" },
  {
    note: "khah-compare",
    re: "(?<k>比)(?<rest>[^，。！？,.!?\\n]{1,8})",
    when: ({ text, end }) => {
      const rest = text.slice(end).split(/[，。！？,.!?\n]/)[0];
      return rest.length > 0 && !/較|khah|閣卡|卡/.test(rest);
    },
    msg: "比較句台語愛有「較」：「A 比 B 較…」（伊比我較懸），抑是「A 較…B」。",
  },
  // ---- 試行（trial）：V一V、V看看 → V看覓 ----
  {
    note: "trial",
    re: "(?<k>(?<v>[\\p{Script=Han}])一\\k<v>)",
    msg: "華語「V一V」（看一看）台語講「V看覓」（khuànn-māi）抑是「V--一下」。",
  },
  { note: "trial", re: "(?<=[\\p{Script=Han}])(?<k>看看)", msg: "「V看看」台語講「V看覓」（khuànn-māi）。", fix: "看覓" },
  // ---- 指示、人稱（deixis／guan-lan-in）----
  { note: "deixis", re: "(?<k>這樣|那樣)", msg: "「這樣／那樣」台語講「按呢」（án-ne）。", fix: "按呢" },
  { note: "deixis", re: "(?<k>這麼)", msg: "「這麼」台語講「遮爾」（tsiah-nī）。", fix: "遮爾" },
  { note: "deixis", re: "(?<k>那麼)", msg: "「那麼」台語講「遐爾」（hiah-nī）。", fix: "遐爾" },
  { note: "guan-lan-in", re: "(?<k>他|她)(?!們)", msg: "「他／她」台語講「伊」（i），無分男女。", fix: "伊" },
  { note: "guan-lan-in", re: "(?<k>我家)", msg: "「我家」台語講「阮兜」（guán tau）——所有格直接黏名詞。", fix: "阮兜" },
  // ---- 時間（numerals）----
  { note: "numerals", re: "(?<k>今天)", msg: "「今天」台語講「今仔日」（kin-á-ji̍t）。", fix: "今仔日" },
  { note: "numerals", re: "(?<k>明天)", msg: "「明天」台語講「明仔載」（bîn-á-tsài）。", fix: "明仔載" },
];

// 詞典長詞 span（[start, end)，2 字以上的 segment 詞）內底的 k 袂報；k 包規个詞（今天＝詞）照報。
export const insideWord = (spans, s, e) =>
  (spans ?? []).some(([ws, we]) => ws < e && s < we && !(s <= ws && we <= e));

// dict.js segment() 結果 → 2 字以上詞典詞（t:"w"）的 span；位置用游標 indexOf 對原文。
export function wordSpans(text, segs) {
  const t = String(text ?? "");
  const spans = [];
  let cursor = 0;
  for (const seg of segs ?? []) {
    const piece = seg.t === "w" ? seg.han : seg.s;
    if (!piece) continue;
    const idx = t.indexOf(piece, cursor);
    if (idx < 0) continue;
    cursor = idx + piece.length;
    if (seg.t === "w" && piece.length > 1) spans.push([idx, cursor]);
  }
  return spans;
}

// 句讀前／文尾（中間會使有句尾語助詞：轉--來--啊、媠--咧）
const PHRASE_END_RE = /^[啊矣啦喔囉乎咧]?\s*(?:[，。！？、；：,.!?;:」』）)]|$)/;
const STRICT_END_RE = /^\s*(?:[，。！？、；：,.!?;:」』）)]|$)/;
// 數詞後壁的「把」是量詞（三把蕹菜 sann pé），毋是華語處置式「把」。
const NUMERAL_RE = /[一二三四五六七八九十兩幾半百千萬]$/;

// hints.calque 的 match 敢欲報：詞典長詞內底的毋報（實在 的 在、不時 的 不）；
// 「了」干焦句讀前（華語句尾 le→矣；句中「洗了」是台語 liáu）；數詞後的「把」毋報。
export function calqueAllowed(text, start, end, han, spans) {
  if (insideWord(spans, start, end)) return false;
  if (han === "了" && !STRICT_END_RE.test(text.slice(end))) return false;
  if (han === "把" && NUMERAL_RE.test(text.slice(0, start))) return false;
  return true;
}

// hints.lighttone 的 match 敢欲報：輕聲佇句尾（tsin tiōng-iàu--ê.），句中「人的心肝」毋是輕聲。
export const lighttoneAllowed = (text, start, end, spans) =>
  !insideWord(spans, start, end) && PHRASE_END_RE.test(text.slice(end));

const COMPILED = GRAMMAR_RULES.map((r) => ({ ...r, rx: new RegExp(r.re, "gdu") }));

// text＋長詞 span → [{ start, end, note, msg, fix? }]（照 start 排）。寫作檢查佮轉換頁共用。
export function findGrammar(text, spans) {
  const t = String(text ?? "");
  const out = [];
  for (const r of COMPILED) {
    r.rx.lastIndex = 0;
    for (const m of t.matchAll(r.rx)) {
      const [start, end] = m.indices.groups?.k ?? m.indices[0];
      if (start === end || insideWord(spans, start, end)) continue;
      const from = Math.max(...["。", "！", "？", "!", "?", "\n", "，", ","].map((p) => t.lastIndexOf(p, start - 1))) + 1;
      const ctx = { text: t, start, end, clause: t.slice(from, start) };
      if (r.when && !r.when(ctx)) continue;
      out.push({
        start, end, note: r.note,
        msg: typeof r.msg === "function" ? r.msg(ctx) : r.msg,
        ...(r.fix ? { fix: r.fix } : {}),
      });
    }
  }
  return out.sort((a, b) => a.start - b.start);
}
