// 推薦用字選擇題的題目產生（無 DOM，會當獨立測試）。
// 700 字詞表是 CC BY-NC-ND：干焦新北市900例句（MIT）會當挖空出題；
// 表內的「用例」一律原文顯示（答了後才出現），無挖空。
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
