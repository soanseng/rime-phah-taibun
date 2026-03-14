#!/usr/bin/env bash
# install.sh — 拍台文 Phah Tai-bun 安裝入口
# 偵測作業系統並呼叫對應的安裝腳本

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

case "$(uname -s)" in
    Linux)
        exec bash "$SCRIPT_DIR/scripts/install_linux.sh" "$@"
        ;;
    Darwin)
        echo "macOS 安裝尚未支援，請手動複製檔案到 ~/Library/Rime/"
        exit 1
        ;;
    *)
        echo "不支援的作業系統：$(uname -s)"
        exit 1
        ;;
esac
