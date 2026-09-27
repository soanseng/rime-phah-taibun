// 詞彙分頁：台語詞／華語釋義查詢。

import { lookup, sutianUrl } from "../dict.js?v=3";
import { formatRomanization, tlToPoj, pojFixDiacritics } from "../roman.js?v=3";

export function initVocab(dict) {
  const $tb = $("#vb-tbl tbody");

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
          .append($("<td></td>").text(r.h || ""))
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
