#!/usr/bin/env bash

# Build a disk image for macOS using create-dmg
DIST_DIR=../dist
ICONS_DIR=../assets/icons
PKG_DIR=$DIST_DIR/dmg
BUNDLE_PATH=$DIST_DIR/naturtag.app
DMG_PATH=$DIST_DIR/naturtag.dmg

mkdir $PKG_DIR
mv $BUNDLE_PATH $PKG_DIR/

create-dmg \
--volname "naturtag" \
--volicon "$ICONS_DIR/logo.icns" \
--icon-size 128 \
--hide-extension "naturtag.app" \
"$DMG_PATH" \
"$PKG_DIR"
