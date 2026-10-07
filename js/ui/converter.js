// 轉換分頁：漢→羅（點字換讀音）／羅→漢（實驗功能）。

import {
  segment, render, wordVariants, buildReverseIndex, tlToHan, decodeTlToHan, buildLM, sutianUrl,
} from "../dict.js?v=23";
import { formatRomanization, stripTones } from "../roman.js?v=23";

const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// 循環候選干焦換漢字詞——純羅馬字詞（guā＝若干）佇「羅→漢」的輸出底無意義
const HAN = /[\u3400-\u9FFF\uF000-\uFAFF]/;
const dictLink = (word, label = "教典") =>
  $("<a class='dict-link'></a>")
    .attr("href", sutianUrl(word))
    .attr("target", "_blank")
    .attr("rel", "noopener")
    .text(label);

export function initConverter(dict, hints, grammarCheck, revIn = null, preDirIn = null) {
  // 延伸詞層：hint 照字典實際內容顯示——無 src 詞就毋通講一个
  // 永遠出袂來的橘虛線標記（公開包這馬有延伸詞，會顯示）。
  const hasExt = Object.values(dict).some((e) => e.src);
  const hintH2R = () => "點漢字換讀音；⟨?⟩ 表示詞典揣無。"
  const rev = revIn ?? buildReverseIndex(dict);
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

  // 文法檢查／輕聲／對照表：全部交予 grammarcheck 模組（#cv-gram）
  const renderHints = (text) => grammarCheck?.(text);

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
    for (let gi = 0; gi < segs.length; ) {
      const seg = segs[gi];
      if (seg.t === "r") {
        $anno.append($("<span></span>").text(seg.s));
        gi++;
      } else if (seg.t === "miss") {
        // 聚合連續 miss（segment 逐字發）成一个詞組區塊
        let run = "";
        while (gi < segs.length && segs[gi].t === "miss") { run += segs[gi].s; gi++; }
        $anno.append(
          $("<span class='anno miss'></span>").attr("title", "詞典揣無").text(`⟨${run}⟩`),
        );
        // 註：連續 miss 聚合成一个⟨詞組⟩顯示（逐字拆解建議佮 segment
        // 用仝一個貪婪匹配，數學上拆袂出新的——結構建議改佇 hints 對照表）
      } else {
        const variants = wordVariants(seg, picks);
        const $w = $("<button type='button' class='anno word'></button>")
          .attr("title", variants.map((v) => `${v.tl}${v.active ? " ✓" : ""}`).join("　")
            + (seg.src === "rime" ? "　〔教典未收：讀音出自拍台文字典〕"
              : seg.src === "rime-moe" ? "　〔教典有收、本典建立層無：讀音出自拍台文字典〕" : ""))
          .text(seg.han);
        if (seg.src) $w.addClass("rime");
        $w.on("click", () => {
          const cur = picks.get(seg.si) ?? 0;
          picks.set(seg.si, (cur + 1) % seg.readings.length);
          paint();
        });
        $anno.append($w, dictLink(seg.han));
        gi++;
      }
    }
  };
  // r2h：結果狀態＋詞卡點選循環同音候選（手動改正同音歧義）
  const r2h = { pieces: [], overrides: new Map() };
  const r2hPieces = (r) => {
    // han 內底照詞序揣位置，拆做 [分隔段] × [詞段]——覆寫用
    const pieces = [];
    let cur = 0;
    for (const w of r.words ?? []) {
      const at = r.han.indexOf(w.word, cur);
      if (at < 0) continue;
      if (at > cur) pieces.push({ s: r.han.slice(cur, at) });
      pieces.push({ w: w.word, reading: w.reading });
      cur = at + w.word.length;
    }
    pieces.push({ s: r.han.slice(cur) });
    return pieces;
  };
  const paintR2H = () => {
    const input = String($("#cv-in").val() ?? "");
    const r = lm ? decodeTlToHan(input, rev, lm) : tlToHan(input, rev);
    if (!lm) ensureLM().then((m) => { if (m && dir === "r2h") paint(); });
    r2h.pieces = r2hPieces(r);
    r2h.overrides.clear();
    $("#cv-h1").text("漢字（實驗）");
    $("#cv-h2").text("詞對照");
    const hanText = () => r2h.pieces.map((p) => p.w ? (r2h.overrides.get(p) ?? p.w) : p.s).join("");
    const $out = $("#cv-tl").text(r.han || "—");
    const $list = $("#cv-poj").empty().removeClass("roman");
    if (r.words?.length) {
      for (const p of r2h.pieces) {
        if (!p.w) continue;
        const tl = formatRomanization(p.reading.replace(/0(?=[a-z])/g, ""));
        const alts = (rev.get(stripTones(p.reading)) ?? []).filter((a) => HAN.test(a.word));
        const $link = dictLink(p.w);
        const $chip = $("<button type='button' class='wchip'></button>")
          .attr("title", alts.length > 1
            ? `點換同音詞（${alts.length} 候選）：${alts.slice(0, 8).map((a) => a.word).join("・")}`
            : "同音詞")
          .append($("<b></b>").text(p.w))
          .append($("<span class='wchip-tl'></span>").text(tl));
        $chip.on("click", () => {
          if (alts.length < 2) return;
          const cur = r2h.overrides.get(p) ?? p.w;
          const i = (alts.findIndex((a) => a.word === cur) + 1) % alts.length;
          r2h.overrides.set(p, alts[i].word);
          $chip.find("b").text(alts[i].word);
          $link.attr("href", sutianUrl(alts[i].word));
          $out.text(hanText());
        });
        $list.append($chip, $link, " ");
      }
    } else {
      $list.text("—");
    }
    $("#cv-anno").hide().empty();
    $("#cv-gram").hide().prop("hidden", true).empty();
  };

  const paint = () => (dir === "h2r" ? paintH2R() : paintR2H());
  const run = () => {
    const text = String($("#cv-in").val() ?? "");
    if (dir === "h2r") {
      segs = segment(text, dict, rev); // rev：羅馬字黏漢字混寫合詞用
      picks.clear();
    }
    paint();
  };
  $("#cv-sandhi").on("change", paint);

  const applyDir = (d) => {
    dir = d;
    $("#panel-convert h2").text(d === "h2r" ? "漢羅 → TL／POJ" : "羅馬字 → 漢字");
    $("#cv-in").attr(
      "placeholder",
      d === "h2r"
        ? "貼漢羅文章，親像：我今仔日欲去台北。"
        : "貼台羅／POJ，親像：Goá kin-á-ji̍t beh khì Tâi-pak.",
    );
    $("#cv-hint").text(d === "h2r" ? hintH2R() : "實驗功能：同音詞真濟，可能選錯詞義。點詞卡換同音詞，點「教典」查辭典；輸出僅供輔助對照。");
  };
  $(".seg-btn[data-dir]").on("click", (ev) => {
    const $b = $(ev.currentTarget);
    if ($b.hasClass("is-active")) return;
    $(".seg-btn[data-dir]").removeClass("is-active");
    $b.addClass("is-active");
    applyDir($b.data("dir"));
    run();
  });
  $("#cv-run").on("click", run);
  $("#cv-hint").text(hintH2R()); // 初始載入就照 hasExt 顯示（preinit 方向佇後壁閣會覆寫）
  $("#cv-in").on("input", () => {
    if ($("#cv-live").prop("checked")) run();
  });
  // 詞典載入中就點方向鈕（main.js 的 .preinit handler 已記方向、
  // 鈕仔視覺嘛有動）：init 了照用，並且收掉 preinit handler 避免雙重綁。
  $(".seg-btn[data-dir]").off("click.preinit");
  if (preDirIn && preDirIn !== "h2r") applyDir(preDirIn);
  $(".copy").on("click", (ev) => {
    const $b = $(ev.currentTarget);
    navigator.clipboard?.writeText($(`#${$b.data("copy")}`).text() ?? "");
    const old = $b.text();
    $b.text("已複製");
    setTimeout(() => $b.text(old), 900);
  });

  // 詞典載入中使用者就拍好字／點過轉換（hit 陣 handler 攏未縛、事件落空）：
  // 初始化了若 input 已有字自動補跑一擺，毋免閣點一擺。
  if (String($("#cv-in").val() ?? "").trim()) run();
}
