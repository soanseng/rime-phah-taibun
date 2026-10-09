// 寫作檢查 × 真實語料（教育部教典例句，docs/study/data/listen.json 頭 200 句）：
// 教育部家己的台文／台羅＝標準，應該真少受點（誤報）；仝批例句的華語翻譯應該大部分有標（檢出）。
// 規則若變吵（親像子字串比對、連字符收著語料片語），這个測試會先擋。
// 數字照 2026-10-09 實測（均勻抽樣：台文 8%、台羅 1.5%、華語 88.5%）留寬限；
// 規則是對頭 200 句調的，這是護欄，毋是獨立的準確率估計。詳細報告：bun scripts/thak/check-eval.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  runChecks, buildSyllableSet, buildMultiReadings, buildAltMap, buildLkkMap,
  buildCharMap, buildWordReadings, buildGlossIndex,
} from "../../docs/check/check-core.js";
import { segment, buildReverseIndex } from "../../docs/thak/js/dict.js?v=26";

const J = (p) => JSON.parse(readFileSync(new URL(`../../${p}`, import.meta.url), "utf8"));
const dict = J("docs/thak/data-public/dict.json");
const rev = buildReverseIndex(dict);
const yongji = J("docs/study/data/yongji.json");
const base = {
  syllableSet: buildSyllableSet(dict),
  multiReadings: buildMultiReadings(dict, new Set(J("docs/check/data/hyphen-words.json").words)),
  altMap: buildAltMap(J("docs/study/data/iongji.json").items),
  lkkMap: buildLkkMap(yongji.items),
  charMap: buildCharMap(yongji.items),
  wordReadings: buildWordReadings(yongji.items),
  recWords: new Set(yongji.items.map((it) => it.word)),
  glossIndex: buildGlossIndex(dict),
  dict,
  hints: J("docs/thak/data-public/hints.json"),
};
const check = (t) => runChecks(t, { ...base, mode: "moe", segments: segment(t, dict, rev) });
// 900 句均勻抽 200 句（固定可重現；頭尾攏有份，毋是頭 200 句）
const all = J("docs/study/data/listen.json").items;
const leku = Array.from({ length: 200 }, (_, i) => all[Math.floor((i * all.length) / 200)]);
const rate = (texts) => texts.filter((t) => check(t).length).length / texts.length;

test("教典台文（教育部 700 模式）：受點的句 ≤ 12%", () => {
  const r = rate(leku.map((x) => x.han));
  assert.ok(r <= 0.12, `台文誤報率 ${(r * 100).toFixed(1)}%`);
});

test("教典台羅：連字符／拼寫幾乎無受點（教育部寫法就是標準）", () => {
  const n = leku.flatMap((x) => check(x.tl)).length;
  assert.ok(n <= 5, `台羅受點 ${n} 條`);
});

test("仝批例句的華語翻譯：≥ 85% 有標（華語用字／直譯／句式）", () => {
  const r = rate(leku.map((x) => x.hoa));
  assert.ok(r >= 0.85, `華語檢出率 ${(r * 100).toFixed(1)}%`);
});
