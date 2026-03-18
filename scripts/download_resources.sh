#!/bin/bash
# download_resources.sh — 下載所有外部資源到 data/ 目錄
# 所有 .git 目錄會被移除，data/ 整個列入 .gitignore
set -euo pipefail

DATA_DIR="$(cd "$(dirname "$0")/.." && pwd)/data"
mkdir -p "$DATA_DIR"

clone_and_degit() {
  local url="$1"
  local dest="$2"
  local desc="$3"
  if [ -d "$dest" ]; then
    echo "  [skip] $desc（已存在）"
  else
    echo "  [download] $desc"
    git clone --depth 1 "$url" "$dest" 2>&1 | tail -1
    rm -rf "$dest/.git"
  fi
}

echo "================================================"
echo " 拍台文 rime-phah-taibun 外部資源下載"
echo "================================================"
echo ""

echo "=== 1/20 ChhoeTaigi 台語字詞資料庫 ==="
echo "  主要字典來源：9 本辭典 CSV，353K 筆"
echo "  授權：各子資料庫不同（CC0 / CC BY-SA / CC BY-ND / CC BY-NC-SA）"
clone_and_degit \
  "https://github.com/ChhoeTaigi/ChhoeTaigiDatabase.git" \
  "$DATA_DIR/ChhoeTaigiDatabase" \
  "ChhoeTaigi/ChhoeTaigiDatabase"

echo ""
echo "=== 2/20glll4678/rime-taigi ==="
echo "  現有 Rime 台語方案，參考 schema 結構和方言碼（EI/EE/OO）"
clone_and_degit \
  "https://github.com/glll4678/rime-taigi.git" \
  "$DATA_DIR/rime-taigi-glll4678" \
  "glll4678/rime-taigi"

echo ""
echo "=== 3/20ryanwuson/rime-liur ==="
echo "  蝦米 Rime 方案，參考 Lua 模組架構（查碼、造詞、符號、日期）"
clone_and_degit \
  "https://github.com/ryanwuson/rime-liur.git" \
  "$DATA_DIR/rime-liur" \
  "ryanwuson/rime-liur"

echo ""
echo "=== 4/20YuRen-tw/rime-taigi-tps ==="
echo "  方音符號台語方案，參考字典格式和方音鍵盤配置"
clone_and_degit \
  "https://github.com/YuRen-tw/rime-taigi-tps.git" \
  "$DATA_DIR/rime-taigi-tps" \
  "YuRen-tw/rime-taigi-tps"

echo ""
echo "=== 5/20ButTaiwan/taigivs ==="
echo "  字咍台語字型，IVS 對照表（Phase 2 用）"
clone_and_degit \
  "https://github.com/ButTaiwan/taigivs.git" \
  "$DATA_DIR/taigivs" \
  "ButTaiwan/taigivs"

echo ""
echo "=== 6/20Taiwanese-Corpus/hue7jip8 ==="
echo "  台語/族語/客語語料清單彙整，含楊允言詞頻研究路徑"
clone_and_degit \
  "https://github.com/Taiwanese-Corpus/hue7jip8.git" \
  "$DATA_DIR/Taiwanese-Corpus-hue7jip8" \
  "Taiwanese-Corpus/hue7jip8"

echo ""
echo "=== 7/20g0v/moedict-data-twblg ==="
echo "  教育部台語辭典開放資料（JSON/CSV），建反查字典用"
clone_and_degit \
  "https://github.com/g0v/moedict-data-twblg.git" \
  "$DATA_DIR/moedict-data-twblg" \
  "g0v/moedict-data-twblg"

echo ""
echo "=== 8/20i3thuan5/khin1siann1-hun1sik4 ==="
echo "  輕聲分析器，含詞頻書寫規範（分詞邏輯參考）"
clone_and_degit \
  "https://github.com/i3thuan5/khin1siann1-hun1sik4.git" \
  "$DATA_DIR/khin1siann1-hun1sik4" \
  "i3thuan5/khin1siann1-hun1sik4"

