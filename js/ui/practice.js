// 練習分頁：看漢字拍台羅；免調可比對，調號另計。

import { practicePool, normalizeAnswer, readingToneless, sutianUrl } from "../dict.js?v=6";
import { formatRomanization, tlToPoj, pojFixDiacritics } from "../roman.js?v=6";

const stripDigits = (s) => s.replace(/[1-9]/g, "");
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
