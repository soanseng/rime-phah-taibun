// 練習分頁：詞語（看漢字拍台羅）＋句子（整句逐詞免調比對；錯題加重抽樣）。

import { practicePool, normalizeAnswer, readingToneless, sutianUrl } from "../dict.js?v=17";
import { formatRomanization, tlToPoj, pojFixDiacritics, toNumeric } from "../roman.js?v=17";

const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const revealHtml = (cur) =>
  `${formatRomanization(cur.r[0])}（POJ：${pojFixDiacritics(formatRomanization(tlToPoj(cur.r[0])))}）　<a class='dict-link' href='${sutianUrl(cur.han)}' target='_blank' rel='noopener'>教典</a>`;

export function initPractice(dict) {
  const pool = practicePool(dict);
  let cur = null;
  let ok = 0;
  let asked = 0;

  const show = (r) =>
    `${formatRomanization(r)}（POJ：${pojFixDiacritics(formatRomanization(tlToPoj(r)))}）`;

  const next = () => {
    cur = pool[Math.floor(Math.random() * pool.length)];
    $("#pr-han").text(cur.han);
    $("#pr-gloss").text(cur.h ? `提示：${cur.h}` : "");
    $("#pr-in").val("").trigger("focus");
    $("#pr-feedback").empty().removeClass("good bad");
  };

  const feedback = (text, cls) =>
    $("#pr-feedback").removeClass("good bad").addClass(cls).text(text);

  const check = () => {
    if (!cur) return;
    const ans = normalizeAnswer($("#pr-in").val());
    if (!ans.numeric) return;
    asked++;
    const match = cur.r.find((r) => readingToneless(r) === ans.toneless);
    if (match) {
      ok++;
      const toneMismatch = ans.hasTones && stripDigits(match) !== stripDigits(ans.numeric);
      $("#pr-feedback").removeClass("bad").addClass("good")
        .html(toneMismatch
          ? `詞對，調號愛改：${show(match)}${revealHtml(cur)}`
          : `正確！${ans.hasTones ? show(match) + revealHtml(cur) : "免調嘛會過。"}`);
    } else {
      feedback("毋對，閣試一擺，抑是點「看答案」。", "bad");
    }
    $("#pr-score").text(`${ok} 對 / ${asked} 題`);
  };

  $("#pr-check").on("click", check);
  $("#pr-in").on("keydown", (e) => {
    if (e.key === "Enter") check();
  });
  $("#pr-show").on("click", () =>
    cur && $("#pr-feedback").removeClass("bad").addClass("good")
      .html(`答案：${cur.han} = ${show(cur.r[0])}${revealHtml(cur)}`));
  $("#pr-next").on("click", next);
  next();
}

// ---- 句子模式 ----
const PUNCT = /[，。、！？；：,.!?;:…「」『』（）()]/g;
const wordToneless = (t) => {
  // 變音符/數字調 攏通：toNumeric 了後除掉調數佮連字符
  let s = toNumeric(t.toLowerCase());
  return s.replace(/[0-9\-]/g, "");
};
const sentWords = (tl) =>
  tl.replace(PUNCT, " ").split(/\s+/).filter((w) => /[a-z0-9]/i.test(w));

export async function initSentencePractice() {
  let sents = [];
  try {
    const r = await fetch("../data-public/sentences.json");
    sents = (await r.json()).s ?? [];
  } catch { /* 載入失敗：句模式無題庫 */ }
  if (!sents.length) {
    $("#ps-han").text("句庫載入失敗");
    return;
  }
  let idx = -1;
  const missPool = new Set();   // 錯題加重抽樣
  let okSent = 0, askedSent = 0;

  const next = () => {
    if (missPool.size && Math.random() < 0.5) {
      idx = [...missPool][Math.floor(Math.random() * missPool.size)];
    } else {
      idx = Math.floor(Math.random() * sents.length);
    }
    $("#ps-han").text(sents[idx][0]);
    $("#ps-hint").text(sents[idx][2] ? `華語：${sents[idx][2]}` : "");
    $("#ps-in").val("").trigger("focus");
    $("#ps-feedback").empty().removeClass("good bad");
  };

  const check = () => {
    if (idx < 0) return;
    const exp = sentWords(sents[idx][1]);
    const got = sentWords($("#ps-in").val());
    if (!got.length) return;
    askedSent++;
    let ok = 0;
    const marks = exp.map((w, i) => {
      if (i < got.length && wordToneless(got[i]) === wordToneless(w)) { ok++; return `<span class="w-ok">${esc(w)}</span>`; }
      return `<span class="w-bad">${esc(w)}</span>`;
    });
    if (got.length > exp.length)
      marks.push(`<span class="w-bad">（多出 ${got.length - exp.length} 詞）</span>`);
    const pct = exp.length ? Math.round((ok / exp.length) * 100) : 100;
    const allOk = ok === exp.length && got.length === exp.length;
    if (allOk) { okSent++; missPool.delete(idx); }
    else missPool.add(idx);
    $("#ps-feedback")
      .removeClass("bad").addClass(allOk ? "good" : "bad")
      .html(`逐詞比對（${ok}/${exp.length} 詞，${pct}%）：${marks.join(" ")}<br>正確：${esc(sents[idx][1])}`);
    $("#ps-score").text(`${okSent} 句全對 / ${askedSent} 句`);
  };

  $("#ps-check").on("click", check);
  $("#ps-in").on("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) check();
  });
  $("#ps-show").on("click", () =>
    $("#ps-feedback").removeClass("bad").addClass("good").text(`答案：${sents[idx][1]}`));
  $("#ps-next").on("click", next);
  next();
}
