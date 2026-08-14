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
  local revision="$4"
  if [ -d "$dest" ]; then
    if [ ! -f "$dest/.source-revision" ] || [ "$(cat "$dest/.source-revision")" != "$revision" ]; then
      echo "  [error] $desc 已存在但修訂不明或不符；請刪除 $dest 後重試" >&2
      exit 1
    fi
    echo "  [skip] $desc @ ${revision:0:12}"
  else
    echo "  [download] $desc @ ${revision:0:12}"
    git init -q "$dest"
    git -C "$dest" remote add origin "$url"
    git -C "$dest" fetch -q --depth 1 origin "$revision"
    git -C "$dest" checkout -q --detach FETCH_HEAD
    local actual
    actual="$(git -C "$dest" rev-parse HEAD)"
    if [ "$actual" != "$revision" ]; then
      echo "  [error] $desc 修訂不符：$actual" >&2
      rm -rf "$dest"
      exit 1
    fi
    printf '%s\n' "$revision" > "$dest/.source-revision"
    rm -rf "$dest/.git"
  fi
}

download_verified() {
  local url="$1"
  local dest="$2"
  local sha256="$3"
  local desc="$4"
  if [ -f "$dest" ] && printf '%s  %s\n' "$sha256" "$dest" | sha256sum -c - >/dev/null 2>&1; then
    echo "  [skip] $desc（已驗證）"
    return
  fi
  local temp="${dest}.download"
  echo "  [download] $desc"
  curl -fsSL "$url" -o "$temp"
  if ! printf '%s  %s\n' "$sha256" "$temp" | sha256sum -c - >/dev/null; then
    rm -f "$temp"
    echo "  [error] $desc SHA-256 驗證失敗" >&2
    exit 1
  fi
  mv -f "$temp" "$dest"
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
  "ChhoeTaigi/ChhoeTaigiDatabase" \
  "b33c6a1fcc2d11a2962e76b6055d528d11677c3b"

echo ""
echo "=== 2/20 glll4678/rime-taigi ==="
echo "  現有 Rime 台語方案，參考 schema 結構和方言碼（EI/EE/OO）"
clone_and_degit \
  "https://github.com/glll4678/rime-taigi.git" \
  "$DATA_DIR/rime-taigi-glll4678" \
  "glll4678/rime-taigi" \
  "28d03225e97ac24924f24b8f1293eb341ecafb83"

echo ""
echo "=== 3/20 ryanwuson/rime-liur ==="
echo "  蝦米 Rime 方案，參考 Lua 模組架構（查碼、造詞、符號、日期）"
clone_and_degit \
  "https://github.com/ryanwuson/rime-liur.git" \
  "$DATA_DIR/rime-liur" \
  "ryanwuson/rime-liur" \
  "01da8ecdc5cfb64bdba2526d6e75ee1483615e94"

echo ""
echo "=== 4/20 YuRen-tw/rime-taigi-tps ==="
echo "  方音符號台語方案，參考字典格式和方音鍵盤配置"
clone_and_degit \
  "https://github.com/YuRen-tw/rime-taigi-tps.git" \
  "$DATA_DIR/rime-taigi-tps" \
  "YuRen-tw/rime-taigi-tps" \
  "ffa76b465ef2f4442622c38189b63653ff438de3"

echo ""
echo "=== 5/20 ButTaiwan/taigivs ==="
echo "  字咍台語字型，IVS 對照表（Phase 2 用）"
clone_and_degit \
  "https://github.com/ButTaiwan/taigivs.git" \
  "$DATA_DIR/taigivs" \
  "ButTaiwan/taigivs" \
  "a2114806be61fc003ce56fcd9663141f8b3e2a24"

echo ""
echo "=== 6/20 Taiwanese-Corpus/hue7jip8 ==="
echo "  台語/族語/客語語料清單彙整，含楊允言詞頻研究路徑"
clone_and_degit \
  "https://github.com/Taiwanese-Corpus/hue7jip8.git" \
  "$DATA_DIR/Taiwanese-Corpus-hue7jip8" \
  "Taiwanese-Corpus/hue7jip8" \
  "64ff872e11ce36c3721889f59de92b694735400c"


echo ""
echo "=== 7/20 i3thuan5/khin1siann1-hun1sik4 ==="
echo "  輕聲分析器，含詞頻書寫規範（分詞邏輯參考）"
clone_and_degit \
  "https://github.com/i3thuan5/khin1siann1-hun1sik4.git" \
  "$DATA_DIR/khin1siann1-hun1sik4" \
  "i3thuan5/khin1siann1-hun1sik4" \
  "308fe8aa43ed7ff1d71e4a0c72079a742aad67b4"

echo ""
echo "=== 8/20 LKK 用字表（Google Sheets CSV 下載）==="
echo "  李江却台語文教基金會漢羅用字規範"
LKK_BASE_URL="https://docs.google.com/spreadsheets/d/e/2PACX-1vR6sABIf13wvn95hKApMWmEYYD-vDL62mVAYBE1jycBRTkiJQush3-HCkkaPMSsv2cOcPZ0blNODFpx/pub"
download_verified \
  "${LKK_BASE_URL}?gid=1364822222&single=true&output=csv" \
  "$DATA_DIR/lkk_yongji.csv" \
  "6a00b025984c57ff53ae78801157a79a3a91c72cbd75b4136f835b819c3707bb" \
  "LKK 字表 CSV（gid=1364822222）"
download_verified \
  "${LKK_BASE_URL}?gid=1982799732&single=true&output=csv" \
  "$DATA_DIR/lkk_suji.csv" \
  "50bf19cc3a7c83ec5e291caf951fc4c736131200e8c45d3455611f539533d035" \
  "LKK 數字用法 CSV（gid=1982799732）"
# 同時保留原始 HTML（若專案根目錄有的話）
PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LKK_HTML="$(ls "$PROJ_DIR"/LKK*.html 2>/dev/null | head -1)"
if [ -n "$LKK_HTML" ] && [ ! -f "$DATA_DIR/lkk_yongji.html" ]; then
  cp "$LKK_HTML" "$DATA_DIR/lkk_yongji.html"
  echo "  [copy] 原始 HTML → data/lkk_yongji.html"
fi

echo ""
echo "=== 9b/21 教育部推薦700字台語漢字 ==="
echo "  教育部公告700字台語漢字推薦用字表"
MINNAN_700_REVISION="ac77ef59fdf5d0c74eba39a385f67e27ca8742a4"
download_verified \
  "https://raw.githubusercontent.com/yiufung/minnan-700/$MINNAN_700_REVISION/700iongji.csv" \
  "$DATA_DIR/700iongji.csv" \
  "ceef5716a02e7f043e6cbf9423c96f52a48d3266e1b6eabefabdcf8bf2f0f316" \
  "教育部700字 CSV"

echo ""
echo "=== 9/20 Taiwanese-Corpus/Ungian_2009_KIPsupin ==="
echo "  楊允言詞頻資料（教育部臺灣閩南語字詞頻調查）"
clone_and_degit \
  "https://github.com/Taiwanese-Corpus/Ungian_2009_KIPsupin.git" \
  "$DATA_DIR/Ungian_2009_KIPsupin" \
  "Taiwanese-Corpus/Ungian_2009_KIPsupin" \
  "9dc2c0bc516e731ff2ed7ee56f04b0dcf12bcac3"

echo ""
echo "=== 10/20 i3thuan5/tai5-uan5_gian5-gi2_kang1-ku7 ==="
echo "  意傳臺灣言語工具（音標轉換用，含原始碼及 Python 套件）"
clone_and_degit \
  "https://github.com/i3thuan5/tai5-uan5_gian5-gi2_kang1-ku7.git" \
  "$DATA_DIR/tai5-uan5_gian5-gi2_kang1-ku7" \
  "i3thuan5/tai5-uan5_gian5-gi2_kang1-ku7" \
  "69716fafb5cacbc2c2b6f3ac4b6931a8a6ed95b6"

echo ""
echo "=== 11/20 ChhoeTaigi/KipSutianDataMirror ==="
echo "  教育部台語辭典鏡像（ODS + 音檔）"
echo "  授權：CC BY-ND 3.0 Taiwan"
clone_and_degit \
  "https://github.com/ChhoeTaigi/KipSutianDataMirror.git" \
  "$DATA_DIR/KipSutianDataMirror" \
  "ChhoeTaigi/KipSutianDataMirror" \
  "936db276e153886e537aaf425dbdafbc1961faaa"

echo ""
echo "=== 12/20 i3thuan5/KeSi ==="
echo "  POJ↔TL 轉換 Python 工具，比 tai5-uan5 更輕量"
echo "  授權：MIT"
clone_and_degit \
  "https://github.com/i3thuan5/KeSi.git" \
  "$DATA_DIR/KeSi" \
  "i3thuan5/KeSi" \
  "b70d0e411eb1ef9f38c89f6f5291f9c7e0c442fb"

echo ""
echo "=== 13/20 Taiwanese-Corpus/icorpus_ka1_han3-ji7 ==="
echo "  iCorpus 臺華平行新聞語料庫（2008-2014），可算真實詞頻"
clone_and_degit \
  "https://github.com/Taiwanese-Corpus/icorpus_ka1_han3-ji7.git" \
  "$DATA_DIR/icorpus_ka1_han3-ji7" \
  "Taiwanese-Corpus/icorpus_ka1_han3-ji7" \
  "f49537f2f446e9c6c024634d8b95dab89b8dab44"

echo ""
echo "=== 14/20 Taiwanese-Corpus/nmtl_2006_dadwt ==="
echo "  台語漢羅及全羅文學作品 2,169 篇，漢羅書寫慣例黃金參考"
clone_and_degit \
  "https://github.com/Taiwanese-Corpus/nmtl_2006_dadwt.git" \
  "$DATA_DIR/nmtl_2006_dadwt" \
  "Taiwanese-Corpus/nmtl_2006_dadwt" \
  "3afb6a805439546b571fec30452b78e06a942277"

echo ""
echo "=== 15/20 Taiwanese-Corpus/moe_minkalaok ==="
echo "  閩南語卡拉OK正字字表，教育部用字規範參考"
clone_and_degit \
  "https://github.com/Taiwanese-Corpus/moe_minkalaok.git" \
  "$DATA_DIR/moe_minkalaok" \
  "Taiwanese-Corpus/moe_minkalaok" \
  "f4af9c9e3caa278a2d9adfe8f5b0a1f217faa2a5"

echo ""
echo "=== 16/20 Taiwanese-Corpus/Khin-hoan_2010_pojbh ==="
echo "  白話字文獻館（歷史 POJ 語料，台灣師範大學 2007-2010）"
clone_and_degit \
  "https://github.com/Taiwanese-Corpus/Khin-hoan_2010_pojbh.git" \
  "$DATA_DIR/Khin-hoan_2010_pojbh" \
  "Taiwanese-Corpus/Khin-hoan_2010_pojbh" \
  "097a75437a0a150efb25b8790c09bad3c1fa7aee"

echo ""
echo "=== 17/20 ChhoeTaigi/Kam-Ui-lim_1913_Kam-Ji-tian ==="
echo "  甘字典 CSV 原始版（1913 年甘為霖台語辭典）"
echo "  授權：CC BY-NC-SA"
clone_and_degit \
  "https://github.com/ChhoeTaigi/Kam-Ui-lim_1913_Kam-Ji-tian.git" \
  "$DATA_DIR/Kam-Ui-lim_1913_Kam-Ji-tian" \
  "ChhoeTaigi/Kam-Ui-lim_1913_Kam-Ji-tian" \
  "b0b40fcb98972bcf1cc0947d3e6702843ccb00bb"

echo ""
echo "=== 18/20 Taiwanese-Corpus/kok4hau7-kho3pun2 ==="
echo "  國小台語課本（康軒版），12冊漢字+台羅對照"
clone_and_degit \
  "https://github.com/Taiwanese-Corpus/kok4hau7-kho3pun2.git" \
  "$DATA_DIR/kok4hau7-kho3pun2" \
  "Taiwanese-Corpus/kok4hau7-kho3pun2" \
  "08ee4252bf4b177c4ac297c7bfa0e20bd1ffecd0"

echo ""
echo "=== 19/20 Taiwanese-Corpus/Sin1pak8tshi7_2015_900-le7ku3 ==="
echo "  常用900例句（詞條漢字+台羅+例句），日常高頻詞彙"
clone_and_degit \
  "https://github.com/Taiwanese-Corpus/Sin1pak8tshi7_2015_900-le7ku3.git" \
  "$DATA_DIR/Sin1pak8tshi7_2015_900-le7ku3" \
  "Taiwanese-Corpus/Sin1pak8tshi7_2015_900-le7ku3" \
  "55391016e3805f637902ce83dc9767e9744e7448"

echo ""
echo "=== 20/20 luke871016/Taigi-Input-method-dictionary-supplement ==="
echo "  建中的教育部臺灣台語輸入法詞庫增補檔案，作為人工增補字詞來源"
clone_and_degit \
  "https://github.com/luke871016/Taigi-Input-method-dictionary-supplement.git" \
  "$DATA_DIR/Taigi-Input-method-dictionary-supplement" \
  "luke871016/Taigi-Input-method-dictionary-supplement" \
  "ada348a5fca5a6ee7932fcc24b9ccba0a6ea814e"

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
