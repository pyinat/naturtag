#!/usr/bin/env bash
# Build an AppImage from the PyInstaller output
set -euo pipefail

SCRIPT_DIR=$(dirname "$(realpath "$0")")
ROOT_DIR=$(dirname "$SCRIPT_DIR")
ASSETS_DIR=$ROOT_DIR/assets
DIST_DIR=$ROOT_DIR/dist
SRC_DIR=$DIST_DIR/naturtag
APPDIR=$DIST_DIR/AppDir
APPIMAGETOOL=$DIST_DIR/appimagetool

# Download appimagetool if not already present
if [ ! -f "$APPIMAGETOOL" ]; then
    ARCH=$(uname -m)
    curl -fsSL -o "$APPIMAGETOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"
    chmod +x "$APPIMAGETOOL"
fi

# Assemble AppDir
rm -rf "$APPDIR"
mkdir -p "$APPDIR/opt"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/scalable/apps"

# Copy PyInstaller output
cp -r "$SRC_DIR" "$APPDIR/opt/naturtag"

# Create AppRun launcher
cat > "$APPDIR/AppRun" << 'EOF'
#!/usr/bin/env bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
exec "$HERE/opt/naturtag/naturtag" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# Copy desktop file with Exec= adjusted for AppImage
sed 's|^Exec=.*|Exec=naturtag|; s|^Path=.*||' "$SCRIPT_DIR/naturtag.desktop" \
    > "$APPDIR/naturtag.desktop"
cp "$APPDIR/naturtag.desktop" "$APPDIR/usr/share/applications/"

# Copy icon
cp "$ASSETS_DIR/icons/logo.svg" "$APPDIR/naturtag.svg"
cp "$ASSETS_DIR/icons/logo.svg" "$APPDIR/usr/share/icons/hicolor/scalable/apps/naturtag.svg"

# Symlink main executable and set file permissions
ln -sf ../../opt/naturtag/naturtag "$APPDIR/usr/bin/naturtag"
find "$APPDIR/opt/naturtag/" -type f -exec chmod 644 -- {} +
find "$APPDIR/opt/naturtag/" -type d -exec chmod 755 -- {} +
chmod +x "$APPDIR/opt/naturtag/naturtag"

# Build AppImage
ARCH=$(uname -m) "$APPIMAGETOOL" "$APPDIR" "$DIST_DIR/naturtag.AppImage"
echo "AppImage created: $DIST_DIR/naturtag.AppImage"
