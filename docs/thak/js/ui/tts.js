// 轉換頁「🔊 唸予我聽」：預設關；使用者開了、撳「唸出來」才下載模型（約 58 MB，存入瀏覽器快取）。
import { speechSentences } from "../tts-core.js?v=1";

const PREF_KEY = "phah-tts-enabled";
const MB = (n) => (n / 1e6).toFixed(0);

// getInput() → { segs, picks, lighttone }：轉換頁目前的分詞佮使用者點過的讀音
export function initTTS(getInput) {
  const $toggle = $("#tts-enable");
  const $panel = $("#tts-panel");
  const $btn = $("#tts-speak");
  const $status = $("#tts-status");
  let tts = null; // { speak, engine }
  let stop = null;

  const setIdle = () => { stop = null; $btn.text("▶ 唸出來").prop("disabled", false); };

  const ensureEngine = async () => {
    if (tts) return tts;
    $btn.prop("disabled", true);
    const { loadEngine, speak } = await import("../tts.js?v=1");
    const engine = await loadEngine(({ phase, loaded, total, cached }) => {
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

  $btn.on("click", async () => {
    if (stop) { stop(); return; }
    const { segs, picks, lighttone } = getInput();
    const { sentences, unread } = speechSentences(segs, picks, lighttone);
    if (!sentences.length) { $status.text("無通唸的台語文字。"); return; }
    try {
      const { engine, speak } = await ensureEngine();
      const nasal = sentences.some((s) => s.includes("\u207F")) ? "（鼻化 ⁿ 模型無支援，唸做無鼻化）" : "";
      const note = (unread.length ? `（詞典揣無讀音、略過：${[...new Set(unread)].join("")}）` : "") + nasal;
      $btn.text("■ 停").prop("disabled", false);
      stop = speak(engine, sentences, {
        onSentence: (i, n) => $status.text(`唸第 ${i + 1}／${n} 句${note}`),
        onDone: (err) => { setIdle(); $status.text(err ? `語音錯誤：${err.message}` : `唸了矣${note}`); },
      });
    } catch (err) {
      setIdle();
      $status.text(`語音載入失敗：${err.message}`);
    }
  });

  const apply = (on) => {
    $panel.prop("hidden", !on);
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
