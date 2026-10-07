// 詞典 worker：fetch＋JSON.parse＋反查索引建攏佇 worker thread，閣用
// 「分段＋ack」流控傳轉主線程——喘擺 6.8MB structured clone 佇主線程
// 會變一个 ~3s long task（Lighthouse TBT）；worker 每段等主線程 ack
// （requestAnimationFrame）才閣傳，主線程逐段攏細段、會當喘氣。
// 協定：main→{url}；worker→{type:"chunk", kind, entries}↔main→{type:"ack"}；
// 收煞→{type:"done", nDict, nRev}。
import { buildReverseIndex } from "./dict.js?v=22";

const CHUNK = 6000;
const waitAck = () => new Promise((r) => { self.onmessage = r; });

self.onmessage = async (ev) => {
  try {
    const res = await fetch(ev.data.url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const dict = await res.json();
    const dictEntries = Object.entries(dict);
    for (let i = 0; i < dictEntries.length; i += CHUNK) {
      self.postMessage({ type: "chunk", kind: "dict", entries: dictEntries.slice(i, i + CHUNK) });
      await waitAck();
    }
    const rev = [...buildReverseIndex(dict).entries()];
    for (let i = 0; i < rev.length; i += CHUNK) {
      self.postMessage({ type: "chunk", kind: "rev", entries: rev.slice(i, i + CHUNK) });
      await waitAck();
    }
    self.postMessage({ type: "done", nDict: dictEntries.length, nRev: rev.length });
    self.onmessage = null;
  } catch (err) {
    self.postMessage({ type: "error", message: String(err?.message ?? err) });
  }
};
