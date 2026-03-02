#!/usr/bin/env bash
# Validate a macOS DMG and its app bundle signatures after build.
# Mounts the DMG, runs codesign and Gatekeeper checks, then unmounts.
#
# Note: spctl --assess will fail for ad-hoc signed apps (expected for open-source distribution
# without a paid Apple Developer ID). The output confirms what Gatekeeper would reject and why.

hdiutil verify "$DMG_PATH"
hdiutil imageinfo "$DMG_PATH"

ROOT_DIR=$(dirname $(dirname "$(realpath $0)"))
DMG_PATH=$ROOT_DIR/dist/naturtag.dmg
MOUNT_POINT=/Volumes/naturtag

hdiutil attach "$DMG_PATH" -mountpoint "$MOUNT_POINT"
ls -la "$MOUNT_POINT/"

codesign --verify --verbose=4 "$MOUNT_POINT/naturtag.app"
codesign -dvvv --entitlements - "$MOUNT_POINT/naturtag.app"

# Gatekeeper simulation: expected to fail for ad-hoc signing, but output is diagnostic
spctl --assess --type exec --verbose=4 "$MOUNT_POINT/naturtag.app" || true

xattr -l "$MOUNT_POINT/naturtag.app" || true

# Verify dylibs and shared libraries are signed
find "$MOUNT_POINT/naturtag.app" -name '*.dylib' -o -name '*.so' | \
    while read lib; do codesign --verify --verbose=2 "$lib" || true; done

hdiutil detach "$MOUNT_POINT"
