#!/usr/bin/env bash
# Build Linux packages with FPM
SRC_DIR=dist/naturtag
PKG_DIR=dist/fpm
export PATH=$PATH:~/.gem/ruby/2.7.0/bin:~/.gem/ruby/3.0.0/bin

# Options for package format(s) to build
while getopts "dsr" option; do
    case "${option}" in
        d)
            PGK_DEB='true';;
        s)
            PGK_SNAP='true';;
        r)
            PGK_RPM='true';;
    esac
done

# Copy pyinstaller output, icon, and desktop file
rm -rf $PKG_DIR
mkdir -p $PKG_DIR/opt
mkdir -p $PKG_DIR/usr/share/applications
mkdir -p $PKG_DIR/usr/share/icons/hicolor/scalable/apps
cp -r $SRC_DIR $PKG_DIR/opt/
cp assets/naturtag.desktop $PKG_DIR/usr/share/applications/
cp assets/logo.svg $PKG_DIR/usr/share/icons/hicolor/scalable/apps/naturtag.svg

# Set file permissions
find $PKG_DIR/opt/naturtag/ -type f -exec chmod 644 -- {} +
find $PKG_DIR/opt/naturtag/ -type d -exec chmod 755 -- {} +
find $PKG_DIR/usr/share -type f -exec chmod 644 -- {} +
chmod +x $PKG_DIR/opt/naturtag/naturtag

# Get app version from poetry config
poetry run pip install tomlkit  #  Shouldn't this already be installed?
app_version=$(poetry run python .github/get_version.py)
echo "Version: $app_version"

# DEB
if [[ ! -z "${PGK_DEB}" ]]; then
    fpm -f -C $PKG_DIR \
        -s dir \
        --verbose \
        --name "naturtag" \
        --version $app_version \
        --description "Tagger for iNaturalist observation photos" \
        --license "MIT" \
        --maintainer "jordan.cook@pioneer.com" \
        --url "https://naturtag.readthedocs.io" \
        --output-type deb \
        --package dist/naturtag.deb
fi

# Snap
if [[ ! -z "${PGK_SNAP}" ]]; then
    fpm -f -C $PKG_DIR \
        -s dir \
        --verbose \
        --name "naturtag" \
        --version $app_version \
        --description "Tagger for iNaturalist observation photos" \
        --license "MIT" \
        --maintainer "jordan.cook@pioneer.com" \
        --url "https://naturtag.readthedocs.io" \
        --output-type snap \
        --package dist/naturtag.snap
fi

# RPM
if [[ ! -z "${PGK_RPM}" ]]; then
    fpm -f -C $PKG_DIR \
        -s dir \
        --verbose \
        --name "naturtag" \
        --version $app_version \
        --description "Tagger for iNaturalist observation photos" \
        --license "MIT" \
        --maintainer "jordan.cook@pioneer.com" \
        --url "https://naturtag.readthedocs.io" \
        --output-type rpm \
        --package dist/naturtag.rpm
fi
