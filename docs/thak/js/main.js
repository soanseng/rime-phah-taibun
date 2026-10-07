// 寫台文網頁工具入口（/convert/ 轉換、/vocab/ 詞彙、/grammar/ 文法）：
// 仝一支 JS，照頁面有的元素啟動對應功能；詞典只有轉換、詞彙頁需要才載。
// 資料路徑攏照模組位置算（頁面佇 /convert/ 等，資料佇 /thak/data-public/）。
// 預設載 data-public＝設定的公開包（來源已標示於頁脚；STTI 之開放運用/ARR
// 差異與 BY-SA 分發義務仍待最終授權複核，部署狀態以該複核為條件）。

import { buildReverseIndex } from "./dict.js?v=26";
import { loadDict } from "./dict.js?v=26";
import { initConverter } from "./ui/converter.js?v=26";
import { initVocab } from "./ui/vocab.js?v=26";
import { initGrammar } from "./ui/grammar.js?v=26";
import { initGrammarCheck } from "./ui/grammarcheck.js?v=26";

const DATA = new URL("../data-public/", import.meta.url);
const has = (id) => Boolean(document.getElementById(id));

// worker：fetch＋parse＋反查索引攏佇背景，閣分段傳——主線程逐段
// yield，無 half長 long task（fallback：直接載，較簡但會阻塞）
const loadViaWorker = () => new Promise((resolve, reject) => {
  const dict = {};
  const revEntries = [];
  const w = new Worker(new URL("./dict-worker.js?v=26", import.meta.url), { type: "module" });
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
  w.postMessage({ url: new URL("dict.json", DATA).href });
});

const ready = async () => {
  if (typeof jQuery === "undefined") {
    const el = document.querySelector("#load-state");
    if (el) el.textContent = "jQuery 載入失敗（CDN 無法連線？）";
    return;
  }
  if (has("gr-notes")) initGrammar();
  const convert = has("cv-in");
  const vocab = has("vb-in");
  if (!convert && !vocab) return;

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
    const hints = convert
      ? await fetch(new URL("hints.json", DATA))
        .then((r) => (r.ok ? r.json() : { lighttone: [], calque: [] }))
        .catch(() => ({ lighttone: [], calque: [] }))
      : null;
    const { dict, revEntries } = await loadViaWorker()
      .catch(() => loadDict(new URL("dict.json", DATA)).then((dict) => ({
        dict, revEntries: [...buildReverseIndex(dict).entries()],
      })));
    $("#load-state").remove();
    if (convert) {
      initConverter(dict, hints, initGrammarCheck(hints), new Map(revEntries), preDir);
      // 例句卡：點了直接轉換、看變調讀音＋POJ
      $(".demo-card").on("click", (ev) => {
        $("#cv-in").val($(ev.currentTarget).data("han") ?? "");
        $("#cv-run").trigger("click");
        document.getElementById("cv-tl").scrollIntoView({ behavior: "smooth", block: "center" });
      });
    }
    if (vocab) initVocab(dict);
  } catch (err) {
    $("#load-state").text(`詞典載入失敗：${err.message}`);
  }
};

$(ready);
