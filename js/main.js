// 入口：載詞典、接分頁、啟動三個分頁模組。
// 預設載 data-public＝設定的公開包（來源已標示於頁脚；STTI 之開放運用/ARR
// 差異與 BY-SA 分發義務仍待最終授權複核，部署狀態以該複核為條件）。
// 本機測其他組合請改 fetch("./data/dict.json")。

import { loadDict } from "./dict.js?v=15";
import { initConverter } from "./ui/converter.js?v=15";
import { initPractice, initSentencePractice } from "./ui/practice.js?v=15";
import { initVocab } from "./ui/vocab.js?v=15";
import { initGrammar } from "./ui/grammar.js?v=15";

const ready = async () => {
  if (typeof jQuery === "undefined") {
    const el = document.querySelector("#load-state");
    if (el) el.textContent = "jQuery 載入失敗（CDN 無法連線？）";
    return;
  }
  initGrammar(); // 獨立載入：文法索引失敗嘛袂拖累其他分頁
  try {
    const [dict, hints] = await Promise.all([
      loadDict("./data-public/dict.json"),
      fetch("./data-public/hints.json")
        .then((r) => (r.ok ? r.json() : { lighttone: [], calque: [] }))
        .catch(() => ({ lighttone: [], calque: [] })),
    ]);
    $("#load-state").remove();
    initConverter(dict, hints);
    initPractice(dict);
    initSentencePractice();
    initVocab(dict);
    $(".seg-btn[data-pmode]").on("click", (ev) => {
      const $b = $(ev.currentTarget);
      $(".seg-btn[data-pmode]").removeClass("is-active");
      $b.addClass("is-active");
      const sent = $b.data("pmode") === "sent";
      $("#pr-word-card").prop("hidden", sent);
      $("#pr-sent-card").prop("hidden", !sent);
    });
  } catch (err) {
    $("#load-state").text(`詞典載入失敗：${err.message}`);
    return;
  }

  $(".tab").on("click", (ev) => {
    const $b = $(ev.currentTarget);
    $(".tab").removeClass("is-active").attr("aria-selected", "false");
    $b.addClass("is-active").attr("aria-selected", "true");
    $(".panel").removeClass("is-active").prop("hidden", true);
    $(`#panel-${$b.data("tab")}`).addClass("is-active").prop("hidden", false);
  });
};

$(ready);
