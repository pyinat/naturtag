#!/usr/bin/env bash
# Build Linux packages with FPM

export PATH=$PATH:~/.gem/ruby/2.7.0/bin:~/.gem/ruby/3.0.0/bin
ASSETS_DIR=../assets
DIST_DIR=../dist
PKG_DIR=$DIST_DIR/fpm
SRC_DIR=$DIST_DIR/naturtag

# Copy pyinstaller output, icon, and desktop file
rm -rf $PKG_DIR
mkdir -p $PKG_DIR/opt
mkdir -p $PKG_DIR/usr/share/applications
mkdir -p $PKG_DIR/usr/share/icons/hicolor/scalable/apps
cp -r $SRC_DIR $PKG_DIR/opt/
cp $ASSETS_DIR/naturtag.desktop $PKG_DIR/usr/share/applications/
cp $ASSETS_DIR/logo.svg $PKG_DIR/usr/share/icons/hicolor/scalable/apps/naturtag.svg

# Set file permissions
find $PKG_DIR/opt/naturtag/ -type f -exec chmod 644 -- {} +
find $PKG_DIR/opt/naturtag/ -type d -exec chmod 755 -- {} +
find $PKG_DIR/usr/share -type f -exec chmod 644 -- {} +
chmod +x $PKG_DIR/opt/naturtag/naturtag

# Get app version from poetry config
poetry run pip install tomlkit  #  Shouldn't this already be installed?
app_version=$(poetry run python get_version.py)
echo "Version: $app_version"

# Build deb, snap, and rpm
fpm -C $PKG_DIR \
    --version $app_version \
    --output-type deb \
    --package $DIST_DIR/naturtag.deb
fpm -C $PKG_DIR \
    --version $app_version \
    --output-type snap \
    --package $DIST_DIR/naturtag.snap
fpm -C $PKG_DIR \
    --version $app_version \
    --output-type rpm \
    --package $DIST_DIR/naturtag.rpm
