#!/usr/bin/env bash
# install.sh — 拍台文 Phah Tâi-bûn 安裝腳本
# 將 schema 和 Lua 檔案複製到 Rime 使用者資料夾
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 偵測 Rime 使用者資料夾
detect_rime_dir() {
    local dirs=(
        "$HOME/.local/share/fcitx5/rime"      # fcitx5-rime (Linux)
        "$HOME/.config/ibus/rime"              # ibus-rime (Linux)
        "$HOME/.config/fcitx/rime"             # fcitx-rime (Linux)
        "$HOME/Library/Rime"                   # macOS (Squirrel)
    )
    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            echo "$dir"
            return 0
        fi
    done
    return 1
}

# 主程式
main() {
    local rime_dir="${1:-}"

    if [ -z "$rime_dir" ]; then
        rime_dir=$(detect_rime_dir) || {
            echo "Error: 找不到 Rime 使用者資料夾"
            echo "用法: $0 [rime_user_dir]"
            echo "範例: $0 ~/.local/share/fcitx5/rime"
            exit 1
        }
    fi

    echo "安裝到: $rime_dir"

    # 複製 schema 檔案
    echo "複製 schema 檔案..."
    cp -f "$SCRIPT_DIR"/schema/*.yaml "$rime_dir/"

    # 複製 Lua 檔案
    echo "複製 Lua 腳本..."
    mkdir -p "$rime_dir/lua"
    cp -f "$SCRIPT_DIR"/lua/*.lua "$rime_dir/lua/"

    echo ""
    echo "安裝完成！請在輸入法設定中重新部署 Rime。"
    echo "  fcitx5: 右鍵系統匣圖示 → 重新部署"
    echo "  ibus:   ibus restart"
}

main "$@"
