#!/usr/bin/env bash
# 拍台文 Phah Tai-bun 自動安裝工具 (macOS / 鼠鬚管 Squirrel)
# 從 bundle installer 呼叫時：bash install_macos.sh --project-root /path/to/staged/files

set -euo pipefail

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

RELEASE_VERSION="0.9.3"
GITHUB_REPO="soanseng/rime-phah-taibun"
_TEMP_SOURCE_DIR=""

cleanup() {
    if [ -n "$_TEMP_SOURCE_DIR" ] && [ -d "$_TEMP_SOURCE_DIR" ]; then
        rm -rf "$_TEMP_SOURCE_DIR"
    fi
}
trap cleanup EXIT

# 解析參數：--project-root 覆蓋預設的專案根目錄
_PROJ_ROOT_OVERRIDE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --project-root)
            _PROJ_ROOT_OVERRIDE="$2"
            shift 2
            ;;
        --project-root=*)
            _PROJ_ROOT_OVERRIDE="${1#*=}"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# 專案根目錄：
# 1. 套件安裝器以 --project-root 指向內含的 payload。
# 2. 本機 clone 直接使用腳本上層目錄。
# 3. curl | bash 沒有同目錄資產時，從固定 release tag 逐檔下載到暫存目錄。
if [ -n "$_PROJ_ROOT_OVERRIDE" ]; then
    if [ ! -d "$_PROJ_ROOT_OVERRIDE" ]; then
        echo "錯誤：--project-root 不存在：$_PROJ_ROOT_OVERRIDE" >&2
        exit 1
    fi
    PROJ_DIR="$(cd "$_PROJ_ROOT_OVERRIDE" && pwd)"
else
    SCRIPT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    if [ -d "$SCRIPT_ROOT/schema" ] && [ -d "$SCRIPT_ROOT/lua" ]; then
        PROJ_DIR="$SCRIPT_ROOT"
    else
        command -v curl >/dev/null 2>&1 || {
            echo "錯誤：指令安裝需要 curl。" >&2
            exit 1
        }
        command -v shasum >/dev/null 2>&1 || {
            echo "錯誤：指令安裝需要 shasum。" >&2
            exit 1
        }
        : "${TMPDIR:=/tmp}"
        _TEMP_SOURCE_DIR="$(mktemp -d "${TMPDIR%/}/phah-taibun.XXXXXX")"
        # 自動跟隨 GitHub 最新 release（查詢失敗就退回上方固定版本），
        # 之後從固定 tag 逐檔下載，不抓整份來源封存檔：release 資產經
        # objects.githubusercontent.com 轉址，部分網路對它極慢或逾時。
        latest_tag="$(curl -fsSL --connect-timeout 10 --max-time 15 "https://api.github.com/repos/$GITHUB_REPO/releases/latest" 2>/dev/null | sed -n 's/.*"tag_name": *"\(v[0-9][0-9.]*\)".*/\1/p' | head -1)"
        case "$latest_tag" in
            v[0-9]*) RELEASE_VERSION="${latest_tag#v}" ;;
        esac
        tree_json="$_TEMP_SOURCE_DIR/tree.json"
        curl -fsSL --connect-timeout 10 --max-time 30 "https://api.github.com/repos/$GITHUB_REPO/git/trees/v$RELEASE_VERSION?recursive=1" -o "$tree_json" \
            || { echo "錯誤：取得檔案清單失敗。" >&2; exit 1; }
        # 從 tree JSON 取出（路徑, 大小）；清單遭截斷時整批拒絕，避免裝出半套。
        files_tsv="$_TEMP_SOURCE_DIR/files.tsv"
        awk '
            /"truncated": *true/ { bad = 1 }
            /"path":/ { p = $0; sub(/.*"path": "/, "", p); sub(/".*/, "", p) }
            /"type":/ { t = $0; sub(/.*"type": "/, "", t); sub(/".*/, "", t) }
            /"size":/ {
                s = $0; sub(/.*"size": /, "", s); sub(/,.*/, "", s)
                if (t == "blob" && (p == "rime.lua" || p ~ /^lua\/phah_taibun_.*\.lua$/ || p ~ /^schema\//))
                    print p "\t" s
                p = ""; t = ""; s = ""
            }
            END { if (bad) exit 1 }
        ' "$tree_json" > "$files_tsv" || { echo "錯誤：檔案清單不完整。" >&2; exit 1; }
        echo "正在從 GitHub v$RELEASE_VERSION 逐檔下載拍台文..."
        PROJ_DIR="$_TEMP_SOURCE_DIR/source"
        mkdir -p "$PROJ_DIR"
        while IFS=$'\t' read -r rel size; do
            dest="$PROJ_DIR/$rel"
            mkdir -p "$(dirname "$dest")"
            echo "  下載 $rel"
            curl -fsSL --retry 3 --connect-timeout 10 --max-time 300 "https://raw.githubusercontent.com/$GITHUB_REPO/v$RELEASE_VERSION/$rel" -o "$dest" \
                || { echo "錯誤：下載 $rel 失敗。" >&2; exit 1; }
            actual_size="$(wc -c < "$dest" | tr -d ' ')"
            if [ "$actual_size" != "$size" ]; then
                echo "錯誤：$rel 大小不符（預期 $size，實得 $actual_size）。" >&2
                exit 1
            fi
        done < "$files_tsv"
    fi
fi

if [ ! -d "$PROJ_DIR/schema" ] || [ ! -d "$PROJ_DIR/lua" ] || [ ! -f "$PROJ_DIR/rime.lua" ]; then
    echo "錯誤：安裝來源不完整：$PROJ_DIR" >&2
    exit 1
fi

# ============================================================
# 鼠鬚管路徑定義
# ============================================================
SQUIRREL_APP="/Library/Input Methods/Squirrel.app"
SQUIRREL_SHARED="$SQUIRREL_APP/Contents/SharedSupport"
RIME_DIR="${RIME_DIR:-$HOME/Library/Rime}"
FONT_DIR="$HOME/Library/Fonts"

# ============================================================
# 標題
# ============================================================
echo
echo "======================================"
echo "  拍台文 Phah Tai-bun 自動安裝工具"
echo "  (macOS / 鼠鬚管 Squirrel)"
echo "======================================"
echo

# ============================================================
# Step 0: 偵測環境
# ============================================================
if [ ! -d "$SQUIRREL_APP" ]; then
    echo -e "${RED}錯誤：找不到鼠鬚管（Squirrel）！${NC}"
    echo
    echo "請先安裝鼠鬚管："
    echo
    echo "  Homebrew："
    echo "    brew install --cask squirrel"
    echo
    echo "  手動下載："
    echo "    https://rime.im/download/"
    echo
    exit 1
fi

echo -e "偵測到 Rime 框架：${GREEN}鼠鬚管 Squirrel${NC}"
echo -e "Rime 資料夾：${GREEN}${RIME_DIR}${NC}"
echo

echo "本工具將執行以下作業："
echo "  1. 複製方案檔（schema/*.yaml）到 Rime 資料夾"
echo "  2. 複製 Lua 腳本（lua/*.lua + rime.lua）到 Rime 資料夾"
echo "  3. 安裝芫荽 iansui 字體"
echo "  4. 部署 RIME（自動重新編譯）"
echo
echo -e "${YELLOW}※ 若有自訂設定尚未備份，請按 Ctrl+C 終止${NC}"
echo

# ============================================================
# 進階功能（與 install_windows.ps1 對齊）：安裝選單、時間戳備份、
# 方案註冊、default.custom.yaml 正規化、嘸蝦米（rime-liur）安裝。
# 本段同時內嵌於 install_linux.sh 與 install_macos.sh——修改請兩邊同步。
# ============================================================
INSTALLER_IS_INTERACTIVE=false
[ -t 0 ] && INSTALLER_IS_INTERACTIVE=true

INSTALL_PHAH=true
INSTALL_LIUR=false

installer_ask_what_to_install() {
    local schemas="${PHAH_TAIBUN_SCHEMAS:-}"
    if [ -z "$schemas" ]; then
        if [ "$INSTALLER_IS_INTERACTIVE" = true ]; then
            echo "請選擇要安裝的輸入方案："
            echo "  1. 拍台文（台語）"
            echo "  2. 嘸蝦米（rime-liur）"
            echo "  3. 拍台文 + 嘸蝦米（預設）"
            printf '請輸入選項 (1/2/3，Enter=3)：'
            local choice=""
            read -r choice || true
            case "$choice" in
                1) schemas="phah" ;;
                2) schemas="liur" ;;
                *) schemas="both" ;;
            esac
        else
            schemas="phah"
        fi
    fi
    case "$schemas" in
        phah) INSTALL_PHAH=true; INSTALL_LIUR=false ;;
        liur) INSTALL_PHAH=false; INSTALL_LIUR=true ;;
        both) INSTALL_PHAH=true; INSTALL_LIUR=true ;;
        *)
            echo "錯誤：PHAH_TAIBUN_SCHEMAS 必須是 phah、liur 或 both（目前：$schemas）" >&2
            exit 1
            ;;
    esac
    echo
}

