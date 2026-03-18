#!/usr/bin/env bash
# Bundle taxonomy FTS db with pyinstaller package and compress
set -euo pipefail

SCRIPT_DIR=$(dirname "$(realpath "$0")")
ROOT_DIR=$(dirname "$SCRIPT_DIR")
DIST_DIR=$ROOT_DIR/dist

# Set platform name
OS=$(uname -s)
case "$OS" in
  Linux)                dist_name=linux ;;
  MINGW*|MSYS*|CYGWIN*) dist_name=windows ;;  # Windows via Git Bash / GitHub Actions runner
  Darwin)               dist_name=macos ;;
  *)                    echo "Unsupported platform: $OS" >&2; exit 1 ;;
esac

# Set platform-specific paths
if [[ "$dist_name" == macos ]]; then
  ASSETS=$DIST_DIR/naturtag.app/Contents/Resources/assets/data
  tar_dir=$DIST_DIR
  tar_target=naturtag.app
else
  ASSETS=$DIST_DIR/naturtag/_internal/assets/data
  tar_dir=$DIST_DIR/naturtag
  tar_target=.
fi

tar -C "$tar_dir" -czvf "${ROOT_DIR}/naturtag-${dist_name}.tar.gz" "$tar_target"
