// 轉換頁「🔊 唸予我聽」：預設關；使用者開了、撳唸才下載模型（約 58 MB，存入瀏覽器快取）。
// 兩種唸法：「▶ 唸全篇」逐句串流；句清單逐句 ▶（文章長的時建議用這个，袂規篇一直佔電腦）。
import { speechSentences } from "../tts-core.js?v=1";

const PREF_KEY = "phah-tts-enabled";
const MODEL_KEY = "phah-tts-model"; // "small"（預設 約 30 MB）｜"full"（約 58 MB）
const LONG_TEXT_SENTENCES = 12; // 超過就提醒一句一句唸
const MB = (n) => (n / 1e6).toFixed(0);

// getInput() → { segs, picks, lighttone }：轉換頁目前的分詞佮使用者點過的讀音
export function initTTS(getInput) {
  const $toggle = $("#tts-enable");
  const $panel = $("#tts-panel");
  const $all = $("#tts-speak");
  const $status = $("#tts-status");
  const $list = $("#tts-sentences");
  const $long = $("#tts-long");
  const $model = $("#tts-model");
  let tts = null; // { speak, engine }
  let playing = null; // { stop, $btn, label }
  let current = { sentences: [], note: "" };

  const ensureEngine = async () => {
    if (tts) return tts;
    const { loadEngine, speak } = await import("../tts.js?v=2");
    const engine = await loadEngine($model.val(), ({ phase, loaded, total, cached }) => {
      if (phase === "model") {
        $status.text(cached
          ? "對瀏覽器快取載入模型…"
          : `下載語音模型 ${MB(loaded)}／${MB(total)} MB（頭一擺；了後存佇瀏覽器快取）`);
      } else if (phase === "runtime") {
        $status.text("準備語音引擎…");
      }
    });
    tts = { engine, speak };
    return tts;
  };

  const stopPlaying = () => {
    if (!playing) return;
    const p = playing;
    playing = null;
    p.stopped = true;
    p.stop?.();
    p.$btn.text(p.label);
  };

  // 唸一組句；$btn 唸中變「■」，閣撳就停。別个鈕撳落去先停這馬的。
  const play = async (sentences, $btn, label) => {
    const again = playing?.$btn?.is($btn);
    stopPlaying();
    if (again) return;
    if (!sentences.length) { $status.text("無通唸的台語文字。"); return; }
    playing = { stop: null, $btn, label };
    const mine = playing;
    $btn.text("■");
    if ($btn.is($all)) $btn.text("■ 停");
    try {
      const { engine, speak } = await ensureEngine();
      if (playing !== mine) return; // 載入中閣撳別个
      const { note } = current;
      mine.stop = speak(engine, sentences, {
        onSentence: (i, n) => $status.text(n > 1 ? `唸第 ${i + 1}／${n} 句${note}` : `唸…${note}`),
        onDone: (err) => {
          if (playing === mine) { playing = null; $btn.text(label); }
          $status.text(err ? `語音錯誤：${err.message}` : mine.stopped ? "停矣。" : `唸了矣${note}`);
        },
      });
    } catch (err) {
      if (playing === mine) { playing = null; $btn.text(label); }
      $status.text(`語音載入失敗：${err.message}`);
    }
  };

  // 轉換結果一變就重做句清單（讀音照使用者點過的）
  const rebuild = () => {
    if ($panel.prop("hidden")) return;
    stopPlaying();
    const { segs, picks, lighttone } = getInput();
    const { sentences, unread } = speechSentences(segs, picks, lighttone);
    const nasal = sentences.some((s) => s.includes("\u207F")) ? "（鼻化 ⁿ 模型無支援，唸做無鼻化）" : "";
    current = {
      sentences,
      note: (unread.length ? `（詞典揣無讀音、略過：${[...new Set(unread)].join("")}）` : "") + nasal,
    };
    $long.prop("hidden", sentences.length <= LONG_TEXT_SENTENCES)
      .text(`文章較長（${sentences.length} 句）：建議一句一句唸；「唸全篇」會一路合成落去，較食電腦。`);
    $all.prop("disabled", !sentences.length);
    $list.empty();
    sentences.forEach((s, i) => {
      const $b = $("<button type='button' class='btn-ghost tts-one'></button>")
        .text("▶").attr("aria-label", `唸第 ${i + 1} 句`)
        .on("click", () => play([s], $b, "▶"));
      $list.append($("<li></li>").append($b, $("<span class='roman'></span>").text(s)));
    });
  };

  $all.on("click", () => play(current.sentences, $all, "▶ 唸全篇"));
  // 換模型：停、放掉這馬的引擎；下擺唸才載新的（另一版的快取會清掉，省空間）
  try { $model.val(localStorage.getItem(MODEL_KEY) || "small"); } catch { /* 私密模式 */ }
  $model.on("change", () => {
    stopPlaying();
    tts = null;
    $status.text("換模型矣：下擺撳唸的時陣載入。");
    try { localStorage.setItem(MODEL_KEY, $model.val()); } catch { /* 私密模式 */ }
  });
  new MutationObserver(rebuild).observe(document.getElementById("cv-poj"), {
    childList: true, characterData: true, subtree: true,
  });

  const apply = (on) => {
    $panel.prop("hidden", !on);
    if (on) rebuild(); else stopPlaying();
    try { localStorage.setItem(PREF_KEY, on ? "1" : "0"); } catch { /* 私密模式 */ }
  };
  $toggle.on("change", () => apply($toggle.prop("checked")));
  let saved = false;
  try { saved = localStorage.getItem(PREF_KEY) === "1"; } catch { /* 私密模式 */ }
  // 詞典載入中（handler 未縛）使用者就勾矣：照伊這馬勾的，毋通共伊蓋做記錄的「關」
  const on = saved || $toggle.prop("checked");
  $toggle.prop("checked", on);
  apply(on);
}
