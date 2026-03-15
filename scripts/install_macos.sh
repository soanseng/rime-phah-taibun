#!/usr/bin/env bash
# 拍台文 Phah Tai-bun 自動安裝工具 (macOS / 鼠鬚管 Squirrel)
# 參考 soanseng/rime-liur-arch 的 rime_liur_installer_linux.sh

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 專案根目錄（install_macos.sh 在 scripts/ 下）
PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# ============================================================
# 鼠鬚管路徑定義
# ============================================================
SQUIRREL_APP="/Library/Input Methods/Squirrel.app"
SQUIRREL_SHARED="$SQUIRREL_APP/Contents/SharedSupport"
SQUIRREL_BIN="$SQUIRREL_APP/Contents/MacOS/Squirrel"
RIME_DIR="${RIME_DIR:-$HOME/Library/Rime}"

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

# ============================================================
# Step 1: 確認安裝
# ============================================================
echo "本工具將執行以下作業："
echo "  1. 複製方案檔（schema/*.yaml）到 Rime 資料夾"
echo "  2. 複製 Lua 腳本（lua/*.lua + rime.lua）到 Rime 資料夾"
echo "  3. 部署 RIME（自動重新編譯）"
echo
echo -e "${YELLOW}※ 若有自訂設定尚未備份，請按 Ctrl+C 終止${NC}"
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
# Step 2: 複製方案檔
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
# Step 3: 複製 Lua 腳本
# ============================================================
echo "[ Step 2: 複製 Lua 腳本 ]"
echo

mkdir -p "$RIME_DIR/lua"

LUA_COUNT=0
for src in "$PROJ_DIR"/lua/*.lua; do
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
        # 已有 rime.lua，追加尚未註冊的拍台文模組
        MERGED=0
        while IFS= read -r line; do
            # 跳過空行和註解
            [[ -z "$line" || "$line" =~ ^[[:space:]]*-- ]] && continue
            # 檢查該行是否已存在
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
        # 沒有現有 rime.lua，直接複製
        cp -f "$PROJ_DIR/rime.lua" "$RIME_DIR/rime.lua"
        echo -e "  ${GREEN}[ok]${NC} rime.lua（模組註冊）"
    fi
fi

# ============================================================
# Step 2.5: 註冊方案到 default.custom.yaml
# ============================================================
if [ "$NEED_REGISTER" = true ]; then
    if [ -f "$RIME_DIR/default.custom.yaml" ]; then
        # 追加 phah_taibun 到現有的 schema_list（使用 @next 語法，不覆蓋現有方案）
        if grep -q 'schema_list/@next' "$RIME_DIR/default.custom.yaml"; then
            echo -e "  ${YELLOW}[skip]${NC} default.custom.yaml 已有 @next 區塊"
        else
            printf '\n  schema_list/@next:\n    schema: phah_taibun\n' >> "$RIME_DIR/default.custom.yaml"
        fi
        echo -e "  ${GREEN}[ok]${NC} 已將 phah_taibun 追加到 default.custom.yaml"
    else
        # 沒有 default.custom.yaml，複製專案的版本
        cp -f "$PROJ_DIR/schema/default.custom.yaml" "$RIME_DIR/default.custom.yaml"
        echo -e "  ${GREEN}[ok]${NC} default.custom.yaml（新建）"
    fi
fi

echo

# ============================================================
# Step 4: 檢查依賴
# ============================================================
echo "[ Step 3: 檢查系統依賴 ]"
echo

# 華語反查需要 luna_pinyin 字典
if [ -f "$SQUIRREL_SHARED/luna_pinyin.schema.yaml" ] || [ -f "$RIME_DIR/luna_pinyin.schema.yaml" ]; then
    echo -e "  ${GREEN}[ok]${NC} luna_pinyin（華語反查字典）"
else
    echo -e "  ${YELLOW}[warn]${NC} 找不到 luna_pinyin 字典，華語反查功能將無法使用"
    echo -e "         安裝方式："
    echo -e "           東風破（plum）："
    echo -e "             bash rime-install luna-pinyin"
    echo -e "           或手動下載："
    echo -e "             https://github.com/rime/rime-luna-pinyin"
fi

echo

# ============================================================
# Step 5: 部署 RIME（鼠鬚管）
# ============================================================
echo "[ Step 4: 部署 RIME ]"
echo

if [ -x "$SQUIRREL_BIN" ]; then
    echo "正在重新部署鼠鬚管..."
    "$SQUIRREL_BIN" --reload 2>/dev/null || true
    echo -e "${GREEN}已通知鼠鬚管重新部署${NC}"
else
    echo -e "${YELLOW}找不到鼠鬚管執行檔，請手動切換輸入法以觸發部署${NC}"
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
echo "  - Lua 腳本：${LUA_COUNT} 個"
echo
echo "切換輸入法：Ctrl+\` 或 Ctrl+Shift+\`"
echo
echo "如遇問題，請到 GitHub 回報："
echo "  https://github.com/soanseng/rime-phah-taibun"
echo
