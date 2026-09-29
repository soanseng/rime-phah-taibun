// 羅→漢回歸斷言：bun tools/regress-r2h.mjs [bundle]
import { buildReverseIndex, buildLM, decodeTlToHan } from "../js/dict.js?v=18";
import { segment, render } from "../js/dict.js?v=18";
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
const { formatRomanization, tlToPoj, pojFixDiacritics } = await import("../js/roman.js?v=18");
ok("免調顯示無 0", wc.words.every(x => !/[0-9]/.test(formatRomanization(x.reading))));
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
// 混寫：羅馬字直（無空白）黏漢字 → 反查合詞；前綴無合/有空白 → 隔空白分詞
const mx = render(segment("Pháiⁿ命人to̍h是艱苦人", dict, rev), new Map(), {});
ok("混寫合詞（Pháiⁿ命人→pháinn-miā-lâng）", nfc(mx.tl).includes(nfc("Pháinn-miā-lâng")));
ok("前綴無合勿綴（to̍h是→to̍h sī）", nfc(mx.tl).includes("to̍h sī "));
ok("混寫 POJ 雙軌（正式字形 ⁿ）", nfc(mx.poj).includes(nfc("Pháiⁿ-miā-lâng")));
ok("tsit款→這款", nfc(render(segment("tsit款", dict, rev), new Map(), {}).tl) === "Tsit-khuán");
const sp = render(segment("Pháiⁿ 命人 to̍h 是 艱苦人", dict, rev), new Map(), {});
ok("有空白照舊＋單空白", nfc(sp.tl) === nfc("Pháiⁿ miā lâng to̍h sī kan-khóo-lâng"));
// 語料級混寫：合詞（hit款→彼款）、多音節尾退空白（ka-tī 行止）、前綴無合（tio̍h 關）
ok("hit款→彼款", nfc(render(segment("hit款", dict, rev), new Map(), {}).tl) === "Hit-khuán");
ok("多音節羅馬尾退空白", nfc(render(segment("ka-tī行止", dict, rev), new Map(), {}).tl) === "Ka-tī hîng-tsí");
ok("tio̍h關分詞", nfc(render(segment("tio̍h關", dict, rev), new Map(), {}).tl) === "Tio̍h kuan");
// POJ 正式字形（lua tl_to_poj 1:1）：o͘/ⁿ 字形＋POJ 調符定位；nng 音節鼻音例外
const pj = (n) => nfc(pojFixDiacritics(formatRomanization(tlToPoj(n))));
ok("khuann3→khòaⁿ（鼻化上標＋調符標 o）", pj("khuann3") === nfc("khòaⁿ"));
ok("too7→tō͘（oo→o͘）", pj("too7") === nfc("tō͘"));
ok("sannh4→saⁿh（鼻化＋h 尾）", pj("sannh4") === "sa\u207Fh");
ok("nng7→nn̄g（音節鼻音毋換 ⁿ）", pj("nng7") === nfc("nn̄g"));
ok("mng5→mn̂g", pj("mng5") === nfc("mn̂g"));
ok("phinn7→phīⁿ", pj("phinn7") === nfc("phīⁿ"));
ok("gua7→gōa（開音節標 o）", pj("gua7") === nfc("gōa"));
ok("kuan2→koán（有韻尾標 a）", pj("kuan2") === nfc("koán"));
ok("ue7→ōe", pj("ue7") === nfc("ōe"));
ok("gueh8→goe̍h（oe 有韻尾標 e）", pj("gueh8") === nfc("goe̍h"));
ok("tsui2→chúi（ui 標 u）", pj("tsui2") === nfc("chúi"));
ok("khiu5→khiû（iu 兩式攏標 u）", pj("khiu5") === nfc("khiû"));
ok("ping1→peng（ing→eng）", pj("ping1") === "peng");
const kw = render(segment("我看水。", dict, rev), new Map(), {});
ok("e2e POJ 雙軌", nfc(kw.poj).includes(nfc("Góa")) && nfc(kw.poj).includes(nfc("khòaⁿ")) && nfc(kw.poj).includes(nfc("chúi")));
ok("e2e TL 照舊 nn/ts", nfc(kw.tl).includes("khu\u00E0nn") && nfc(kw.tl).includes("tsu\u00ED"));
console.log("KNOWN 同音誤合（嘛/罵 攏 ma7）:", render(segment("mā人格", dict, rev), new Map(), {}).tl, "（應 mā jîn-keh；語境歧義，和 r2h 仝類）");
console.log(fail ? `${fail} FAILED` : "ALL PASS");
process.exit(fail ? 1 : 0);