# 變動任何設定前，先做時間戳備份（不覆蓋先前的備份檔）
installer_backup_default_custom() {
    [ -f "$RIME_DIR/default.custom.yaml" ] || return 0
    local stamp
    stamp="$(date +%Y%m%d-%H%M%S)"
    cp -f "$RIME_DIR/default.custom.yaml" "$RIME_DIR/default.custom.yaml.backup-$stamp"
    echo -e "  ${YELLOW}[備份]${NC} default.custom.yaml → default.custom.yaml.backup-$stamp"
}

# 取得未占用的 schema_list/@next 編號後綴（"" 或 " 1"、" 2"…）
installer_free_next_suffix() {
    local dc="$1" idx=1 suffix=""
    while :; do
        if grep -Eq "^[[:space:]]*schema_list/@next${suffix}:[[:space:]]*$" "$dc" 2>/dev/null; then
            suffix=" $idx"
            idx=$((idx + 1))
        else
            printf '%s' "$suffix"
            return
        fi
    done
}

# 追加單一方案（已存在就跳過）；支援 - schema: 列表、__patch: 列表、@next 形式；
# 檔案是空的或只有註解時，先補 patch: 錨點，避免追加落在結構外。
installer_register_schema() {
    local id="$1"
    local dc="$RIME_DIR/default.custom.yaml"
    [ -f "$dc" ] || return 0
    grep -Eq "schema:[[:space:]]*${id}[[:space:]]*\$" "$dc" && return 0
    if grep -q '^[[:space:]]*- schema:' "$dc"; then
        local tmp
        tmp="$(mktemp)"
        awk -v id="$id" '
            { lines[NR] = $0 }
            END {
                last = 0
                for (i = 1; i <= NR; i++) if (lines[i] ~ /^[[:space:]]*- schema:/) last = i
                for (i = 1; i <= NR; i++) {
                    print lines[i]
                    if (i == last) {
                        indent = lines[i]; sub(/- schema:.*/, "", indent)
                        print indent "- schema: " id
                    }
                }
            }' "$dc" > "$tmp" && mv -f "$tmp" "$dc"
        return
    fi
    if ! grep -q '^__patch:' "$dc"; then
        if ! grep -q '^patch:[[:space:]]*\$' "$dc"; then
            if [ -s "$dc" ] && [ -n "$(tr -d '[:space:]#' < "$dc")" ]; then
                printf '\npatch:\n' >> "$dc"
            else
                printf 'patch:\n' > "$dc"
            fi
        fi
    fi
    local suffix
    suffix="$(installer_free_next_suffix "$dc")"
    if grep -q '^__patch:' "$dc"; then
        printf '  - patch/+:\n      schema_list/@next%s:\n        schema: %s\n' "$suffix" "$id" >> "$dc"
    else
        printf '  schema_list/@next%s:\n    schema: %s\n' "$suffix" "$id" >> "$dc"
    fi
}

