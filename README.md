# 讀台文 Tha̍k Tâi-bûn

漢羅 ⇄ 台羅 TL／白話字 POJ 一頁式網頁：貼漢羅文章即時轉出台羅（TL）佮白話字（POJ）雙軌對照，點漢字換讀音，做拼音練習、查詞彙——攏免安裝、免後端。

讀台文是 [寫台文 Siá Tâi-bûn](https://taigi.anatomind.com/)（[rime-phah-taibun](https://github.com/soanseng/rime-phah-taibun)，RIME 台語輸入法，舊名拍台文）的姊妹品，共用仝一个轉換核心：寫台文予你**寫**台文，讀台文予你**讀**台文。

## 功能

- **轉換**：漢羅 → TL／POJ 雙軌。多音字點漢字循環切換讀音；詞典揣無的字顯示 ⟨?⟩。POJ 出正式字形（oo→o͘、nn→ⁿ、ts→ch、ua→oa）兼 POJ 調符定位（gōa、hōe、chúi；有韻尾照舊：koán、goe̍h）。混寫無空白嘛會使：羅馬字直接黏漢字會試佮詞典合做一个詞（「Pháiⁿ命人」→ 歹命人 → pháinn-miā-lâng；「hit款」→ 彼款），組袂起就隔做空格（to̍h是 → to̍h sī）。已知限制：去調合詞袂分同音異詞，「mā人格」會揀著「罵人」（嘛／罵 攏 ma7），語境歧義佮羅→漢解碼仝款。
- **羅→漢（實驗）**：拍台羅／POJ（免調、數字調、調符攏會使）出漢字佮 TL 正規化。有標調句內無調符音節按正字法當 1/4 聲（`tsit`→這、`tsi̍t`→一）。同音詞真濟，可能選錯詞義——詞對照卡點會循環換同音詞，僅供輔助對照。
- **拼音練習**：看漢字拍台羅——免調就算對，拍調號嘛會當；比對該詞全部讀音（方言變體攏接受）。
- **詞彙查詢**：台語詞／華語釋義查詢，附 TL、POJ、華語對照。
- **學習提示（輸入區文法檢查佮教學，建議性質）**：① 用字建議——華台對照表比對（上長片語優先、span 袂重複列），有筆記的會使點「看文法」② 輕聲標記建議 ③ **可能用著的文法點** chip：照筆記觸發詞（漢字子字串／臺羅詞界／疊字正規）掃，點了跳去文法頁彼篇。純規則比對、毋是語法解析：攏是「建議檢查／可參考」，毋是判對毋著。
- **教典連結**：詞條直接連去[教育部臺灣台語常用詞辭典](https://sutian.moe.edu.tw/und-hani/)。
- **Landing／SEO**：頂蒂例句卡（教典真實句，點一句直接看變調讀音＋POJ）；canonical／og:url／JSON-LD（WebApplication）／robots.txt／sitemap.xml 攏指向 https://thak.anatomind.com/ 。
- **性能**：詞典 6.8MB 佇 worker 解析＋反查索引、分段 ack 傳轉主線程（主線程無 long task）；句庫／詞彙例句拍到分頁才載；字體 `display=optional`＋非同步 CSS（CLS 0）；jQuery defer。Lighthouse（本機 headless-shell，2026-10-07）：SEO／A11y／Best-Practices **100/100/100**，Performance mobile 69／desktop 73——行動版 TBT 大頭是 jQuery 佇節流環境的評估時間（~3s），家己的載入鏈已無 long task。

手機、平板、桌機攏好用（RWD），字型用 [芫荽 Iansui](https://fonts.google.com/specimen/Iansui)（支援 𠢕、𤆬、𨑨迌 等台語推薦用字）。

## 品質數字（誠實標註）

| 項目 | 數字 | 說明 |
|---|---|---|
| 漢→TL | 90.2／90.3／91.2／90.1% 去調相似、100% 字元涵蓋 | 四篇真實文章（10／6／8／12 對）嚴格配對；POJ 無對照稿未計分。延伸詞層（拍台文字典 fallback）上線後 ⟨miss⟩ 歸零 |
| 羅→漢（實驗） | lattice 92.6／93.2／92.1／89.9%｜greedy 59.5／62.4／63.2／61.1% | 開發集／held-out×3。2026-10-07 升級（+2.7～+4.0）：隱性調號（有標調句內無調符＝1/4 聲，`tsit`→這、`beh`→欲）、讀音條件化 unigram（runi：「到」的 373 全是 kau 用法，袂使替 tio̍h 討票）、教典收錄訊號取代 gloss 紅利（𪜶/抑 無釋義）、≥2 連續未知音節逐字文讀組詞（抗原、儲存）。第四篇（醫學＋英文專名）略低：免疫學複合詞多在詞典外。殘餘誤差＝同鍵同調的同音詞——詞對照卡點選會循環換同音詞 |

> 羅→漢仍屬實驗：同音詞歧義（的/個、人/膿、新聞/訊問）與語料域偏移（identity 為新聞體）
> 會造成誤選；標點、斷行、未命中音節原樣保留。
> **獨立最後測試（2026-10-07）**：蔡培火《十項管見》（1925，純 POJ 全書，
> zh-min-nan.wikisource）十章 19,873 音節——涵蓋 99.5%、零 crash、輸出可讀；
> 語料 `tools/wikisource/`、測試 `tools/wikisource-r2h.mjs`。舊式 `o·` 中點
> 未入解碼（當分隔音節），1925 拼法（Tâi-oan、gîn）靠 pojToTl 轉換無問題。

| 來源 | 授權 |
|---|---|
| iTaigi 華台對照典 | CC0 |
| 台華線頂對照典、台灣植物名彙 | CC BY-SA 4.0 |
| 教育部「以本土語言標注臺灣地名」 | CC BY 3.0 TW |
| 教育部 STTI 學科術語臺灣台語對譯 | 依官方說明開放運用、標示來源 |
| 新北市 900 例句工作坊（Taiwanese-Corpus） | MIT（上游 repo 聲明） |
| 李江却台語文教基金會 LKK 用字表 | 標示來源（非商用） |
| 拍台文字典 rime-phah-taibun 主詞庫（延伸詞層） | 混合授權、非商業：CC0＋CC BY-SA 4.0＋CC BY-ND 3.0 TW＋**CC BY-NC-SA 3.0 TW**（台日大辭典、Maryknoll、Embree、甘字典）＋待確認來源（[rime LICENSE](https://github.com/soanseng/rime-phah-taibun/blob/main/LICENSE) 完整揭露）。使用者 2026-09-29 裁定照 rime repo 2026-09-24 慣例（非商業＋完整揭露）入公開包。補本典建立層缺詞讀音（1–4 字、頻率≥500、音節＝字數），UI 標〔延伸詞〕、教典收錄狀態用 twblg title 精確核對（教典未收／教典有收） |
| iCorpus 詞頻 | CC BY 4.0 |
| 教育部臺灣台語常用詞辭典（萌典版 dict-twblg，例句衍生統計） | CC BY-ND 3.0 TW（標示來源；本站非商用） |
| 臺灣台語語料庫應用檢索系統 TGGL（國家教育研究院，文法頁） | 語料庫授權條款：**只收書目索引**（編號／語法點／臺羅／群組），說明佮例句不重刊、外連原站；標示來源、致謝教育部 |
| 文法筆記（grammar-notes.json，data-public/） | 說明自寫、分類自訂；例句以教典真實句為主（逐句標〔教典〕，連官方華語對譯照原句重刊，CC BY-ND 3.0 TW、標示來源），無適配句主題用自造句（標〔自造〕）；自造句對譯與註記本站加 |
| 維基學院《閩南語文法》（筆記參考之一） | CC BY-SA 4.0（僅標示來源連結，未抄錄內文；其採閩拼，非臺羅） |
| 廖淑鳳（2007）〈國小台語教科書基本句型練習研究〉（臺師大碩論） | 文法筆記的虛詞／複句／語氣詞框架參考；僅書目引用、未抄錄內文 |
| 郭永錕（2016）《台語《語法》》講義（高雄市政府教育局） | 疑問／否定句型框架參考；僅書目引用、未抄錄內文 |
| 塗豆仁學台語（2024-10-03）臉書〈台語的十個特色文法〉 | 特色句法／輕聲框架；例句自造，無重刊貼文原句 |
| 李淑鳳（2013）〈台語連詞和副詞的關聯性〉，《台灣學誌》第7期 | 「愈／那」連用分類參考；僅書目引用、未抄錄內文 |

BY-SA 資料之衍生詞典包隨 repo 提供（`data-public/dict.json`）；各來源授權以原釋出條款為準。


> **授權複核注意**：STTI 官方計畫說明「提供一般大眾參考運用」並要求標示來源，
> 但其網站版權標示為 All rights reserved——兩者尚待釐清；公開部署前建議完成
> 該來源之授權複核，佮確認 CC BY-SA 資料的分發義務（隨附 `data-public/` 即為
> 可下載之衍生資料集）。

> **STTI 入包對帳（2026-09-27）**：5,515 條中 5,467 入包；48 拒收＝39 條
> 台語詞欄非純漢字（羅馬字借詞親像 phi̋n-phóng、數字條）＋9 條純漢字但
> 音節數佮字數不符（親像 海邊仔=hai2 pinn1，來源資料本身不一致）。

## 開發

```bash
# 產生資料包（需 sibling 目錄 rime-phah-taibun 佮伊的 data/）
python3 tools/build.py --mode public --out data-public

# build 後處理（冪等）：教典例句→讀音條件化 unigram（bigrams.json）
# ＋教典讀音補正（dict.json：一 it4、相 siong1）
bun tools/build-runi.mjs && bun tools/build-lexfix.mjs
# 重抓 TGGL 語法點索引 → data-public/grammars.json（只取中繼資料，原文不落地）
node tools/fetch-grammar.mjs

# 本機起 web server
python3 -m http.server 8765
# 打開 http://127.0.0.1:8765/
```

依賴：Python 3.10+（建置）、jQuery 4.0（CDN）、芫荽字型（Google Fonts）。無建置步驟——純靜態檔案。

## 部署（Cloudflare Pages）

1. Fork/clone 本 repo，推去 GitHub。
2. Cloudflare Pages → Create project → Connect to Git → 選本 repo。
3. Build settings：**Framework preset** `None`、**Build command** 留空、**Build output directory** `/`（根目錄）。
4. Deploy。`data-public/dict.json` 已在版控內，無需要額外建置。

## Roadmap（v2）

- [x] 連讀變調 toggle（詞內連讀近似）佮輕聲詞顯示（`--`）
- [x] bigram＋trigram 語言模型（identity＋900句＋詞典短語＋教典例句）。**A/B 消融（`tools/ablation-trigram.mjs`）**：例句域 84.67→84.71%（+0.04pp），四語料 0.00 差——trigram 零退化、醫學/新聞域零覆蓋（1,909 條文語三元組），日常域微增益。四語料 lattice 88.4/89.4/89.0/83.6%
- [x] 句級練習（教典例句 11,512 句，逐句併教典原文核對；CC BY-ND 3.0 TW 標示來源；逐詞免調比對＋錯題加重抽樣）
- [x] 詞彙例句（教典，CC BY-ND 3.0 TW，標示來源）
- [x] 補齊 之／枵／植／臨 等缺詞（讀音內證自本典複詞）
- [x] 多字結構文法建議：華語→台語對照表擴充 13 條多字結構（的時候→時陣、看不懂→看無、越來越→愈來愈…），UI 只顯示文章命中（多字優先），全表收 details；標明「參考用，毋是自動文法解析」。註：曾試「未命中長詞拆詞建議」，因 segment 佮拆解用仝一個貪婪匹配、數學上拆袂出新詞，已撤

## Roadmap（v2.1）

- [x] 輸入區文法檢查佮教學（`js/ui/grammarcheck.js`，建議性質）：calque 對照 28→39 條——新增 12 條先對本典（dict.json）稽核（我們／你們／他們／知道／喜歡／還是／哪裡／怎麼／昨天／這裡／那裡／是不是，獨立詞佮子字串零碰撞）；11 條試加後著詞典碰撞（呢⊂按呢、但是、不過、今天、明天、時候、可以、如果、誰、嗎⊂嗎啡、吧⊂酒吧）已撤。grammar-notes 25 篇有觸發詞 `match`／`matchRe`（共：避開 一共／總共／共同；疊字：X X；結構主題 3 篇無固定觸發詞），chip 點了 `revealNote()` 跳文法頁滾動＋閃爍。fetch race：notes 載入後補 render。

## 授權

程式碼：MIT。資料：依各來源條款（見上表）。
- [x] per-key 調號頻率 prior：變調形輸入（連讀輸出貼回解碼）+0.5~+1.8pp，
  本調輸入零變動。雙護欄：①同鍵有全對候選（本調）不免罰（保 新聞/訊問 鑑別）
  ②tonefreq 愛 ≥2 調形記錄才用分布（單調形鍵 share=1＝全面減罰、無鑑別性，
  無護欄版回圈 +6.2pp 就是這種病態增益，已除）。tonefreq 14,763 鍵（主讀音 once/詞）
