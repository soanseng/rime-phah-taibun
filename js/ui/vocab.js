// 詞彙分頁：台語詞／華語釋義查詢＋教典例句（CC BY-ND 3.0 TW，標示來源）。

import { lookup, sutianUrl } from "../dict.js?v=13";
import { formatRomanization, tlToPoj, pojFixDiacritics } from "../roman.js?v=13";

const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
export async function initVocab(dict) {
  const $tb = $("#vb-tbl tbody");
  let examples = {};
  try {
    examples = await (await fetch("../data-public/examples.json")).json();
  } catch { /* 例句載入失敗：欄位留空 */ }
  const exHtml = (han) =>
    (examples[han] ?? [])
      .map(([h, t]) => `<div class="ex">${esc(h)}<br><span class="roman">${esc(t)}</span></div>`)
      .join("");
  const run = () => {
    const rows = lookup(dict, String($("#vb-in").val() ?? ""));
    $("#vb-count").text(rows.length ? `${rows.length} 筆` : "（這馬無半筆）");
    $tb.empty();
    for (const r of rows.slice(0, 50)) {
      const tl = formatRomanization(r.r[0]);
      const poj = pojFixDiacritics(formatRomanization(tlToPoj(r.r[0])));
      $tb.append(
        $("<tr></tr>")
          .append($("<td class='w'></td>").text(r.han))
          .append($("<td class='roman'></td>").text(tl))
          .append($("<td class='roman'></td>").text(poj))
          .append($("<td class='ex-cell'></td>").html(exHtml(r.han)))
          .append(
            $("<td></td>").append(
              $("<a class='dict-link'></a>")
                .attr("href", sutianUrl(r.han))
                .attr("target", "_blank")
                .attr("rel", "noopener")
                .text("教典"),
            ),
          ),
      );
    }
  };

  $("#vb-in").on("input", run);
}
