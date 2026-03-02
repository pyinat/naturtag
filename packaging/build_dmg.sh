#!/usr/bin/env bash
# Build a disk image for macOS using create-dmg
set -euo pipefail

ROOT_DIR=$(dirname $(dirname "$(realpath $0)"))
DIST_DIR=$ROOT_DIR/dist
ICONS_DIR=$ROOT_DIR/assets/icons
PKG_DIR=$DIST_DIR/dmg
DMG_PATH=$DIST_DIR/naturtag.dmg

# Pre-flight checks
if [[ ! -d "$DIST_DIR/naturtag.app" ]]; then
    echo "Error: $DIST_DIR/naturtag.app not found. Run PyInstaller first." >&2
    exit 1
fi
if ! command -v create-dmg &>/dev/null; then
    echo "Error: create-dmg is not installed." >&2
    exit 1
fi

# Ad-hoc sign all bundled libraries, then the app itself
find "$DIST_DIR/naturtag.app" -name '*.dylib' -o -name '*.so' | while IFS= read -r lib; do
    codesign --force --sign - "$lib"
done
codesign --force --deep --sign - "$DIST_DIR/naturtag.app"
codesign --verify --verbose=2 "$DIST_DIR/naturtag.app"

mkdir "$PKG_DIR"
mv "$DIST_DIR/naturtag.app" "$PKG_DIR/"

create-dmg \
--volname "naturtag" \
--volicon "$ICONS_DIR/logo.icns" \
--icon-size 128 \
--hide-extension "naturtag.app" \
--no-internet-enable \
"$DMG_PATH" \
"$PKG_DIR"
