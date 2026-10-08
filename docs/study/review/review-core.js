// 弱點複習核心：讀音答案比對。POJ/TL、調符／數字調攏會，無標調用
// 隱含調（舒聲 1，入聲 -p/-t/-k/-h 是 4）。比毋著就照音節分類錯誤。
import { addImplicitTones, pojToTl, stripTones } from "../../thak/js/roman.js?v=26";

const INITIALS = ["tsh", "ph", "th", "kh", "ts", "ng", "p", "t", "k", "m", "b", "n", "l", "g", "s", "j", "h"];
const ASPIRATED = new Map([
  ["p", "ph"], ["t", "th"], ["k", "kh"], ["ts", "tsh"],
  ["ph", "p"], ["th", "t"], ["kh", "k"], ["tsh", "ts"],
]);
const NASAL_CODA = new Set(["nn", "m", "n", "ng"]);

const initialOf = (toneless) => INITIALS.find((i) => toneless.startsWith(i)) ?? "";
const finalOf = (toneless) => toneless.slice(initialOf(toneless).length);
// 韻拆做（母音，韻尾）：ann→a+nn、ang→a+ng、ai→ai 無韻尾
const finalParts = (final) => final.match(/^(.*?)(nn|ng|m|n|p|t|k|h)?$/).slice(1);

// 兩个帶調數字音節比對：回傳錯誤分類，答著就 null
function classifySyllable(expected, actual) {
  const se = stripTones(expected);
  const sa = stripTones(actual);
  const te = expected.match(/([1-9])$/)?.[1] ?? "";
  const ta = actual.match(/([1-9])$/)?.[1] ?? "";
  if (se === sa) return te === ta ? null : "tone";
  const ie = initialOf(se);
  const ia = initialOf(sa);
  const fe = finalOf(se);
  const fa = finalOf(sa);
  if (ASPIRATED.get(ie) === ia && fe === fa) return "aspiration";
  if (fe === fa) return "initial";
  const [ve, ce] = finalParts(fe);
  const [va, ca] = finalParts(fa);
  if (ve === va && (NASAL_CODA.has(ce) || !ce) && (NASAL_CODA.has(ca) || !ca)) return "nasal";
  if (ie === ia) return "final";
  return "other";
}

const toSyllables = (s) =>
  addImplicitTones(pojToTl(String(s ?? "").trim()).replace(/-/g, " ")).split(/\s+/).filter(Boolean);

// gradeReading("tsiah8", "chia̍h") → { ok: true, categories: [] }
// 拍毋著 → categories 是錯誤分類（tone／aspiration／initial／final／nasal／other），無重複
export function gradeReading(expectedNumeric, input) {
  const expected = toSyllables(expectedNumeric);
  const actual = toSyllables(input);
  if (!actual.length || expected.length !== actual.length) return { ok: false, categories: ["other"] };
  const cats = new Set();
  expected.forEach((syl, i) => {
    const cat = classifySyllable(syl, actual[i]);
    if (cat) cats.add(cat);
  });
  return { ok: cats.size === 0, categories: [...cats] };
}
