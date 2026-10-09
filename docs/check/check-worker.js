// 寫作檢查 worker：詞典（~8 MB JSON）parse、反查索引、音節／多音節集合攏佇
// 背景建，檢查（runChecks＋segment）嘛佇遮跑——主線程袂予詞典卡牢
// （Lighthouse TBT 原本 10 秒）。
// 協定：main→{type:"init", urls:{dict, iongji, hints, yongji, hyphen}} → worker→{type:"ready"}｜{type:"error", message}；
// main→{type:"check", id, text, target, mode} → worker→{type:"result", id, issues}。
import { runChecks, buildSyllableSet, buildMultiReadings, buildAltMap, buildLkkMap, buildCharMap, buildWordReadings, buildGlossIndex } from "./check-core.js?v=5";
import { segment, buildReverseIndex } from "../thak/js/dict.js?v=26";

let data = null;

const json = async (url) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
};

self.onmessage = async ({ data: msg }) => {
  if (msg.type === "init") {
    try {
      const [dict, iongji, hints, yongji, hyphen] = await Promise.all(
        [msg.urls.dict, msg.urls.iongji, msg.urls.hints, msg.urls.yongji, msg.urls.hyphen].map(json),
      );
      data = {
        dict,
        rev: buildReverseIndex(dict),
        syllableSet: buildSyllableSet(dict),
        multiReadings: buildMultiReadings(dict, new Set(hyphen.words)),
        altMap: buildAltMap(iongji.items),
        lkkMap: buildLkkMap(yongji.items),
        charMap: buildCharMap(yongji.items),
        wordReadings: buildWordReadings(yongji.items),
        recWords: new Set(yongji.items.map((it) => it.word)),
        glossIndex: buildGlossIndex(dict),
        hints,
      };
      self.postMessage({ type: "ready" });
    } catch (err) {
      self.postMessage({ type: "error", message: String(err?.message ?? err) });
    }
  } else if (msg.type === "check" && data) {
    const { text } = msg;
    const issues = runChecks(text, {
      target: msg.target,
      mode: msg.mode,
      syllableSet: data.syllableSet,
      multiReadings: data.multiReadings,
      segments: text ? segment(text, data.dict, data.rev) : null,
      altMap: data.altMap,
      dict: data.dict,
      lkkMap: data.lkkMap,
      charMap: data.charMap,
      wordReadings: data.wordReadings,
      recWords: data.recWords,
      glossIndex: data.glossIndex,
      hints: data.hints,
    });
    self.postMessage({ type: "result", id: msg.id, issues });
  }
};
