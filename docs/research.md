# 研究與資料來源

拍台文不是只手寫一份 Rime 字典。這頁記錄landing page「數字看拍台文」背後的完整故事：統計怎麼算、資料怎麼來、建置流程長什麼樣。

## 統計數字怎麼來的

首頁的四個數字與詞長分布圖，全部從出貨的 `schema/phah_taibun.dict.yaml` 直接計算：

- **221,792 詞條**：主字典的總行數（`tests/test_landing_stats.py` 重新計算並釘住首頁顯示值）。
- **詞長分布**：以讀音欄的連字符/空白切音節——1 音節 24,161、2 音節 121,621、3 音節 55,651、4 音節以上 20,359。超過一半的詞是兩音節，這是「連打整詞出現」設計的底氣。
- **5,424 個一字多音字**：同一個漢字在字典中有兩個以上讀音（文白異讀等），像講（káng·kóng·khiáng）、飯（pn̄g·huān）、翼（si̍t·i̍k）、喙（tshuì·huī）。輸入時你打得出其中任何一種讀法，候選都會列出来。
- **353K → 221,792**：ChhoeTaigi 9 本辭典的原始字詞約 353K 筆，經清洗、去重、格式驗證後進主字典，再併入教育部學科術語與臺灣地名詞條；詞身份以（漢字, 正規化 TL 讀音）成對判定，只有漢字或只有讀音都不算同一個詞。

## 建置流程

`scripts/` 會下載 23 個語言資源，轉換 ChhoeTaigi CSV 與教育部 KipSutian ODS、抽取語料詞頻、建立華語反查、解析 LKK 與教育部推薦用字、產生輕聲詞條、匯入人工詞庫增補、併入教育部學科術語佮臺灣地名詞條、擷取雙字詞組，最後再驗證 Rime 字典格式。

1. **辭典轉換**：iTaigi、台華線頂、台日、Maryknoll、Embree、教育部、甘字典與 KipSutian ODS 等資料轉成 Rime 可用格式。
2. **詞頻加權**：從 iCorpus、Ungian 2009、康軒課本、900 例句、NMTL、KipSutian、白話字文獻抽詞頻，讓常用詞優先。
3. **人工增補詞庫**：把建中的增補 CSV 轉成 Rime 詞條，跳過不合法拼音，並記錄重複與品質報告。
4. **教育部官方詞條**：解析學科術語 ODS 佮地名 ODT 清單（僅取臺灣台語欄），附上華語對照進反查表；地名括號／斜線替讀會展開，第一優勢腔為主要讀音、第二優勢腔低權重列出。
5. **輸入體驗資料**：建立華語→台語反查、輕聲候選、bigram 詞組、LKK 漢羅規則與 MOE 700 字推薦標記。

## 楊允言老師的字詞頻研究

`scripts/extract_ungian_freq.py` 讀取 **Ungian_2009_KIPsupin** 專案中的 JSON 資料。這份資料來自楊允言老師提供的「教育部臺灣閩南語字詞頻調查工作」，內容是台語文作品整理成教育部台羅（KIP/TL）後的語料。腳本會解析 1,093 個 JSON 檔，抽出台羅行、切出詞 token，統計每個詞出現次數，也輸出句子給 bigram 詞組建置使用。

這很重要，因為輸入法不能只知道「有哪些字詞」，還要知道「哪些字詞在文章裡比較常出現」。有了文學與書面台語的詞頻，拍台文可以把常用詞排前面，減少選字，也讓漢羅文章、創作、教學和長文輸入更順。

## 設計細節

這些是首頁「設計細節精選」三條的完整版：

