#!/usr/bin/env bash
# Validate a macOS DMG and its app bundle signatures after build.
# Mounts the DMG, runs codesign and Gatekeeper checks, then unmounts.
#
# Note: spctl --assess will fail for ad-hoc signed apps (expected for open-source distribution
# without a paid Apple Developer ID). The output confirms what Gatekeeper would reject and why.
ROOT_DIR=$(dirname $(dirname "$(realpath $0)"))
DMG_PATH=$ROOT_DIR/dist/naturtag.dmg
MOUNT_POINT=/Volumes/naturtag

# Pre-flight check
if [[ ! -f "$DMG_PATH" ]]; then
    echo "Error: $DMG_PATH not found. Run build_dmg.sh first." >&2
    exit 1
fi

hdiutil verify "$DMG_PATH"
hdiutil imageinfo "$DMG_PATH"

hdiutil attach "$DMG_PATH" -mountpoint "$MOUNT_POINT" -nobrowse
trap "hdiutil detach '$MOUNT_POINT' 2>/dev/null || true" EXIT

ls -la "$MOUNT_POINT/"

codesign --verify --verbose=4 "$MOUNT_POINT/naturtag.app"
codesign -dvvv --entitlements - "$MOUNT_POINT/naturtag.app"

# Gatekeeper simulation: expected to fail for ad-hoc signing, but output is diagnostic
spctl --assess --type exec --verbose=4 "$MOUNT_POINT/naturtag.app" || true

xattr -l "$MOUNT_POINT/naturtag.app" || true

# Verify dylibs and shared libraries are signed
find "$MOUNT_POINT/naturtag.app" -name '*.dylib' -o -name '*.so' | \
    while IFS= read -r lib; do codesign --verify --verbose=2 "$lib" || true; done
