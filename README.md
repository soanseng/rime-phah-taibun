# 讀台文 Tha̍k Tâi-bûn

漢羅 ⇄ 台羅 TL／白話字 POJ 一頁式網頁：貼漢羅文章即時轉出台羅（TL）佮白話字（POJ）雙軌對照，點漢字換讀音，做拼音練習、查詞彙——攏免安裝、免後端。

讀台文是 [拍台文 Phah Tâi-bûn](https://github.com/soanseng/rime-phah-taibun)（Rime 台語輸入法）的姊妹品：拍台文予你**拍**台文，讀台文予你**讀**台文。

## 功能

- **轉換**：漢羅 → TL／POJ 雙軌。多音字點漢字循環切換讀音；詞典揣無的字顯示 ⟨?⟩。
- **羅→漢（實驗）**：拍台羅／POJ（免調、數字調攏會使）出漢字佮 TL 正規化。同音詞真濟，可能選錯詞義，僅供輔助對照。
- **拼音練習**：看漢字拍台羅——免調就算對，拍調號嘛會當；比對該詞全部讀音（方言變體攏接受）。
- **詞彙查詢**：台語詞／華語釋義查詢，附 TL、POJ、華語對照。
- **學習提示**：輕聲建議（親像「轉去」→ 轉--去）＋華語直譯通用小提醒。
- **教典連結**：詞條直接連去[教育部臺灣台語常用詞辭典](https://sutian.moe.edu.tw/und-hani/)。

手機、平板、桌機攏好用（RWD），字型用 [芫荽 Iansui](https://fonts.google.com/specimen/Iansui)（支援 𠢕、𤆬、𨑨迌 等台語推薦用字）。

## 品質數字（誠實標註）

| 項目 | 數字 | 說明 |
|---|---|---|
| 漢→TL | 90.1／89.8／90.6% 去調相似、約 99% 字元涵蓋 | 三篇真實文章（10／6／8 對）嚴格配對；POJ 無對照稿未計分 |
| 羅→漢（實驗） | lattice 88.4／89.4／89.3%｜greedy 58.3／60.8／62.0% | 三篇＝開發集／held-out#1／held-out#2（全新未觸碰）。第三篇前建置曾依前兩篇輸出迭代，屬漸進驗證。殘餘誤差＝同鍵同調同頻極端同音（儲存/除船、濟/坐） |

> 羅→漢仍屬實驗：同音詞歧義（的/個、人/膿、新聞/訊問）與語料域偏移（identity 為新聞體）
> 會造成誤選；標點、斷行、未命中音節原樣保留。

| 來源 | 授權 |
|---|---|
| iTaigi 華台對照典 | CC0 |
| 台華線頂對照典、台灣植物名彙 | CC BY-SA 4.0 |
| 教育部「以本土語言標注臺灣地名」 | CC BY 3.0 TW |
| 教育部 STTI 學科術語臺灣台語對譯 | 依官方說明開放運用、標示來源 |
| 新北市 900 例句工作坊（Taiwanese-Corpus） | MIT（上游 repo 聲明） |
| 李江却台語文教基金會 LKK 用字表 | 標示來源（非商用） |
| iCorpus 詞頻 | CC BY 4.0 |
| 教育部臺灣台語常用詞辭典（萌典版 dict-twblg，例句衍生統計） | CC BY-ND 3.0 TW（標示來源；本站非商用） |

BY-SA 資料之衍生詞典包隨 repo 提供（`data-public/dict.json`）；各來源授權以原釋出條款為準。


> **授權複核注意**：STTI 官方計畫說明「提供一般大眾參考運用」並要求標示來源，
> 但其網站版權標示為 All rights reserved——兩者尚待釐清；公開部署前建議完成
> 該來源之授權複核，佮確認 CC BY-SA 資料的分發義務（隨附 `data-public/` 即為
> 可下載之衍生資料集）。

## 開發

```bash
# 產生資料包（需 sibling 目錄 rime-phah-taibun 佮伊的 data/）
python3 tools/build.py --mode public --out data-public

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
- [x] bigram 語言模型提升羅→漢（identity＋900句＋詞典短語＋教典例句，58.3%→78.7%）
- [ ] 900 例句句級練習
- [ ] 補齊 之／枵／植／臨 等缺詞
- [ ] 多字結構文法建議（這馬干焦通用對照表）

## 授權

程式碼：MIT。資料：依各來源條款（見上表）。
