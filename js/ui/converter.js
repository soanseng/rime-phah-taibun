// 轉換分頁：漢→羅（點字換讀音）／羅→漢（實驗功能）。

import {
  segment, render, wordVariants, buildReverseIndex, tlToHan, decodeTlToHan, buildLM, sutianUrl,
} from "../dict.js?v=9";
import { formatRomanization, pojToTl } from "../roman.js?v=9";

const dictLink = (word, label = "教典") =>
  $("<a class='dict-link'></a>")
    .attr("href", sutianUrl(word))
    .attr("target", "_blank")
    .attr("rel", "noopener")
    .text(label);

export function initConverter(dict, hints) {
  const rev = buildReverseIndex(dict);
  let lm = null;        // bigram LM（羅→漢用）
  let lmPromise = null; // single-flight：避免重複 fetch
  const ensureLM = () => {
    if (lm) return Promise.resolve(lm);
    if (!lmPromise) {
      lmPromise = fetch("./data-public/bigrams.json")
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
        .then((j) => { lm = buildLM(j); return lm; })
        .catch(() => { lm = false; return false; });
    }
    return lmPromise;
  };
  const picks = new Map();
  let segs = [];
  const lighttoneMap = new Map((hints?.lighttone ?? []).map((lt) => [lt.han, lt.reading]));
  let dir = "h2r";

  const renderHints = (text) => {
    const found = [];
    for (const lt of hints.lighttone) {
      if (text.includes(lt.han)) found.push(`輕聲：<code>${lt.marked}</code>（${lt.reading}）`);
      if (found.length >= 8) break;
    }
    const $h = $("#cv-hints");
    $h.prop("hidden", false).show().empty();
    if (found.length) {
      $h.append("<div class='hint-title'>輕聲建議（依用字偵測）</div><ul></ul>");
      const $ul = $h.find("ul").last();
      for (const f of found) $ul.append($("<li></li>").html(f));
    }
    const rows = hints.calque
      .map((c) => `<li>「${c.han}」→ <code>${c.suggest}</code></li>`)
      .join("");
    $h.append(
      "<details class='calque'><summary>華語直譯通用小提醒（點開看）</summary>" +
      `<ul>${rows}</ul></details>`,
    );
  };

  const paintH2R = () => {
    const { tl, poj } = render(segs, picks, {
      sandhi: $("#cv-sandhi").prop("checked"),
      lighttone: lighttoneMap,
    });
    $("#cv-h1").text("台羅 TL");
    $("#cv-h2").text("白話字 POJ");
    $("#cv-tl").text(tl || "—");
    $("#cv-poj").text(poj || "—");
    const $anno = $("#cv-anno").show().empty();
    for (const seg of segs) {
      if (seg.t === "r") {
        $anno.append($("<span></span>").text(seg.s));
      } else if (seg.t === "miss") {
        $anno.append(
          $("<span class='anno miss'></span>").attr("title", "詞典揣無").text(`⟨${seg.s}⟩`),
        );
      } else {
        const variants = wordVariants(seg, picks);
        const $w = $("<button type='button' class='anno word'></button>")
          .attr("title", variants.map((v) => `${v.tl}${v.active ? " ✓" : ""}`).join("　"))
          .text(seg.han);
        $w.on("click", () => {
          const cur = picks.get(seg.si) ?? 0;
          picks.set(seg.si, (cur + 1) % seg.readings.length);
          paint();
        });
        $anno.append($w, dictLink(seg.han));
      }
    }
    renderHints(String($("#cv-in").val() ?? ""));
  };
  const paintR2H = () => {
    const input = String($("#cv-in").val() ?? "");
    // bigram lattice 解碼（LM lazy-load；載入前 fallback greedy）
    const r = lm ? decodeTlToHan(input, rev, lm) : tlToHan(input, rev);
    if (!lm) ensureLM().then((m) => { if (m && dir === "r2h") paint(); });
    $("#cv-h1").text("漢字（實驗）");
    $("#cv-h2").text("詞對照");
    $("#cv-tl").text(r.han || "—");
    const $list = $("#cv-poj").empty().removeClass("roman");
    if (r.words?.length) {
      for (const w of r.words.slice(0, 80)) {
        const tl = formatRomanization(w.reading.replace(/0(?=[a-z])/g, ""));
        $list.append(
          $("<span class='wchip'></span>")
            .append($("<b></b>").text(w.word))
            .append($("<span class='wchip-tl'></span>").text(tl))
            .append(dictLink(w.word)),
        );
      }
    } else {
      $list.text("—");
    }
    $("#cv-anno").hide().empty();
    $("#cv-hints").hide().prop("hidden", true).empty();
  };

  const paint = () => (dir === "h2r" ? paintH2R() : paintR2H());
  const run = () => {
    const text = String($("#cv-in").val() ?? "");
    if (dir === "h2r") {
      segs = segment(text, dict);
      picks.clear();
    }
    paint();
  };
  $("#cv-sandhi").on("change", paint);

  $(".seg-btn[data-dir]").on("click", (ev) => {
    const $b = $(ev.currentTarget);
    if ($b.hasClass("is-active")) return;
    $(".seg-btn[data-dir]").removeClass("is-active");
    dir = $b.data("dir");
    $("#panel-convert h2").text(dir === "h2r" ? "漢羅 → TL／POJ" : "羅馬字 → 漢字");
    $("#cv-in").attr(
      "placeholder",
      dir === "h2r"
        ? "貼漢羅文章，親像：我今仔日欲去台北。"
        : "貼台羅／POJ，親像：Goá kin-á-ji̍t beh khì Tâi-pak.",
    );
    $("#cv-hint").text(
      dir === "h2r" ? "點漢字換讀音；⟨?⟩ 表示詞典揣無。" : "實驗功能：同音詞真濟，可能選錯詞義，輸出僅供輔助對照，毋是可靠翻譯。",
    );
    run();
  });

  $("#cv-run").on("click", run);
  $("#cv-in").on("input", () => {
    if ($("#cv-live").prop("checked")) run();
  });
  $(".copy").on("click", (ev) => {
    const $b = $(ev.currentTarget);
    navigator.clipboard?.writeText($(`#${$b.data("copy")}`).text() ?? "");
    const old = $b.text();
    $b.text("已複製");
    setTimeout(() => $b.text(old), 900);
  });
}