# 列出已註冊方案 id（- schema: 與 @next 兩種形式，依出現順序去重）
installer_schema_ids() {
    local dc="$RIME_DIR/default.custom.yaml"
    [ -f "$dc" ] || return 0
    awk '
        function grab(line, dash) {
            if (dash) sub(/^[[:space:]]*- schema:[[:space:]]*/, "", line)
            else sub(/^[[:space:]]*schema:[[:space:]]*/, "", line)
            sub(/[[:space:]]+$/, "", line)
            if (!(line in seen)) { seen[line] = 1; order[++n] = line }
        }
        /^[[:space:]]*- schema:[[:space:]]*[^[:space:]]+[[:space:]]*$/ { grab($0, 1); nextok = 0; next }
        /^[[:space:]]*schema_list\/@next([[:space:]]+[0-9]+)?[[:space:]]*:[[:space:]]*$/ { nextok = 1; next }
        nextok && /^[[:space:]]+schema:[[:space:]]*[^[:space:]]+[[:space:]]*$/ { grab($0, 0); nextok = 0; next }
        { nextok = 0 }
        END { for (i = 1; i <= n; i++) print order[i] }
    ' "$dc"
}

# 互動：列出方案清單，讓使用者挑要保留哪些（Enter=全部保留）；
# 剛安裝的方案（拍台文／嘸蝦米）受保護，不會被剪掉。
installer_keep_which_prompt() {
    [ "$INSTALLER_IS_INTERACTIVE" = true ] || return 0
    local dc="$RIME_DIR/default.custom.yaml"
    [ -f "$dc" ] || return 0
    local ids
    ids="$(installer_schema_ids)"
    [ -n "$ids" ] || return 0
    local -a current=()
    while IFS= read -r line; do current+=("$line"); done <<< "$ids"
    echo "目前 default.custom.yaml 的方案清單："
    local i=1
    for id in "${current[@]}"; do
        echo "  $i. $id"
        i=$((i + 1))
    done
    printf '要保留哪些？（Enter=全部保留，或輸入編號如 1,3）：'
    local answer=""
    read -r answer || true
    if [ -z "$answer" ]; then
        echo -e "  ${GREEN}保留全部既有方案${NC}"
        return 0
    fi
    answer="${answer//[，,]/ }"
    local -a keep=()
    local tok
    for tok in $answer; do
        case "$tok" in
            ''|*[!0-9]*) ;;
            *)
                if [ "$tok" -ge 1 ] && [ "$tok" -le "${#current[@]}" ]; then
                    keep+=("${current[$((tok - 1))]}")
                fi
                ;;
        esac
    done
    installer_list_contains() {
        local needle="$1" item
        shift
        for item in "$@"; do [ "$item" = "$needle" ] && return 0; done
        return 1
    }
    local -a drop=()
    for id in "${current[@]}"; do
        if installer_list_contains "$id" ${keep[@]+"${keep[@]}"}; then
            continue
        fi
        case "$id" in
            phah_taibun|phah_taibun_telex) if [ "$INSTALL_PHAH" = true ]; then continue; fi ;;
            liur) if [ "$INSTALL_LIUR" = true ]; then continue; fi ;;
        esac
        drop+=("$id")
    done
    if [ ${#drop[@]} -eq 0 ]; then
        echo -e "  ${GREEN}保留全部既有方案${NC}"
        return 0
    fi
    local tmp
    tmp="$(mktemp)"
    local drops
    drops="$(printf '%s\n' "${drop[@]}")"
    awk -v drops="$drops" '
        BEGIN { n = split(drops, d, "\n"); for (i = 1; i <= n; i++) drop[d[i]] = 1 }
        {
            if (nextok) {
                nextok = 0
                id = $0; sub(/^[[:space:]]*schema:[[:space:]]*/, "", id); sub(/[[:space:]]+$/, "", id)
                if (id in drop) next
                print pend; print; next
            }
            if ($0 ~ /^[[:space:]]*- schema:[[:space:]]*[^[:space:]]+[[:space:]]*$/) {
                id = $0; sub(/^[[:space:]]*- schema:[[:space:]]*/, "", id); sub(/[[:space:]]+$/, "", id)
                if (id in drop) next
                print; next
            }
            if ($0 ~ /^[[:space:]]*schema_list\/@next([[:space:]]+[0-9]+)?[[:space:]]*:[[:space:]]*$/) {
                nextok = 1; pend = $0; next
            }
            print
        }' "$dc" > "$tmp" && mv -f "$tmp" "$dc"
    echo -e "  ${YELLOW}已移除未選擇的方案：${drop[*]}${NC}"
}

# 互動：注音（bopomofo）預設保留
installer_bopomofo_prompt() {
    [ "$INSTALLER_IS_INTERACTIVE" = true ] || return 0
    local dc="$RIME_DIR/default.custom.yaml"
    [ -f "$dc" ] || return 0
    grep -Eq 'schema:[[:space:]]*bopomofo[[:space:]]*\$' "$dc" && return 0
    printf '要保留注音輸入法（bopomofo）嗎？(Y/n)：'
    local answer=""
    read -r answer || true
    case "$answer" in
        n|N) return 0 ;;
        *)
            installer_register_schema bopomofo
            echo -e "  ${GREEN}已將 bopomofo（注音）加入方案清單${NC}"
            ;;
    esac
}

