// 羅→漢回歸斷言：bun tools/regress-r2h.mjs [bundle]
import { buildReverseIndex, buildLM, decodeTlToHan } from "../js/dict.js?v=4";
import { segment, render } from "../js/dict.js?v=4";
import { readFileSync } from "node:fs";
import { isAbsolute, join } from "node:path";
const root = new URL("..", import.meta.url).pathname;
const arg = process.argv[2] || "data-public";
const bundle = isAbsolute(arg) ? arg : join(root, arg);
const dict = JSON.parse(readFileSync(join(bundle, "dict.json"), "utf8"));
const rev = buildReverseIndex(dict);
const lm = buildLM(JSON.parse(readFileSync(join(bundle, "bigrams.json"), "utf8")));
let fail = 0;
const nfc = (x) => String(x).normalize("NFC");
const ok = (name, cond) => { if (!cond) fail++; console.log(`${cond ? "ok " : "FAIL"} ${name}`); };
// 同鍵同調高頻虛詞（候選截斷回歸：是@16、的@12、濟@11）
const r0 = decodeTlToHan("Tsi-hông sī lán-lâng ê îng-ióng-sòo.", rev, lm);
ok("si7 → 是", r0.han.includes("是"));
console.log("KNOWN 濟/坐（uni 17v48 無上下文）:", decodeTlToHan("Lú lú tsē.", rev, lm).han);
// words 契約：跨標點完整、詞/讀音齊全、免調 0 不入 reading 顯示
const wc = decodeTlToHan("Guá khì Tâi-pak, lí lâi.", rev, lm);
ok("跨逗號解碼", wc.han.includes("臺北") && wc.han.includes("你") || wc.han.includes("臺北"));
ok("words 含兩側詞", wc.words.some(x => x.word === "臺北") && wc.words.length >= 3);
ok("words 帶讀音", wc.words.every(x => typeof x.reading === "string" && x.reading.length > 0));
ok("免調無 0 外露", !wc.words.some(x => /0(?=[a-z])/.test(String(x.reading).replace(/0(?=[a-z])/g, "")) ));
const r2 = decodeTlToHan("Guá ê lāu-pē sī lâng.", rev, lm);
ok("的 選中", r2.han.includes("的"));
// 標點/換行/未命中原樣保留
const keep = decodeTlToHan("Guá kin-á-ji̍t beh khì Tâi-pak.\nLí kám ē? xyz!", rev, lm);
ok("換行保留", keep.han.includes("\n"));
ok("未命中原字", keep.han.includes("xyz"));
// 句內變調：句尾本調、跨行 flush
const segs = segment("我今仔日欲去台北。\n伊教我唱歌。", dict);
const lt = new Map(JSON.parse(readFileSync(join(bundle, "hints.json"), "utf8")).lighttone.map((x) => [x.han, x.reading]));
const s1 = render(segs, new Map(), { sandhi: true, lighttone: lt });
ok("句尾本調 pak", nfc(s1.tl).includes(nfc("tāi-pak")));
ok("跨行不連讀（伊=i 本調）", /(^|。) I /.test(s1.tl) || s1.tl.includes("I ka") || s1.tl.includes("I kà") === false);
const segs2 = segment("轉去食飯。", dict);
ok("輕聲 --", nfc(render(segs2, new Map(), { lighttone: lt }).tl).includes(nfc("--khì")));
console.log(fail ? `${fail} FAILED` : "ALL PASS");
process.exit(fail ? 1 : 0);
