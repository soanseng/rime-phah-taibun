// 羅→漢回歸斷言：bun tools/regress-r2h.mjs [bundle]
import { buildReverseIndex, buildLM, decodeTlToHan } from "../js/dict.js?v=21";
import { segment, render } from "../js/dict.js?v=21";
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
const { formatRomanization, tlToPoj, pojFixDiacritics } = await import("../js/roman.js?v=21");
// 上游 rime-phah-taibun v0.9.4 parity：Python tl_to_poj 內嵌 poj_fix_diacritics
// （音節尾 oa/oe 標 o、ui 標 u；大小寫攏支援；空白嘛是音節邊界）
ok("tlToPoj oa 修正", nfc(tlToPoj("gua\u0304")) === nfc("go\u0304a"));
ok("tlToPoj oe 修正", nfc(tlToPoj("hue\u0304")) === nfc("ho\u0304e"));
ok("tlToPoj ui 修正", nfc(tlToPoj("ui\u0304")) === nfc("u\u0304i"));
ok("tlToPoj 有韻尾無徙", nfc(tlToPoj("kua\u0301n")) === nfc("koa\u0301n") && nfc(tlToPoj("gue\u030Dh")) === nfc("goe\u030Dh"));
ok("tlToPoj oai 無徙", nfc(tlToPoj("kua\u0300i")) === nfc("koa\u0300i"));
ok("tlToPoj 大寫 OA", nfc(tlToPoj("Gua\u0304")) === nfc("Go\u0304a") && nfc(tlToPoj("Ui\u0304")) === nfc("U\u0304i"));
ok("tlToPoj 空白分音節", nfc(tlToPoj("gua\u0304 hue\u0304")) === nfc("go\u0304a ho\u0304e"));
ok("tlToPoj 數字照舊", tlToPoj("gua7 hue7") === "goa7 hoe7");
ok("fix 冪等", nfc(pojFixDiacritics(tlToPoj("gua\u0304"))) === nfc(tlToPoj("gua\u0304")));
ok("免調顯示無 0", wc.words.every(x => !/[0-9]/.test(formatRomanization(x.reading))));
const r2 = decodeTlToHan("Guá ê lāu-pē sī lâng.", rev, lm);
ok("的 選中", r2.han.includes("的"));
// 標點/換行/未命中原樣保留
const keep = decodeTlToHan("Guá kin-á-ji̍t beh khì Tâi-pak.\nLí kám ē? xyz!", rev, lm);
ok("換行保留", keep.han.includes("\n"));
ok("未命中原字", keep.han.includes("xyz"));
// 隱性調號（v21）：有標調句內無調符音節＝1/4 聲；規句無調／--輕聲／mih 例外
// （句界佇標點重置——tsit 愛佮標調詞仝句才推斷著）
const r3 = decodeTlToHan("Goá khòaⁿ tsit ê ang--á", rev, lm);
ok("tsit→這（同句推斷 tone4）", r3.han.includes("這")
  && r3.words.find((x) => x.word === "這")?.reading === "tsit4");
const r5 = decodeTlToHan("li khi tai-pak", rev, lm); // 規句免調：mode 照舊
ok("tsi̍t→一", decodeTlToHan("Tsi̍t ê lâng khì Tâi-pak.", rev, lm).han.includes("一"));
const r4 = decodeTlToHan("Án-ne tsiah ē tsi̍t ê êng-ióng-sòo.", rev, lm);
ok("tsiah→才", r4.han.includes("才"));
ok("siánn-mih→啥物（mih 例外）", decodeTlToHan("Siánn-mih?", rev, lm).han.includes("啥物"));
ok("舊式 o·＝oo", decodeTlToHan("Tô·-su-kóan ū chheh.", rev, lm).han.includes("圖書館"));
ok("--輕聲維持免調", decodeTlToHan("Suà--lo̍h-lâi!", rev, lm).han.includes("紲落"));
ok("規句無調＝免調模式", r5.words.every((x) => !/[1-9]/.test(x.reading)));
// 句內變調：句尾本調、跨行 flush
const segs = segment("我今仔日欲去台北。\n伊教我唱歌。", dict);
const lt = new Map(JSON.parse(readFileSync(join(bundle, "hints.json"), "utf8")).lighttone.map((x) => [x.han, x.reading]));
const s1 = render(segs, new Map(), { sandhi: true, lighttone: lt });
ok("句尾本調 pak", nfc(s1.tl).includes(nfc("tāi-pak")));
ok("跨行不連讀（伊=i 本調）", /(^|。) I /.test(s1.tl) || s1.tl.includes("I ka") || s1.tl.includes("I kà") === false);
// render 層 e2e：實際呈現路徑（dict.js flush chain）出現代體 POJ
const rp = render(segment("我講台語。", dict), new Map(), { sandhi: false });
ok("render POJ góa（oa 標 o）", nfc(rp.poj).includes(nfc("Go\u0301a")));
ok("render POJ tâi-gí", nfc(rp.poj).includes(nfc("ta\u0302i-gi\u0301")));
const segs2 = segment("轉去食飯。", dict);
// 混寫：羅馬字直（無空白）黏漢字 → 反查合詞；前綴無合/有空白 → 隔空白分詞
const mx = render(segment("Pháiⁿ命人to̍h是艱苦人", dict, rev), new Map(), {});
ok("混寫合詞（Pháiⁿ命人→pháinn-miā-lâng）", nfc(mx.tl).includes(nfc("Pháinn-miā-lâng")));
ok("前綴無合勿綴（to̍h是→to̍h sī）", nfc(mx.tl).includes("to̍h sī "));
ok("混寫 POJ 雙軌（正式字形 ⁿ）", nfc(mx.poj).includes(nfc("Pháiⁿ-miā-lâng")));
ok("tsit款→這款", nfc(render(segment("tsit款", dict, rev), new Map(), {}).tl) === "Tsit-khuán");
const sp = render(segment("Pháiⁿ 命人 to̍h 是 艱苦人", dict, rev), new Map(), {});
const spt = nfc(sp.tl);
// 空白規則性質斷言（詞典成長予分詞變化：命人 會當是詞）：
// 輸入空白保留、無雙空白、羅馬字／漢字讀音之間單空白隔開。
ok("有空白照舊＋單空白", spt.startsWith(nfc("Pháiⁿ "))
  && spt.includes(nfc(" to̍h ")) && spt.endsWith(nfc("kan-khóo-lâng"))
  && !/\s\s/.test(spt) && !/^[\s-]|[\s-]$/.test(spt)
  && nfc(render(segment("Pháiⁿ miā lâng", dict, rev), new Map(), {}).tl) === nfc("Pháiⁿ miā lâng"));
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