# 把 default.custom.yaml 整理成乾淨排版＋說明註解（冪等）；
# 回傳 0＝已重寫；1＝維持原樣（__patch: 複合格式或非 patch: 檔）。
installer_normalize_default_custom() {
    local dc="$RIME_DIR/default.custom.yaml"
    [ -f "$dc" ] || return 1
    local tmp
    tmp="$(mktemp)"
    if awk '
        function emit(s) { out = out s "\n" }
        function grab(line, dash) {
            if (dash) sub(/^[[:space:]]*- schema:[[:space:]]*/, "", line)
            else sub(/^[[:space:]]*schema:[[:space:]]*/, "", line)
            sub(/[[:space:]]+$/, "", line)
            if (!(line in seen)) { seen[line] = 1; IDS[++n] = line }
        }
        { L[NR] = $0 }
        END {
            bs = 0
            for (i = 1; i <= NR; i++) if (L[i] !~ /^[[:space:]]*(#|$)/) { bs = i; break }
            if (bs == 0 || L[bs] !~ /^patch:[[:space:]]*$/) exit 1
            nextok = 0
            for (i = 1; i <= NR; i++) {
                if (L[i] ~ /^[[:space:]]*- schema:[[:space:]]*[^[:space:]]+[[:space:]]*$/) { grab(L[i], 1); nextok = 0 }
                else if (L[i] ~ /^[[:space:]]*schema_list\/@next([[:space:]]+[0-9]+)?[[:space:]]*:[[:space:]]*$/) { nextok = 1 }
                else if (nextok && L[i] ~ /^[[:space:]]+schema:[[:space:]]*[^[:space:]]+[[:space:]]*$/) { grab(L[i], 0); nextok = 0 }
                else nextok = 0
                if (L[i] ~ /switcher\/save_options/) hasopt = 1
                if (L[i] ~ /^[[:space:]]*- schema:/) dash = 1
            }
            emit("# default.custom.yaml — 拍台文安裝工具維護")
            emit("#")
            emit("# 安裝工具只會「追加」設定，不會覆蓋內建方案與你的其他設定；")
            emit("# 原始內容在每次安裝前都會備份成 default.custom.yaml.backup-<時間戳>。")
            emit("#")
            emit("# schema_list：可用的輸入方案，順序＝F4 選單順序。")
            if (hasopt) emit("# switcher/save_options：記住 F4 選過的模式，重新部署或重開機不用重選。")
            emit("")
            emit("patch:")
            if (hasopt) {
                emit("  # 記住 F4 的模式選擇")
                emit("  switcher/save_options/@before 0: poj_mode")
                emit("  switcher/save_options/@next: full_romanization")
            }
            if (n > 0) {
                if (dash) {
                    emit("  # 輸入方案清單（明確列表：以此為準，內建方案不會出現在 F4）；要增刪方案就增減下面幾行。")
                    emit("  schema_list:")
                    for (i = 1; i <= n; i++) emit("    - schema: " IDS[i])
                } else {
                    emit("  # 以下方案以 @next 附加在內建清單之後（內建注音、倉頡等仍可用）；新增方案建議重跑安裝工具。")
                    emit("  schema_list/@next:")
                    emit("    schema: " IDS[1])
                    for (i = 2; i <= n; i++) { emit("  schema_list/@next " (i - 1) ":"); emit("    schema: " IDS[i]) }
                }
            }
            seenPatch = 0; leading = 1; nextok = 0
            for (i = 1; i <= NR; i++) {
                line = L[i]
                if (leading) {
                    if (line ~ /^[[:space:]]*(#|$)/) continue
                    leading = 0
                }
                if (!seenPatch) {
                    if (line ~ /^patch:[[:space:]]*$/) seenPatch = 1
                    continue
                }
                if (index(line, "  # 記住 F4 的模式選擇") == 1) continue
                if (index(line, "  # 輸入方案清單（明確列表") == 1) continue
                if (index(line, "  # 以下方案以 @next") == 1) continue
                if (line ~ /^[[:space:]]*- schema:[[:space:]]*[^[:space:]]+[[:space:]]*$/) continue
                if (dash && line ~ /^[[:space:]]*schema_list:[[:space:]]*$/) continue
                if (line ~ /^[[:space:]]*schema_list\/@next([[:space:]]+[0-9]+)?[[:space:]]*:[[:space:]]*$/) {
                    nextok = 1; continue
                }
                if (nextok && line ~ /^[[:space:]]+schema:[[:space:]]*[^[:space:]]+[[:space:]]*$/) { nextok = 0; continue }
                nextok = 0
                if (line ~ /switcher\/save_options/) continue
                emit(line)
            }
            printf "%s", out
        }' "$dc" > "$tmp"; then
        mv -f "$tmp" "$dc"
        return 0
    fi
    rm -f "$tmp"
    return 1
}

# 下載 URL 到 dest；本地已存在且大小與遠端相同（HEAD content-length）就跳過。
installer_fetch_if_changed() {
    local url="$1" dest="$2" label="$3"
    if [ -f "$dest" ]; then
        local remote_size=""
        remote_size="$(curl -sIL --connect-timeout 10 --max-time 20 "$url" 2>/dev/null | tr -d '\r' \
            | awk 'tolower($1) == "content-length:" { v = $2 } END { print v }')"
        if [ -n "$remote_size" ] && [ "$remote_size" = "$(wc -c < "$dest" | tr -d ' ')" ]; then
            echo -e "  ${GREEN}[已安裝]${NC} $label"
            return 0
        fi
    fi
    mkdir -p "$(dirname "$dest")"
    if curl -fsSL --connect-timeout 10 --max-time 120 "$url" -o "$dest"; then
        echo -e "  ${GREEN}[ok]${NC} $label"
    else
        echo -e "  ${YELLOW}[失敗]${NC} $label"
        return 1
    fi
}

# 安裝嘸蝦米（rime-liur-arch）：清單來自 GitHub tree API（curl+python3）、
# 已存在且大小相同跳過、自訂檔保留、rime.lua 以 marker 整份合併、字體已存在跳過。
installer_install_liur() {
    echo
    echo "[ 嘸蝦米（rime-liur） ]"
    echo
    local version="mixed"
    if [ "$INSTALLER_IS_INTERACTIVE" = true ]; then
        echo "請選擇嘸蝦米版本："
        echo "  1. 完整版（中打含英文詞庫版）（推薦）"
        echo "  2. 基礎版（中打不含英文詞庫）"
        printf '請輸入選項 (1 或 2，Enter=1)：'
        local c=""
        read -r c || true
        [ "$c" = "2" ] && version="chinese-only"
        echo
    fi
    command -v curl >/dev/null 2>&1 || { echo -e "${YELLOW}嘸蝦米安裝失敗：需要 curl${NC}"; return 1; }
    command -v python3 >/dev/null 2>&1 || { echo -e "${YELLOW}嘸蝦米安裝失敗：需要 python3（解析檔案清單）${NC}"; return 1; }
    local repo="soanseng/rime-liur-arch"
    local base="https://raw.githubusercontent.com/$repo/main"
    local api="https://api.github.com/repos/$repo/git/trees/main?recursive=1"
    echo "正在從 GitHub 取得嘸蝦米檔案清單（$repo）..."
    local all
    all="$(curl -fsSL --connect-timeout 10 --max-time 30 "$api" 2>/dev/null | python3 -c '
import sys, json
try:
    for item in json.load(sys.stdin).get("tree", []):
        if item.get("type") == "blob":
            print(item["path"])
except Exception:
    pass' 2>/dev/null)"
    if [ -z "$all" ]; then
        echo -e "${YELLOW}嘸蝦米安裝失敗：無法取得檔案清單${NC}"
        return 1
    fi
    local -a root=() lua=() opencc=() configs=() fonts=()
    local p
    while IFS= read -r p; do
        [ -n "$p" ] || continue
        case "$p" in
            docs/*|README.md|LICENSE|.gitignore|rime_liur_installer.sh|rime_liur_installer.ps1|rime_liur_installer_linux.sh) continue ;;
        esac
        case "$p" in
            lua/*) lua+=("$p") ;;
            opencc/*) opencc+=("$p") ;;
            configs/*) configs+=("$p") ;;
            fonts/*) fonts+=("$p") ;;
            rime.lua) ;;
            */*) ;;
            *) root+=("$p") ;;
        esac
    done <<< "$all"
    local total=$(( ${#root[@]} + ${#lua[@]} + ${#opencc[@]} + ${#configs[@]} + 1 ))
    echo "找到 $total 個方案檔案、${#fonts[@]} 個字體"
    # 自訂檔一律保留
    local -a custom=(openxiami_CustomWord.dict.yaml default.custom.yaml weasel.custom.yaml squirrel.custom.yaml)
    local f rel dest is_custom
    for p in "${root[@]}"; do
        is_custom=false
        for f in "${custom[@]}"; do [ "$f" = "$p" ] && is_custom=true; done
        if [ "$is_custom" = true ] && [ -f "$RIME_DIR/$p" ]; then
            echo -e "  ${GREEN}[保留]${NC} $p"
        else
            installer_fetch_if_changed "$base/$p" "$RIME_DIR/$p" "$p"
        fi
    done
    for p in "${lua[@]}"; do
        rel="${p#lua/}"
        installer_fetch_if_changed "$base/$p" "$RIME_DIR/lua/$rel" "lua/$rel"
    done
    for p in "${opencc[@]}"; do
        installer_fetch_if_changed "$base/$p" "$RIME_DIR/opencc/${p#opencc/}" "opencc/${p#opencc/}"
    done
    for p in "${configs[@]}"; do
        mkdir -p "$RIME_DIR/configs"
        curl -fsSL --connect-timeout 10 --max-time 60 "$base/$p" -o "$RIME_DIR/configs/${p#configs/}" \
            || { echo -e "${YELLOW}[失敗]${NC} $p"; }
    done
    # rime.lua：marker 整份合併
    local liur_rime_lua
    liur_rime_lua="$(mktemp)"
    curl -fsSL --connect-timeout 10 --max-time 60 "$base/rime.lua" -o "$liur_rime_lua" || { rm -f "$liur_rime_lua"; echo -e "${YELLOW}[失敗]${NC} rime.lua"; }
    if [ -s "$liur_rime_lua" ]; then
        if [ ! -f "$RIME_DIR/rime.lua" ]; then
            cp -f "$liur_rime_lua" "$RIME_DIR/rime.lua"
            echo -e "  ${GREEN}[ok]${NC} rime.lua"
        elif ! grep -q 'liu_w2c_sorter' "$RIME_DIR/rime.lua"; then
            cp -f "$RIME_DIR/rime.lua" "$RIME_DIR/rime.lua.bak"
            cat "$liur_rime_lua" >> "$RIME_DIR/rime.lua"
            echo -e "  ${GREEN}[ok]${NC} rime.lua（合併，兩邊模組都保留）"
        else
            echo -e "  ${GREEN}[已安裝]${NC} rime.lua"
        fi
    fi
    rm -f "$liur_rime_lua"
    if [ "$version" = "mixed" ]; then
        cp -f "$RIME_DIR/configs/liur.schema.yaml" "$RIME_DIR/liur.schema.yaml" 2>/dev/null \
            && echo -e "  ${GREEN}[ok]${NC} 嘸蝦米完整版（中打含英文詞庫版）"
    else
        cp -f "$RIME_DIR/configs/liur.chinese-only.schema.yaml" "$RIME_DIR/liur.schema.yaml" 2>/dev/null \
            && echo -e "  ${GREEN}[ok]${NC} 嘸蝦米基礎版（中打不含英文詞庫）"
    fi
    rm -rf "$RIME_DIR/configs"
    installer_register_schema liur
    [ "$version" = "mixed" ] && installer_register_schema easy_en
    echo -e "  ${GREEN}[ok]${NC} 已將 liur 加入 default.custom.yaml（保留既有方案）"
    for p in "${fonts[@]}"; do
        f="$(basename "$p")"
        if [ -f "$FONT_DIR/$f" ]; then
            echo -e "  ${GREEN}[已安裝]${NC} $f（字體）"
        else
            mkdir -p "$FONT_DIR"
            if curl -fsSL --connect-timeout 10 --max-time 300 "$base/$p" -o "$FONT_DIR/$f"; then
                echo -e "  ${GREEN}[ok]${NC} $f（字體）"
            else
                echo -e "  ${YELLOW}[失敗]${NC} $f（字體）"
            fi
        fi
    done
}
# ---- 進階功能區塊結束 ----

installer_ask_what_to_install

# ============================================================
# 偵測現有方案
# ============================================================
echo "[ 偵測現有方案 ]"
echo

EXISTING_SCHEMAS=()
for schema_file in "$RIME_DIR"/*.schema.yaml; do
    [ -f "$schema_file" ] || continue
    schema_name=$(basename "$schema_file" .schema.yaml)
    EXISTING_SCHEMAS+=("$schema_name")
done

if [ ${#EXISTING_SCHEMAS[@]} -gt 0 ]; then
    echo -e "已安裝的輸入方案："
    for s in "${EXISTING_SCHEMAS[@]}"; do
        echo -e "  ${GREEN}•${NC} $s"
    done
    echo
    echo -e "${GREEN}拍台文只會安裝 phah_taibun_* 檔案，不會覆蓋現有方案${NC}"
else
    echo -e "未偵測到現有方案（首次安裝）"
fi

echo

# 檢查現有 default.custom.yaml 中是否已有 phah_taibun
NEED_REGISTER=true
[ "$INSTALL_PHAH" = true ] || NEED_REGISTER=false
if [ -f "$RIME_DIR/default.custom.yaml" ]; then
    if grep -q 'phah_taibun' "$RIME_DIR/default.custom.yaml"; then
        NEED_REGISTER=false
        echo -e "${GREEN}default.custom.yaml 已含 phah_taibun 方案，跳過註冊${NC}"
    else
        echo -e "${YELLOW}偵測到現有的 default.custom.yaml，將追加拍台文方案（不會覆蓋現有設定）${NC}"
    fi
fi

# ============================================================
# Step 1: 複製方案檔
# ============================================================
if [ "$INSTALL_PHAH" = true ]; then

echo "[ Step 1: 複製方案檔 ]"
echo

mkdir -p "$RIME_DIR"

SCHEMA_FILES=(
    "phah_taibun.schema.yaml"
    "phah_taibun_telex.schema.yaml"
    "phah_taibun.dict.yaml"
    "hanlo_rules.yaml"
    "lighttone_rules.json"
    "moe700.yaml"
    "hoabun_map.txt"
    "phah_taibun.wordlist"
)

for file in "${SCHEMA_FILES[@]}"; do
    src="$PROJ_DIR/schema/$file"
    if [ -f "$src" ]; then
        cp -f "$src" "$RIME_DIR/$file"
        echo -e "  ${GREEN}[ok]${NC} $file"
    else
        echo -e "  ${RED}[miss]${NC} $file（不存在：$src）"
    fi
done


# OpenCC 資料（Emoji，rime-emoji LGPL-3.0）到 opencc/ 子目錄
OPENCC_FILES=(
    "emoji.json"
    "emoji_word.txt"
    "emoji_category.txt"
)
mkdir -p "$RIME_DIR/opencc"
for file in "${OPENCC_FILES[@]}"; do
    src="$PROJ_DIR/opencc/$file"
    if [ -f "$src" ]; then
        cp -f "$src" "$RIME_DIR/opencc/$file"
        echo -e "  ${GREEN}[ok]${NC} opencc/$file"
    else
        echo -e "  ${RED}[miss]${NC} opencc/$file（不存在：$src）"
    fi
done

# 使用者自訂字典：只在不存在時複製（不覆蓋使用者詞庫）
for file in "phah_taibun.custom.dict.yaml" "phah_taibun.phrase.dict.yaml"; do
    src="$PROJ_DIR/schema/$file"
    dest="$RIME_DIR/$file"
    if [ -f "$src" ] && [ ! -f "$dest" ]; then
        cp "$src" "$dest"
        echo -e "  ${GREEN}[ok]${NC} $file（首次安裝）"
    elif [ -f "$src" ] && [ -f "$dest" ]; then
        echo -e "  ${YELLOW}[保留]${NC} $file（已有使用者資料）"
    fi
done

echo

# ============================================================
# Step 2: 複製 Lua 腳本
# ============================================================
echo "[ Step 2: 複製 Lua 腳本 ]"
echo

mkdir -p "$RIME_DIR/lua"

# 只複製 phah_taibun_* 開頭的 Lua 檔案，避免覆蓋其他方案的模組
LUA_COUNT=0
for src in "$PROJ_DIR"/lua/phah_taibun_*.lua; do
    [ -f "$src" ] || continue
    filename=$(basename "$src")
    cp -f "$src" "$RIME_DIR/lua/$filename"
    echo -e "  ${GREEN}[ok]${NC} $filename"
    LUA_COUNT=$((LUA_COUNT + 1))
done

if [ "$LUA_COUNT" -eq 0 ]; then
    echo -e "  ${YELLOW}[skip]${NC} 沒有找到 Lua 腳本"
fi

# 合併 rime.lua 模組註冊檔（舊版 librime-lua 相容）
if [ -f "$PROJ_DIR/rime.lua" ]; then
    if [ -f "$RIME_DIR/rime.lua" ]; then
        cp -f "$RIME_DIR/rime.lua" "$RIME_DIR/rime.lua.bak"
        echo -e "  ${YELLOW}[備份]${NC} rime.lua → rime.lua.bak"

        MERGED=0
        while IFS= read -r line; do
            [[ -z "$line" || "$line" =~ ^[[:space:]]*-- ]] && continue
            if ! grep -qF "$line" "$RIME_DIR/rime.lua"; then
                echo "$line" >> "$RIME_DIR/rime.lua"
                MERGED=$((MERGED + 1))
            fi
        done < "$PROJ_DIR/rime.lua"
        if [ "$MERGED" -gt 0 ]; then
            echo -e "  ${GREEN}[ok]${NC} rime.lua（追加 $MERGED 個模組，保留現有設定）"
        else
            echo -e "  ${GREEN}[ok]${NC} rime.lua（模組已註冊，無需變更）"
        fi
    else
        cp -f "$PROJ_DIR/rime.lua" "$RIME_DIR/rime.lua"
        echo -e "  ${GREEN}[ok]${NC} rime.lua（模組註冊）"
    fi
fi

fi

# ============================================================
# Step 2.5: 註冊方案到 default.custom.yaml
# ============================================================
installer_backup_default_custom
if [ "$NEED_REGISTER" = true ]; then
    if [ -f "$RIME_DIR/default.custom.yaml" ]; then
        cp -f "$RIME_DIR/default.custom.yaml" "$RIME_DIR/default.custom.yaml.bak"
        echo -e "  ${YELLOW}[備份]${NC} default.custom.yaml → default.custom.yaml.bak"

        LAST_SCHEMA_LINE=$(grep -n '\- schema:' "$RIME_DIR/default.custom.yaml" | tail -1 | cut -d: -f1)
        if [ -n "$LAST_SCHEMA_LINE" ]; then
            NEW_LINE=$(sed -n "${LAST_SCHEMA_LINE}p" "$RIME_DIR/default.custom.yaml" | sed 's/- schema: .*/- schema: phah_taibun/')
            sed -i '' "${LAST_SCHEMA_LINE}a\\
${NEW_LINE}" "$RIME_DIR/default.custom.yaml"
        elif grep -q '^__patch:' "$RIME_DIR/default.custom.yaml"; then
            # __patch: 列表檔：合併必須用 - patch/+，直接加 key 會落在列表外（壞 YAML）
            printf '\n  - patch/+:\n      schema_list/@next:\n        schema: phah_taibun\n' >> "$RIME_DIR/default.custom.yaml"
        else
            printf '\n  schema_list/@next:\n    schema: phah_taibun\n' >> "$RIME_DIR/default.custom.yaml"
        fi
        echo -e "  ${GREEN}[ok]${NC} 已將 phah_taibun 追加到 default.custom.yaml（保留現有方案）"
    else
        cp -f "$PROJ_DIR/schema/default.custom.yaml" "$RIME_DIR/default.custom.yaml"
        echo -e "  ${GREEN}[ok]${NC} default.custom.yaml（新建）"
    fi
fi
# ============================================================
# Step 2.55: 舊安裝補註冊 Telex 方案（既有 default.custom.yaml 已含
# phah_taibun，主註冊步驟會跳過，需另行追加）
# ============================================================
# default.custom.yaml 有兩種格式：__patch:（patch 列表）與 patch:（單一 map）。
# 直接把 schema_list/@next 1: 附加到檔尾會落在結構外，造成 YAML 解析失敗
# （所有方案註冊失效），必須依格式插入。
if [ -f "$RIME_DIR/default.custom.yaml" ] && ! grep -q 'phah_taibun_telex' "$RIME_DIR/default.custom.yaml"; then
    cp -f "$RIME_DIR/default.custom.yaml" "$RIME_DIR/default.custom.yaml.bak"
    LAST_SCHEMA_LINE=$(grep -n '^[[:space:]]*- schema: phah_taibun[[:space:]]*$' "$RIME_DIR/default.custom.yaml" | tail -1 | cut -d: -f1)
    if [ -n "$LAST_SCHEMA_LINE" ]; then
        INDENT=$(sed -n "${LAST_SCHEMA_LINE}s/^\([[:space:]]*\).*/\1/p" "$RIME_DIR/default.custom.yaml")
        sed -i '' "${LAST_SCHEMA_LINE}a\\
${INDENT}- schema: phah_taibun_telex" "$RIME_DIR/default.custom.yaml"
    elif grep -q '^__patch:' "$RIME_DIR/default.custom.yaml"; then
        printf '\n  - patch/+:\n      schema_list/@next 1:\n        schema: phah_taibun_telex\n' >> "$RIME_DIR/default.custom.yaml"
    else
        printf '\n  schema_list/@next 1:\n    schema: phah_taibun_telex\n' >> "$RIME_DIR/default.custom.yaml"
    fi
    echo -e "  ${GREEN}[ok]${NC} 已將 phah_taibun_telex 追加到 default.custom.yaml（保留現有方案）"
fi

# ============================================================
# Step 2.6: save_options — 記住 F4 選過的 TL/POJ、漢羅/全羅
# ============================================================
if [ -f "$RIME_DIR/default.custom.yaml" ] && ! grep -q 'poj_mode' "$RIME_DIR/default.custom.yaml"; then
    cp -f "$RIME_DIR/default.custom.yaml" "$RIME_DIR/default.custom.yaml.bak"
    if grep -q '^__patch:' "$RIME_DIR/default.custom.yaml"; then
        printf '\n  - patch/+:\n      switcher/save_options/@before 0: poj_mode\n      switcher/save_options/@next: full_romanization\n' >> "$RIME_DIR/default.custom.yaml"
    else
        sed -i '' '/^patch:/a\
  switcher/save_options/@before 0: poj_mode\
  switcher/save_options/@next: full_romanization
' "$RIME_DIR/default.custom.yaml"
    fi
    echo -e "  ${GREEN}[ok]${NC} 已將 poj_mode / full_romanization 加入 save_options（記住模式選擇）"
fi

installer_keep_which_prompt
installer_bopomofo_prompt

echo

# ============================================================
# Step 3: 檢查系統依賴
# ============================================================
echo "[ Step 3: 檢查系統依賴 ]"
echo

# 注音反查需要 bopomofo_tw 方案
if [ -f "$SQUIRREL_SHARED/bopomofo_tw.schema.yaml" ] || [ -f "$RIME_DIR/bopomofo_tw.schema.yaml" ]; then
    echo -e "  ${GREEN}[ok]${NC} bopomofo_tw（注音反查字典）"
elif [ -f "$SQUIRREL_SHARED/terra_pinyin.schema.yaml" ] || [ -f "$RIME_DIR/terra_pinyin.schema.yaml" ]; then
    echo -e "  ${GREEN}[ok]${NC} terra_pinyin（注音反查字典基礎）"
else
    echo -e "  ${YELLOW}[warn]${NC} 找不到 bopomofo_tw 字典，注音反查功能將無法使用"
    echo -e "         鼠鬚管通常已內建注音方案，若無反應請重新安裝鼠鬚管"
fi

# 芫荽 iansui 字體
mkdir -p "$FONT_DIR"
if ls "$FONT_DIR"/Iansui* &>/dev/null || ls "$FONT_DIR"/iansui* &>/dev/null; then
    echo -e "  ${GREEN}[ok]${NC} 芫荽 iansui 字體"
else
    echo -e "  ${YELLOW}[install]${NC} 正在下載芫荽 iansui 字體..."
    IANSUI_REVISION="9d9a8e68bf1e138dd91e562eeff28d95bca33196"
    IANSUI_SHA256="7f1aa62e9dcbf40d0ce41a5d3f1e5ea602e66c295778ac6fefb6b84d8ed08bd5"
    IANSUI_URL="https://raw.githubusercontent.com/ButTaiwan/iansui/$IANSUI_REVISION/fonts/ttf/Iansui-Regular.ttf"
    FONT_TMP="$FONT_DIR/.Iansui-Regular.ttf.download"
    if curl -fsSL "$IANSUI_URL" -o "$FONT_TMP" \
        && printf '%s  %s\n' "$IANSUI_SHA256" "$FONT_TMP" | shasum -a 256 -c - >/dev/null; then
        mv -f "$FONT_TMP" "$FONT_DIR/Iansui-Regular.ttf"
        echo -e "  ${GREEN}[ok]${NC} 芫荽 iansui 字體已驗證並安裝到 $FONT_DIR"
    else
        rm -f "$FONT_TMP"
        echo -e "  ${YELLOW}[warn]${NC} 字體下載或 SHA-256 驗證失敗，請手動安裝："
        echo -e "         https://github.com/ButTaiwan/iansui/releases"
    fi
fi

echo

if [ "$INSTALL_LIUR" = true ]; then
    installer_install_liur || echo -e "${YELLOW}嘸蝦米安裝失敗，拍台文不受影響；可稍後重試${NC}"
fi

# ============================================================
# Step 3.5: 整理 default.custom.yaml（乾淨排版＋說明註解；
# 使用者自有設定原樣保留，__patch: 複合格式不動）
# ============================================================
if installer_normalize_default_custom; then
    echo -e "  ${GREEN}[ok]${NC} 已整理 default.custom.yaml（乾淨排版＋註解）"
else
    echo -e "  ${YELLOW}[保留]${NC} default.custom.yaml 維持原格式（__patch: 複合格式不動，方案已補齊）"
fi

# ============================================================
# Step 4: 部署 RIME（鼠鬚管）
# ============================================================
echo "[ Step 4: 部署 RIME ]"
echo

# 終止鼠鬚管並重新啟動以觸發部署（參考 rime-liur）
killall Squirrel 2>/dev/null || true
sleep 1
if ! open -a Squirrel; then
    echo -e "${RED}部署失敗：無法重新啟動鼠鬚管。${NC}" >&2
    echo "請確認 /Library/Input Methods/Squirrel.app 存在，再手動執行：open -a Squirrel" >&2
    exit 1
fi
echo -e "${GREEN}已重新啟動鼠鬚管，正在部署中...${NC}"

echo
echo "======================================"
echo -e "${GREEN}  拍台文 Phah Tai-bun 安裝完成！${NC}"
echo "======================================"
echo
echo "Rime 框架：鼠鬚管 Squirrel"
echo "Rime 資料夾：$RIME_DIR"
echo
echo "已安裝："
echo "  - 方案檔：${#SCHEMA_FILES[@]} 個"
echo "  - Lua 腳本：${LUA_COUNT} 個（皆為 phah_taibun_* 命名）"
echo

# 顯示所有可用方案
echo "可用的輸入方案："
for schema_file in "$RIME_DIR"/*.schema.yaml; do
    [ -f "$schema_file" ] || continue
    schema_name=$(basename "$schema_file" .schema.yaml)
    if [ "$schema_name" = "phah_taibun" ]; then
        echo -e "  ${GREEN}•${NC} $schema_name（拍台文）← 新安裝"
    else
        echo -e "  •  $schema_name"
    fi
done
echo
echo "切換輸入法：Ctrl+\` 或 Ctrl+Shift+\`"
echo

# 字體設定提示
SQUIRREL_CUSTOM="$RIME_DIR/squirrel.custom.yaml"
if [ -f "$SQUIRREL_CUSTOM" ] && grep -q "font_face.*[Ii]ansui" "$SQUIRREL_CUSTOM" 2>/dev/null; then
    : # 已設定
else
    echo -e "${YELLOW}【字體設定】${NC}"
    echo "  建議在 $SQUIRREL_CUSTOM 加入以下設定："
    echo
    echo -e "    ${GREEN}patch:${NC}"
    echo -e "    ${GREEN}  style/font_face: \"Iansui\"${NC}"
    echo -e "    ${GREEN}  style/font_point: 18${NC}"
    echo
    echo "  儲存後重新部署即可生效。"
    echo
fi

echo "如遇問題，請到 GitHub 回報："
echo "  https://github.com/soanseng/rime-phah-taibun"
echo