- **萬用查字不只開頭可用**：不確定哪一段拼音時，可以打 `si?`、`s?ah`、`tsh?` 這類模式查音節，再進一步選字。
- **字典查無的詞也能逐音節組**：打 `kio-tiann` 或整句連打，候選自動逐音節組合；用 `-` 斷音節，`Tab` 逐字選出想要的字——選字就是選調，最後送出如「橋鼎」。
- **字典裡的詞，連打會整詞出現**：詞典權重保證整詞優先：連續輸入 `tsiah8-png7`，「食飯」會以整詞排在前頭，不會被拆成單字組句；高頻單字也搶不走整詞的位置。字典外的詞才走逐音節組合。
- **注音反查會回到台語候選**：用 `~` 從華語注音找字後，會把台語拼音送回主輸入流程，並在註解和全羅輸出中顯示調符。
- **輕聲候選來自字典和規則**：從語料建立輕聲詞條，也在輸入時即時產生輕聲候選，保留 `--` 標記，像「轉--來」「食--飽」這種用法不會被吃掉。
- **POJ/TL 調符細節有特別處理**：針對 `oa`、`oe`、`ui`、`iu`、`nng`、`nn` 轉 `ⁿ` 等細節反覆修正，避免輸出看起來不像真正的白話字或台羅。
- **候選區直接提示推薦用字**：**◆** 標示推薦漢字，**★** 標示推薦羅馬字，來源包含 LKK 漢羅規範與教育部推薦用字 700 字詞。
- **鍵盤流程為長文輸入調整**：`Tab` 可進入 `asdfghjkl;` 選字，數字鍵保留給聲調；`\` 可在漢羅和全羅間切換，輸出模式會記住。

## 外部資源（23 個）

### 辭典與用字標準

- [ChhoeTaigi 台語字詞資料庫](https://github.com/ChhoeTaigi/ChhoeTaigiDatabase)：9 本辭典 CSV，353K 筆原始字詞資料。
- [KipSutianDataMirror](https://github.com/ChhoeTaigi/KipSutianDataMirror)：教育部台語辭典鏡像，ODS 詞目進主字典並提供注音反查讀音，例句進詞頻語料。
- [LKK 用字表](https://www.tgb.org.tw/)：李江却台語文教基金會漢羅用字規範（Google Sheets 公開），決定哪些詞輸出漢字或羅馬字。
- [教育部推薦 700 字](https://github.com/yiufung/minnan-700)：候選區 ◆ 推薦漢字標記。
- [建中的教育部臺灣台語輸入法詞庫增補檔案](https://github.com/luke871016/Taigi-Input-method-dictionary-supplement)：政府機關、行政區、數字時間日期、常見人名、台/臺變體與 LKK 羅馬字詞。
- [moe_minkalaok](https://github.com/Taiwanese-Corpus/moe_minkalaok)：閩南語卡拉OK正字字表，作為教育部用字規範參考。
- [甘字典 CSV 原始版](https://github.com/ChhoeTaigi/Kam-Ui-lim_1913_Kam-Ji-tian)：1913 年甘為霖台語辭典。

### 教育部官方資料

- [學科術語臺灣台語對譯（STTI）](https://stti.moe.edu.tw/)：8 大領域學科術語的台語對譯（5,500+ 詞條），只取臺灣台語欄。官方計畫說明「提供一般大眾參考運用」，依其要求標示來源；站點版權標示為 All rights reserved。
- [以本土語言標注臺灣地名](https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/twplacename.html)：第 1 階段鐵路／捷運／高鐵／台灣好行站名清單＋第 2 階段行政區、聚落、自然實體、公共設施、街道（9,000+ 詞條），創用 CC 姓名標示 3.0 臺灣。僅取臺灣台語欄；第一優勢腔為主要讀音（權重 700），第二優勢腔為替讀（650）。

### 語料與詞頻

- [Taiwanese-Corpus/hue7jip8](https://github.com/Taiwanese-Corpus/hue7jip8)：台語、族語、客語語料清單，包含楊允言詞頻研究路徑。
- [Ungian_2009_KIPsupin](https://github.com/Taiwanese-Corpus/Ungian_2009_KIPsupin)：楊允言詞頻資料，教育部臺灣閩南語字詞頻調查。
- [iCorpus 臺華平行新聞語料庫](https://github.com/Taiwanese-Corpus/icorpus_ka1_han3-ji7)：2008-2014 新聞語料，計算真實新聞用詞頻率。
- [NMTL 文學語料](https://github.com/Taiwanese-Corpus/nmtl_2006_dadwt)：2,169 篇台語漢羅與全羅文學作品，作為漢羅書寫慣例參考。
- [白話字文獻館](https://github.com/Taiwanese-Corpus/Khin-hoan_2010_pojbh)：歷史 POJ 語料，經 POJ→TL 轉換後納入詞頻。
- [康軒國小台語課本](https://github.com/Taiwanese-Corpus/kok4hau7-kho3pun2)：12 冊漢字與台羅對照，補日常教學詞彙。
- [常用 900 例句](https://github.com/Taiwanese-Corpus/Sin1pak8tshi7_2015_900-le7ku3)：詞條漢字、台羅與例句，補日常高頻詞。

### 輸入法與語言工具參考

- [glll4678/rime-taigi](https://github.com/glll4678/rime-taigi)：既有 Rime 台語方案，參考 schema 結構與方言碼。
- [rime-liur](https://github.com/ryanwuson/rime-liur)：蝦米 Rime 方案，參考查碼、造詞、符號、日期等 Lua 模組架構。
- [rime-taigi-tps](https://github.com/YuRen-tw/rime-taigi-tps)：方音符號台語方案，參考字典格式與方音鍵盤配置。
- [意傳輕聲分析器](https://github.com/i3thuan5/khin1siann1-hun1sik4)：輕聲詞頻、書寫規範與分詞邏輯參考。
- [意傳臺灣言語工具](https://github.com/i3thuan5/tai5-uan5_gian5-gi2_kang1-ku7)：音標轉換與台文 NLP 工具參考。
- [KeSi](https://github.com/i3thuan5/KeSi)：輕量 POJ↔TL 轉換工具。

### 字型與字形

- [ButTaiwan/taigivs](https://github.com/ButTaiwan/taigivs)：字咍台語字型與 IVS 對照表，作為特殊台文漢字顯示參考。

各來源的授權與商用限制，詳見 [LICENSE](https://github.com/soanseng/rime-phah-taibun/blob/main/LICENSE) 的 per-source 對照表。
