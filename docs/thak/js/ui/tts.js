// 轉換頁「🔊 唸予我聽」：預設關；使用者開了、撳唸才下載模型（預設約 30 MB，存入瀏覽器快取）。
// 兩種唸法：「▶ 唸全篇」逐句串流；轉換輸出（TL／POJ）逐句右上角的細 ▶ 干焦唸彼句
// （文章長的時建議用這个，袂規篇一直佔電腦）。
import { speechSentences, splitPhrases } from "../tts-core.js?v=4";

const PREF_KEY = "phah-tts-enabled";
const MODEL_KEY = "phah-tts-model"; // "small"（預設 約 30 MB）｜"full"（約 58 MB）
const LONG_TEXT_SENTENCES = 12; // 超過就提醒一句一句唸
const MB = (n) => (n / 1e6).toFixed(0);

// conv：initConverter() 的回傳 { speechInput, setSentencePlayer }
export function initTTS(conv) {
  const $toggle = $("#tts-enable");
  const $panel = $("#tts-panel");
  const $all = $("#tts-speak");
  const $status = $("#tts-status");
  const $long = $("#tts-long");
  const $model = $("#tts-model");
  let tts = null; // { speak, engine }
  let playing = null; // { stop, stopped, $btn, done() }

  const ensureEngine = async () => {
    if (tts) return tts;
    const { loadEngine, speak } = await import("../tts.js?v=4");
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

  // 鈕仔狀態：唸全篇鈕換文字；逐句細鈕用 class（CSS 畫 ▶／■，毋改文字，複製袂濫著）
  const mark = ($btn, on) => {
    if ($btn.is($all)) $btn.text(on ? "■ 停" : "▶ 唸全篇");
    else $btn.toggleClass("is-playing", on).attr("aria-label", on ? "停" : "唸這句");
  };

  const stopPlaying = () => {
    if (!playing) return;
    const p = playing;
    playing = null;
    p.stopped = true;
    p.stop?.();
    mark(p.$btn, false);
  };

  // 提醒干焦講這擺欲唸的句（揣無讀音的字、鼻化 ⁿ）
  const noteFor = (sentences, unread) =>
    (unread.length ? `（詞典揣無讀音、略過：${[...new Set(unread)].join("")}）` : "")
    + (sentences.some((s) => s.includes("\u207F")) ? "（鼻化 ⁿ 模型無支援，唸做無鼻化）" : "");

  // 詞光：輸出區（TL／POJ；羅→漢是漢字）第 g 句的第 w 詞。逐擺重揣 DOM（轉換結果會重畫）。
  // 顯示的詞數佮唸的詞數無仝（親像詞典揣無的字）就光規句，毋亂對。
  const spokenWords = (sentence) => splitPhrases(sentence).flatMap((p) => p.split(" ")).filter((w) => /\p{L}/u.test(w));
  const highlight = (sentences, groupOf, s, w) => {
    $(".cv-sent.is-speaking, .cv-w.is-speaking").removeClass("is-speaking");
    if (s === null) return;
    for (const box of ["#cv-tl", "#cv-poj"]) {
      const $sent = $(box).children(".cv-sent").eq(groupOf[s]);
      if (!$sent.length) continue;
      const $words = $sent.children(".cv-w");
      if ($words.length === spokenWords(sentences[s]).length) $words.eq(w).addClass("is-speaking");
      else $sent.addClass("is-speaking");
    }
  };

  // 唸一組句；仝一个鈕閣撳就停，撳別个鈕先停這馬的。
  const play = async ({ sentences, unread, groupOf }, $btn) => {
    const note = noteFor(sentences, unread);
    const again = playing?.$btn?.is($btn);
    stopPlaying();
    if (again) return;
    if (!sentences.length) { $status.text("無通唸的台語文字。"); return; }
    const mine = { stop: null, stopped: false, $btn };
    playing = mine;
    mark($btn, true);
    try {
      const { engine, speak } = await ensureEngine();
      if (playing !== mine) return; // 載入中閣撳別个
      mine.stop = speak(engine, sentences, {
        onSentence: (i, n) => $status.text(n > 1 ? `唸第 ${i + 1}／${n} 句${note}` : `唸…${note}`),
        onWord: (s, w) => highlight(sentences, groupOf, s, w),
        onDone: (err) => {
          if (playing === mine) { playing = null; mark($btn, false); }
          $status.text(err ? `語音錯誤：${err.message}` : mine.stopped ? "停矣。" : `唸了矣${note}`);
        },
      });
    } catch (err) {
      if (playing === mine) { playing = null; mark($btn, false); }
      $status.text(`語音載入失敗：${err.message}`);
    }
  };

  const current = () => {
    const { segs, picks, lighttone } = conv.speechInput();
    return { picks, lighttone, ...speechSentences(segs, picks, lighttone) };
  };

  // 轉換結果一變（重轉、點字換讀音、變調開關）：停唸、更新提醒
  const refresh = () => {
    if ($panel.prop("hidden")) return;
    stopPlaying();
    const { sentences } = current();
    $long.prop("hidden", sentences.length <= LONG_TEXT_SENTENCES)
      .text(`文章較長（${sentences.length} 句）：建議撳轉換結果逐句右上角的 ▶ 一句一句唸；「唸全篇」會一路合成落去，較食電腦。`);
    $all.prop("disabled", !sentences.length);
  };

  $all.on("click", () => play(current(), $all));
  // 逐句：converter 共該句的 seg 組佮伊是第幾句交過來，照仝款規則轉做模型句
  const playGroup = (group, $btn, g) => {
    const { picks, lighttone } = conv.speechInput();
    const res = speechSentences(group, picks, lighttone);
    play({ ...res, groupOf: res.groupOf.map(() => g) }, $btn);
  };
  // 輸出區內容換（childList／文字）才重整；鈕仔狀態是 class，袂觸發
  new MutationObserver(refresh).observe(document.getElementById("cv-poj"), {
    childList: true, characterData: true, subtree: true,
  });

  // 換模型：停、放掉這馬的引擎；下擺唸才載新的（另一版的快取會清掉，省空間）
  try { $model.val(localStorage.getItem(MODEL_KEY) || "small"); } catch { /* 私密模式 */ }
  $model.on("change", () => {
    stopPlaying();
    tts = null;
    $status.text("換模型矣：下擺撳唸的時陣載入。");
    try { localStorage.setItem(MODEL_KEY, $model.val()); } catch { /* 私密模式 */ }
  });

  const apply = (on) => {
    $panel.prop("hidden", !on);
    if (!on) stopPlaying();
    conv.setSentencePlayer(on ? playGroup : null); // 漢→羅會重畫輸出
    if (on) refresh(); // 羅→漢無重畫，嘛愛更新提醒佮鈕仔
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
