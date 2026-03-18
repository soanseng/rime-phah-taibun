#!/usr/bin/env bash
# 拍台文 Phah Tai-bun 自動安裝工具 (macOS / 鼠鬚管 Squirrel)
# 從 bundle installer 呼叫時：bash install_macos.sh --project-root /path/to/staged/files

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

# 專案根目錄：優先使用 --project-root 參數，否則從腳本位置推算
if [ -n "$_PROJ_ROOT_OVERRIDE" ] && [ -d "$_PROJ_ROOT_OVERRIDE" ]; then
    PROJ_DIR="$(cd "$_PROJ_ROOT_OVERRIDE" && pwd)"
else
    PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd)"
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
echo "[ Step 1: 複製方案檔 ]"
echo

mkdir -p "$RIME_DIR"

SCHEMA_FILES=(
    "phah_taibun.schema.yaml"
    "phah_taibun.dict.yaml"
    "phah_taibun_reverse.dict.yaml"
    "hanlo_rules.yaml"
    "lighttone_rules.json"
    "moe700.yaml"
    "hoabun_map.txt"
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

# ============================================================
# Step 2.5: 註冊方案到 default.custom.yaml
# ============================================================
if [ "$NEED_REGISTER" = true ]; then
    if [ -f "$RIME_DIR/default.custom.yaml" ]; then
        cp -f "$RIME_DIR/default.custom.yaml" "$RIME_DIR/default.custom.yaml.bak"
        echo -e "  ${YELLOW}[備份]${NC} default.custom.yaml → default.custom.yaml.bak"

        LAST_SCHEMA_LINE=$(grep -n '\- schema:' "$RIME_DIR/default.custom.yaml" | tail -1 | cut -d: -f1)
        if [ -n "$LAST_SCHEMA_LINE" ]; then
            NEW_LINE=$(sed -n "${LAST_SCHEMA_LINE}p" "$RIME_DIR/default.custom.yaml" | sed 's/- schema: .*/- schema: phah_taibun/')
            sed -i '' "${LAST_SCHEMA_LINE}a\\
${NEW_LINE}" "$RIME_DIR/default.custom.yaml"
        else
            printf '\n  schema_list/@next:\n    schema: phah_taibun\n' >> "$RIME_DIR/default.custom.yaml"
        fi
        echo -e "  ${GREEN}[ok]${NC} 已將 phah_taibun 追加到 default.custom.yaml（保留現有方案）"
    else
        cp -f "$PROJ_DIR/schema/default.custom.yaml" "$RIME_DIR/default.custom.yaml"
        echo -e "  ${GREEN}[ok]${NC} default.custom.yaml（新建）"
    fi
fi

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
    IANSUI_URL="https://raw.githubusercontent.com/ButTaiwan/iansui/main/fonts/ttf/Iansui-Regular.ttf"
    if curl -sL "$IANSUI_URL" -o "$FONT_DIR/Iansui-Regular.ttf" 2>/dev/null; then
        echo -e "  ${GREEN}[ok]${NC} 芫荽 iansui 字體已安裝到 $FONT_DIR"
    else
        echo -e "  ${YELLOW}[warn]${NC} 無法下載 iansui 字體，請手動安裝："
        echo -e "         https://github.com/ButTaiwan/iansui/releases"
    fi
fi

echo

# ============================================================
# Step 4: 部署 RIME（鼠鬚管）
# ============================================================
echo "[ Step 4: 部署 RIME ]"
echo

# 終止鼠鬚管並重新啟動以觸發部署（參考 rime-liur）
killall Squirrel 2>/dev/null || true
sleep 1
if [ -d "$SQUIRREL_APP" ]; then
    open -a Squirrel
    echo -e "${GREEN}已重新啟動鼠鬚管，正在部署中...${NC}"
else
    echo -e "${YELLOW}請手動點選選單列輸入法圖示 → 重新部署${NC}"
fi

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
