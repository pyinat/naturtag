#!/usr/bin/env bash
# Build a disk image for macOS using create-dmg

ROOT_DIR=$(dirname $(dirname "$(realpath $0)"))
DIST_DIR=$ROOT_DIR/dist
ICONS_DIR=$ROOT_DIR/assets/icons
PKG_DIR=$DIST_DIR/dmg
DMG_PATH=$DIST_DIR/naturtag.dmg

mkdir $PKG_DIR
mv $DIST_DIR/naturtag.app $PKG_DIR/

create-dmg \
--volname "naturtag" \
--volicon "$ICONS_DIR/logo.icns" \
--icon-size 128 \
--hide-extension "naturtag.app" \
"$DMG_PATH" \
"$PKG_DIR"

hdiutil verify "$DMG_PATH"
hdiutil imageinfo "$DMG_PATH"
