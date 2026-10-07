// 入口：載詞典、接分頁、啟動三個分頁模組。
// 預設載 data-public＝設定的公開包（來源已標示於頁脚；STTI 之開放運用/ARR
// 差異與 BY-SA 分發義務仍待最終授權複核，部署狀態以該複核為條件）。
// 本機測其他組合請改 fetch("./data/dict.json")。

import { buildReverseIndex } from "./dict.js?v=24";
import { loadDict } from "./dict.js?v=24";
import { initConverter } from "./ui/converter.js?v=24";
import { initPractice, initSentencePractice } from "./ui/practice.js?v=24";
import { initVocab } from "./ui/vocab.js?v=24";
import { initGrammar } from "./ui/grammar.js?v=24";
import { initGrammarCheck } from "./ui/grammarcheck.js?v=24";

const ready = async () => {
  if (typeof jQuery === "undefined") {
    const el = document.querySelector("#load-state");
    if (el) el.textContent = "jQuery 載入失敗（CDN 無法連線？）";
    return;
  }
  initGrammar(); // 獨立載入：文法索引失敗嘛袂拖累其他分頁
  // 詞典載入中（5–10 秒）方向鈕就先會動：記方向＋鈕仔視覺切換，
  // initConverter 了照用（off click.preinit 收掉，避免雙重綁）。
  let preDir = null;
  $(".seg-btn[data-dir]").on("click.preinit", (ev) => {
    const $b = $(ev.currentTarget);
    preDir = $b.data("dir");
    $(".seg-btn[data-dir]").removeClass("is-active");
    $b.addClass("is-active");
  });
  try {
    // worker：fetch＋parse＋反查索引攏佇背景，閣分段傳——主線程逐段
    // yield，無 half長 long task（fallback：直接載，較簡但會阻塞）
    const hints = await fetch("./data-public/hints.json")
      .then((r) => (r.ok ? r.json() : { lighttone: [], calque: [] }))
      .catch(() => ({ lighttone: [], calque: [] }));
    const loadViaWorker = () => new Promise((resolve, reject) => {
      const dict = {};
      const revEntries = [];
      const w = new Worker("./js/dict-worker.js?v=24", { type: "module" });
      const raf = () => new Promise(requestAnimationFrame);
      let ready = Promise.resolve();
      w.onmessage = (ev) => {
        const d = ev.data;
        if (d.type === "chunk") {
          if (d.kind === "dict") Object.assign(dict, ...d.entries.map(([k, v]) => ({ [k]: v })));
          else revEntries.push(...d.entries);
          ready = ready.then(raf).then(() => w.postMessage({ type: "ack" }));
        } else if (d.type === "done") {
          w.terminate();
          ready.then(() => resolve({ dict, revEntries }));
        } else {
          w.terminate();
          reject(new Error(d.message));
        }
      };
      w.onerror = () => { w.terminate(); reject(new Error("worker 失敗")); };
      w.postMessage({ url: "./data-public/dict.json" });
    });
    const { dict, revEntries } = await loadViaWorker()
      .catch(() => loadDict("./data-public/dict.json").then((dict) => ({
        dict, revEntries: [...buildReverseIndex(dict).entries()],
      })));
    const rev = new Map(revEntries);
    $("#load-state").remove();
    initConverter(dict, hints, initGrammarCheck(hints), rev, preDir);
    initPractice(dict);
    // 句庫 973KB——練習分頁頭一擺開才載（landing/轉換無愛等伊）
    let sentReady = false;
    const sentInit = () => { if (!sentReady) { sentReady = true; initSentencePractice(); } };
    $("#tab-practice").on("click", sentInit);
    $(".seg-btn[data-pmode='sent']").on("click", sentInit);
    initVocab(dict);
    // Landing 例句卡：點了→轉換分頁看變調讀音＋POJ
    $(".demo-card").on("click", (ev) => {
      $("#tab-convert").trigger("click");
      $("#cv-in").val($(ev.currentTarget).data("han") ?? "");
      $("#cv-run").trigger("click");
      $("#panel-convert")[0].scrollIntoView({ behavior: "smooth", block: "start" });
    });
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