echo ""
echo "=== 9/20LKK 用字表（Google Sheets CSV 下載）==="
echo "  李江却台語文教基金會漢羅用字規範"
LKK_BASE_URL="https://docs.google.com/spreadsheets/d/e/2PACX-1vR6sABIf13wvn95hKApMWmEYYD-vDL62mVAYBE1jycBRTkiJQush3-HCkkaPMSsv2cOcPZ0blNODFpx/pub"
if [ -f "$DATA_DIR/lkk_yongji.csv" ]; then
  echo "  [skip] LKK 字表 CSV（已存在）"
else
  echo "  [download] LKK 字表 CSV（gid=1364822222）"
  curl -sL "${LKK_BASE_URL}?gid=1364822222&single=true&output=csv" -o "$DATA_DIR/lkk_yongji.csv"
  echo "  → $(wc -l < "$DATA_DIR/lkk_yongji.csv") 行"
fi
if [ -f "$DATA_DIR/lkk_suji.csv" ]; then
  echo "  [skip] LKK 數字用法 CSV（已存在）"
else
  echo "  [download] LKK 數字用法 CSV（gid=1982799732）"
  curl -sL "${LKK_BASE_URL}?gid=1982799732&single=true&output=csv" -o "$DATA_DIR/lkk_suji.csv"
  echo "  → $(wc -l < "$DATA_DIR/lkk_suji.csv") 行"
fi
# 同時保留原始 HTML（若專案根目錄有的話）
PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LKK_HTML="$(ls "$PROJ_DIR"/LKK*.html 2>/dev/null | head -1)"
if [ -n "$LKK_HTML" ] && [ ! -f "$DATA_DIR/lkk_yongji.html" ]; then
  cp "$LKK_HTML" "$DATA_DIR/lkk_yongji.html"
  echo "  [copy] 原始 HTML → data/lkk_yongji.html"
fi

echo ""
echo "=== 9b/20 教育部推薦700字台語漢字 ==="
echo "  教育部公告700字台語漢字推薦用字表"
if [ -f "$DATA_DIR/700iongji.csv" ]; then
  echo "  [skip] 教育部700字 CSV（已存在）"
else
  echo "  [download] 教育部700字 CSV（yiufung/minnan-700）"
  curl -sL "https://raw.githubusercontent.com/yiufung/minnan-700/master/700iongji.csv" -o "$DATA_DIR/700iongji.csv"
  echo "  → $(wc -l < "$DATA_DIR/700iongji.csv") 行"
fi

echo ""
echo "=== 10/20Taiwanese-Corpus/Ungian_2009_KIPsupin ==="
echo "  楊允言詞頻資料（教育部臺灣閩南語字詞頻調查）"
clone_and_degit \
  "https://github.com/Taiwanese-Corpus/Ungian_2009_KIPsupin.git" \
  "$DATA_DIR/Ungian_2009_KIPsupin" \
  "Taiwanese-Corpus/Ungian_2009_KIPsupin"

echo ""
echo "=== 11/20i3thuan5/tai5-uan5_gian5-gi2_kang1-ku7 ==="
echo "  意傳臺灣言語工具（音標轉換用，含原始碼及 Python 套件）"
clone_and_degit \
  "https://github.com/i3thuan5/tai5-uan5_gian5-gi2_kang1-ku7.git" \
  "$DATA_DIR/tai5-uan5_gian5-gi2_kang1-ku7" \
  "i3thuan5/tai5-uan5_gian5-gi2_kang1-ku7"

echo ""
echo "=== 12/20ChhoeTaigi/KipSutianDataMirror ==="
echo "  教育部台語辭典鏡像（ODS + 音檔），比 moedict-data-twblg 更完整"
echo "  授權：CC BY-ND 3.0 Taiwan"
clone_and_degit \
  "https://github.com/ChhoeTaigi/KipSutianDataMirror.git" \
  "$DATA_DIR/KipSutianDataMirror" \
  "ChhoeTaigi/KipSutianDataMirror"

echo ""
echo "=== 13/20i3thuan5/KeSi ==="
echo "  POJ↔TL 轉換 Python 工具，比 tai5-uan5 更輕量"
echo "  授權：MIT"
clone_and_degit \
  "https://github.com/i3thuan5/KeSi.git" \
  "$DATA_DIR/KeSi" \
  "i3thuan5/KeSi"

