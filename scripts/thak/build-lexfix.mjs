// 字辭典補正（冪等，重跑覆寫）：dict.json 讀音修正——LEXICON_FIXES
// （教典根據，逐條附證據）。
// 執行：bun scripts/thak/build-lexfix.mjs
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const root = new URL("../../docs/thak/", import.meta.url).pathname;
const dir = join(root, "data-public");



// ---- 1) 讀音修正（源頭：build 表格內底資料愛嘛修；這遮先補成品 bundle）----
const LEXICON_FIXES = {
  // 教典「一」文讀 it（入聲 4）；it8 予隱性調推斷揀錯字（驗證 103 擺反例）
  "一": { replace: { it8: "it4" } },
  // 教典「相同」siong-tâng→siong1（文讀陰平）；表內干焦 siong3（siòng）
  "相": { add: ["siong1"] },
};
const dictPath = join(dir, "dict.json");
const dict = JSON.parse(readFileSync(dictPath, "utf8"));
let fixed = 0;
for (const [w, fx] of Object.entries(LEXICON_FIXES)) {
  const e = dict[w];
  if (!e) continue;
  if (fx.replace) e.r = e.r.map((r) => fx.replace[r] ?? r);
  if (fx.add) for (const r of fx.add) if (!e.r.includes(r)) e.r.push(r);
  fixed++;
}
writeFileSync(dictPath, JSON.stringify(dict));
console.log(`LEXICON_FIXES: ${fixed} 詞條`);



// 註：教育部建議用字（LKK 900/700）做過「候選詞紅利」A/B——音讀鍵相撞
// （a→阿 四界討票）四語料 -0.5，弊多於利，已拆。欲支援異用字顯示，
// CSV 佇 rime-phah-taibun/data/{lkk_yongji,700iongji}.csv。
