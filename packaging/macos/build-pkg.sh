#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${PHAH_TAIBUN_VERSION:-0.4.0}"
BUILD_DIR="$ROOT/packaging/macos/build"
PAYLOAD_DIR="$BUILD_DIR/payload/Library/Application Support/PhahTaiBun"
COMPONENT_PKG="$BUILD_DIR/PhahTaiBunComponent.pkg"
OUTPUT_PKG="$BUILD_DIR/PhahTaiBun.pkg"

rm -rf "$BUILD_DIR"
mkdir -p "$PAYLOAD_DIR"

cp -R "$ROOT/schema" "$PAYLOAD_DIR/schema"
cp -R "$ROOT/lua" "$PAYLOAD_DIR/lua"
cp -R "$ROOT/icons" "$PAYLOAD_DIR/icons"
cp "$ROOT/rime.lua" "$PAYLOAD_DIR/rime.lua"
cp "$ROOT/scripts/install_macos.sh" "$PAYLOAD_DIR/install_macos.sh"

pkgbuild \
  --root "$BUILD_DIR/payload" \
  --identifier "tw.phah-taibun.installer" \
  --version "$VERSION" \
  --scripts "$ROOT/packaging/macos/scripts" \
  "$COMPONENT_PKG"

productbuild \
  --package "$COMPONENT_PKG" \
  "$OUTPUT_PKG"

echo "Built: $OUTPUT_PKG"
