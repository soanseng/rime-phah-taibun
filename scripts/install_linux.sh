#!/usr/bin/env bash
# 拍台文 Phah Tai-bun 自動安裝工具 (Linux / fcitx5 + ibus)
# 參考 soanseng/rime-liur-arch 的 rime_liur_installer_linux.sh

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 專案根目錄（install_linux.sh 在 scripts/ 下）
PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# ============================================================
# 偵測 Rime 框架
# ============================================================
detect_rime() {
    if [ -d "$HOME/.local/share/fcitx5/rime" ] || command -v fcitx5-remote &>/dev/null; then
        RIME_FRAMEWORK="fcitx5"
        RIME_DIR="$HOME/.local/share/fcitx5/rime"
    elif [ -d "$HOME/.config/ibus/rime" ] || command -v ibus &>/dev/null; then
        RIME_FRAMEWORK="ibus"
        RIME_DIR="$HOME/.config/ibus/rime"
    else
        RIME_FRAMEWORK=""
        RIME_DIR=""
    fi
}

# ============================================================
# 標題
# ============================================================
echo
echo "======================================"
echo "  拍台文 Phah Tai-bun 自動安裝工具"
echo "  (Linux / fcitx5 + ibus)"
echo "======================================"
echo

# ============================================================
# Step 0: 偵測環境
# ============================================================
detect_rime

if [ -z "$RIME_FRAMEWORK" ]; then
    echo -e "${RED}錯誤：找不到 fcitx5-rime 或 ibus-rime！${NC}"
    echo
    echo "請先安裝其中一個："
    echo
    echo "  fcitx5（推薦）："
    echo "    Arch:   sudo pacman -S fcitx5-rime"
    echo "    Debian: sudo apt install fcitx5-rime"
    echo "    Fedora: sudo dnf install fcitx5-rime"
    echo
    echo "  ibus："
    echo "    Arch:   sudo pacman -S ibus-rime"
    echo "    Debian: sudo apt install ibus-rime"
    echo "    Fedora: sudo dnf install ibus-rime"
    exit 1
fi

echo -e "偵測到 Rime 框架：${GREEN}${RIME_FRAMEWORK}${NC}"
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

# 自定義設定檔選項
if [ -f "$RIME_DIR/default.custom.yaml" ]; then
    echo -e "${YELLOW}偵測到現有的 default.custom.yaml${NC}"
    echo
    echo "1. 保留（推薦）- 保留現有設定，僅安裝方案檔"
    echo "2. 覆蓋 - 使用拍台文預設設定（會清除您的自訂設定）"
    echo

    while true; do
        read -p "請輸入選項 (1 或 2): " customChoice < /dev/tty
        case $customChoice in
            1)
                KEEP_DEFAULT_CUSTOM=true
                echo -e "${GREEN}已選擇：保留自定義設定檔${NC}"
                break
                ;;
            2)
                KEEP_DEFAULT_CUSTOM=false
                echo -e "${GREEN}已選擇：覆蓋自定義設定檔${NC}"
                break
                ;;
            *)
                echo -e "${RED}請輸入 1 或 2${NC}"
                ;;
        esac
    done
    echo
else
    KEEP_DEFAULT_CUSTOM=false
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

# default.custom.yaml 根據選擇處理
if [ "$KEEP_DEFAULT_CUSTOM" = false ]; then
    SCHEMA_FILES+=("default.custom.yaml")
fi

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

# 複製 rime.lua 模組註冊檔（舊版 librime-lua 相容）
if [ -f "$PROJ_DIR/rime.lua" ]; then
    cp -f "$PROJ_DIR/rime.lua" "$RIME_DIR/rime.lua"
    echo -e "  ${GREEN}[ok]${NC} rime.lua（模組註冊）"
fi

echo

# ============================================================
# Step 4: 建立共用 rime 預設檔案的符號連結 + 檢查依賴
# ============================================================
echo "[ Step 3: 檢查系統依賴 ]"
echo

RIME_SHARED="/usr/share/rime-data"
if [ -d "$RIME_SHARED" ]; then
    for preset in default.yaml key_bindings.yaml punctuation.yaml; do
        if [ -f "$RIME_SHARED/$preset" ] && [ ! -f "$RIME_DIR/$preset" ]; then
            ln -sf "$RIME_SHARED/$preset" "$RIME_DIR/$preset"
        fi
    done

    # 華語反查需要 luna_pinyin 字典
    if [ -f "$RIME_SHARED/luna_pinyin.schema.yaml" ] || [ -f "$RIME_DIR/luna_pinyin.schema.yaml" ]; then
        echo -e "  ${GREEN}[ok]${NC} luna_pinyin（華語反查字典）"
    else
        echo -e "  ${YELLOW}[warn]${NC} 找不到 luna_pinyin 字典，華語反查功能將無法使用"
        echo -e "         安裝方式："
        echo -e "           Arch:   sudo pacman -S rime-luna-pinyin"
        echo -e "           Debian: sudo apt install librime-data-luna-pinyin"
    fi
else
    echo -e "  ${YELLOW}[warn]${NC} 找不到 $RIME_SHARED，可能缺少 rime-data 套件"
fi

echo

# ============================================================
# Step 5: 部署 RIME
# ============================================================
echo "[ Step 4: 部署 RIME ]"
echo

if [ "$RIME_FRAMEWORK" = "fcitx5" ]; then
    if command -v fcitx5-remote &>/dev/null; then
        echo "正在重新部署 fcitx5-rime..."
        fcitx5-remote -r 2>/dev/null || true
        sleep 1
        if command -v rime_deployer &>/dev/null; then
            echo "正在編譯字典（可能需要數秒）..."
            rime_deployer --build "$RIME_DIR" 2>/dev/null || true
        fi
        fcitx5-remote -r 2>/dev/null || true
        echo -e "${GREEN}已重新部署 fcitx5-rime${NC}"
    else
        echo -e "${YELLOW}fcitx5-remote 不可用，請手動重啟 fcitx5${NC}"
    fi
elif [ "$RIME_FRAMEWORK" = "ibus" ]; then
    if command -v ibus &>/dev/null; then
        echo "正在重新部署 ibus-rime..."
        ibus write-cache 2>/dev/null || true
        if command -v rime_deployer &>/dev/null; then
            echo "正在編譯字典（可能需要數秒）..."
            rime_deployer --build "$RIME_DIR" 2>/dev/null || true
        fi
        ibus restart 2>/dev/null || true
        echo -e "${GREEN}已重新部署 ibus-rime${NC}"
    else
        echo -e "${YELLOW}ibus 不可用，請手動重啟 ibus${NC}"
    fi
fi

echo
echo "======================================"
echo -e "${GREEN}  拍台文 Phah Tai-bun 安裝完成！${NC}"
echo "======================================"
echo
echo "Rime 框架：$RIME_FRAMEWORK"
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
