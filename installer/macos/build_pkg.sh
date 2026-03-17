#!/bin/bash
# build_pkg.sh — Build macOS .pkg installer for 拍台文輸入法
# Requires: macOS with pkgbuild + productbuild

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"
STAGING="${BUILD_DIR}/staging"
VERSION="${1:-1.0.0}"

echo "Building phah_taibun macOS installer v${VERSION}..."

# --- Clean & prepare ---
rm -rf "${BUILD_DIR}"
mkdir -p "${STAGING}/schema" "${STAGING}/lua" "${STAGING}/scripts" "${STAGING}/fonts"

# --- Stage files in standard project layout ---
# (postinstall calls install_macos.sh --project-root pointing here)
cp "${PROJECT_ROOT}"/schema/phah_taibun.schema.yaml \
   "${PROJECT_ROOT}"/schema/phah_taibun.dict.yaml \
   "${PROJECT_ROOT}"/schema/phah_taibun_reverse.dict.yaml \
   "${PROJECT_ROOT}"/schema/hanlo_rules.yaml \
   "${PROJECT_ROOT}"/schema/lighttone_rules.json \
   "${PROJECT_ROOT}"/schema/hoabun_map.txt \
   "${PROJECT_ROOT}"/schema/default.custom.yaml \
   "${STAGING}/schema/"

# Copy user-editable dicts if they exist
for f in phah_taibun.phrase.dict.yaml phah_taibun.custom.dict.yaml; do
    [ -f "${PROJECT_ROOT}/schema/$f" ] && cp "${PROJECT_ROOT}/schema/$f" "${STAGING}/schema/"
done

cp "${PROJECT_ROOT}"/lua/phah_taibun_*.lua "${STAGING}/lua/"
cp "${PROJECT_ROOT}"/rime.lua "${STAGING}/"

# Stage install script (postinstall delegates to it)
cp "${PROJECT_ROOT}"/scripts/install_macos.sh "${STAGING}/scripts/"

# --- Download Iansui font if not cached ---
FONT_PATH="${STAGING}/fonts/Iansui-Regular.ttf"
if [ ! -f "${FONT_PATH}" ]; then
    echo "Downloading Iansui font..."
    FONT_URL=$(curl -s https://api.github.com/repos/ChhoeTaigi/iansui/releases/latest \
        | grep "browser_download_url.*Iansui-Regular\.ttf" \
        | head -1 \
        | cut -d '"' -f 4)
    curl -L -o "${FONT_PATH}" "${FONT_URL}"
fi

# --- Build component .pkg ---
pkgbuild \
    --root "${STAGING}" \
    --install-location /private/var/tmp/phah_taibun_staging \
    --scripts "${SCRIPT_DIR}/scripts" \
    --identifier com.phah-taibun.schema \
    --version "${VERSION}" \
    "${BUILD_DIR}/phah_taibun.pkg"

# --- Build product .pkg (with UI) ---
# Copy resources for installer UI
mkdir -p "${BUILD_DIR}/resources"
cp "${PROJECT_ROOT}/LICENSE" "${BUILD_DIR}/resources/"

cat > "${BUILD_DIR}/resources/welcome.html" << 'HTML'
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, sans-serif; padding: 20px;">
<h1>拍台文輸入法</h1>
<h2>Phah Tai-bun Input Method</h2>
<p>這是一個基於 Rime 的台語輸入法，支援漢羅混寫。</p>
<p>安裝前請確認：</p>
<ul>
<li>需要已安裝鼠鬚管 (Squirrel) Rime 引擎（<a href="https://rime.im/download/">下載</a>）</li>
</ul>
<p>安裝程式會：</p>
<ul>
<li>安裝拍台文輸入方案</li>
<li>安裝芫荽字體</li>
</ul>
<p>安裝完成後，請在「系統設定 → 鍵盤 → 輸入方式」中啟用。</p>
</body>
</html>
HTML

productbuild \
    --distribution "${SCRIPT_DIR}/distribution.xml" \
    --resources "${BUILD_DIR}/resources" \
    --package-path "${BUILD_DIR}" \
    "${BUILD_DIR}/phah-taibun-${VERSION}.pkg"

echo ""
echo "Build complete: ${BUILD_DIR}/phah-taibun-${VERSION}.pkg"