echo ""
echo "=== 14/20Taiwanese-Corpus/icorpus_ka1_han3-ji7 ==="
echo "  iCorpus 臺華平行新聞語料庫（2008-2014），可算真實詞頻"
clone_and_degit \
  "https://github.com/Taiwanese-Corpus/icorpus_ka1_han3-ji7.git" \
  "$DATA_DIR/icorpus_ka1_han3-ji7" \
  "Taiwanese-Corpus/icorpus_ka1_han3-ji7"

echo ""
echo "=== 15/20Taiwanese-Corpus/nmtl_2006_dadwt ==="
echo "  台語漢羅及全羅文學作品 2,169 篇，漢羅書寫慣例黃金參考"
clone_and_degit \
  "https://github.com/Taiwanese-Corpus/nmtl_2006_dadwt.git" \
  "$DATA_DIR/nmtl_2006_dadwt" \
  "Taiwanese-Corpus/nmtl_2006_dadwt"

echo ""
echo "=== 16/20Taiwanese-Corpus/moe_minkalaok ==="
echo "  閩南語卡拉OK正字字表，教育部用字規範參考"
clone_and_degit \
  "https://github.com/Taiwanese-Corpus/moe_minkalaok.git" \
  "$DATA_DIR/moe_minkalaok" \
  "Taiwanese-Corpus/moe_minkalaok"

echo ""
echo "=== 17/20Taiwanese-Corpus/Khin-hoan_2010_pojbh ==="
echo "  白話字文獻館（歷史 POJ 語料，台灣師範大學 2007-2010）"
clone_and_degit \
  "https://github.com/Taiwanese-Corpus/Khin-hoan_2010_pojbh.git" \
  "$DATA_DIR/Khin-hoan_2010_pojbh" \
  "Taiwanese-Corpus/Khin-hoan_2010_pojbh"

echo ""
echo "=== 18/20ChhoeTaigi/Kam-Ui-lim_1913_Kam-Ji-tian ==="
echo "  甘字典 CSV 原始版（1913 年甘為霖台語辭典）"
echo "  授權：CC BY-NC-SA"
clone_and_degit \
  "https://github.com/ChhoeTaigi/Kam-Ui-lim_1913_Kam-Ji-tian.git" \
  "$DATA_DIR/Kam-Ui-lim_1913_Kam-Ji-tian" \
  "ChhoeTaigi/Kam-Ui-lim_1913_Kam-Ji-tian"

echo ""
echo "=== 19/20 Taiwanese-Corpus/kok4hau7-kho3pun2 ==="
echo "  國小台語課本（康軒版），12冊漢字+台羅對照"
clone_and_degit \
  "https://github.com/Taiwanese-Corpus/kok4hau7-kho3pun2.git" \
  "$DATA_DIR/kok4hau7-kho3pun2" \
  "Taiwanese-Corpus/kok4hau7-kho3pun2"

echo ""
echo "=== 20/20 Taiwanese-Corpus/Sin1pak8tshi7_2015_900-le7ku3 ==="
echo "  常用900例句（詞條漢字+台羅+例句），日常高頻詞彙"
clone_and_degit \
  "https://github.com/Taiwanese-Corpus/Sin1pak8tshi7_2015_900-le7ku3.git" \
  "$DATA_DIR/Sin1pak8tshi7_2015_900-le7ku3" \
  "Taiwanese-Corpus/Sin1pak8tshi7_2015_900-le7ku3"

echo ""
echo "================================================"
echo " 自動下載完成！"
echo "================================================"
echo ""
echo "data/ 目錄："
du -sh "$DATA_DIR"/*/  2>/dev/null || ls -1d "$DATA_DIR"/*/
echo ""
echo "================================================"
echo " 待手動處理（需使用者操作）"
echo "================================================"
echo ""
echo "1. 意傳臺灣言語工具（Python NLP 套件，音標轉換用）"
echo "   uv add tai5-uan5_gian5-gi2_kang1-ku7"
echo "   文件：https://i3thuan5.github.io/tai5-uan5_gian5-gi2_kang1-ku7/"
echo ""
echo "2. 芫荽字體（ChhoeTaigi/iansui，專為台文設計，SIL OFL 授權）"
echo "   建議安裝以獲得最佳台文顯示效果"
echo "   https://github.com/ChhoeTaigi/iansui"
echo ""
echo "================================================"
