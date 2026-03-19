#!/usr/bin/env bash
# Build a Flatpak bundle from pyinstaller package
set -euo pipefail

SCRIPT_DIR=$(dirname "$(realpath "$0")")
ROOT_DIR=$(dirname "$SCRIPT_DIR")
DIST_DIR=$ROOT_DIR/dist
TARBALL=$ROOT_DIR/naturtag-linux.tar.gz
BUILD_DIR=$ROOT_DIR/flatpak-build
REPO_DIR=$ROOT_DIR/flatpak-repo

if [ ! -f "$TARBALL" ]; then
    echo "Error: $TARBALL not found. Run 'just build-pyinstaller' first." >&2
    exit 1
fi

mkdir -p "$DIST_DIR"

# Set version and date
VERSION=$(uv run python "$SCRIPT_DIR/get_version.py")
DATE=$(date -u +%Y-%m-%d)
sed "s|@VERSION@|$VERSION|g; s|@DATE@|$DATE|g" \
    "$SCRIPT_DIR/org.pyinat.naturtag.metainfo.xml" \
    > "$DIST_DIR/org.pyinat.naturtag.metainfo.xml"

# Build Flatpak and export a single-file bundle
flatpak-builder \
    --force-clean \
    --repo="$REPO_DIR" \
    "$BUILD_DIR" \
    "$SCRIPT_DIR/org.pyinat.naturtag.yml"
flatpak build-bundle \
    "$REPO_DIR" \
    "$DIST_DIR/naturtag.flatpak" \
    org.pyinat.naturtag

echo "Flatpak bundle created: $DIST_DIR/naturtag.flatpak"
