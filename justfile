# Notes:
# * lint recipe: tools and environments are managed by prek/pre-commit
# * All other recipes: uv will manage venv and automatically install python+dependencies as needed

doc_build_dir := 'docs/_build/html'
live_docs_port := '8181'
live_docs_watch := 'pyinaturalist examples'
live_docs_ignore := '*.csv *.ipynb *.pyc *.tmp **/modules/* **/jupyter_execute/*'

# Run linters and generate coverage report (default)
default: lint cov


# Local development
# ----------------------------------------

# Run tests; optionally specify path(s)
test *paths='test':
    uv run pytest {{paths}}

# Run tests and generate coverage report; optionally specify coverage formats (default: html term)
cov *cov_formats='html term':
    #!/usr/bin/env sh
    cov_args=""
    for fmt in {{cov_formats}}; do cov_args="$cov_args --cov-report=$fmt"; done
    if [ -n "$PYTEST_VERBOSE" ]; then verbose="--verbose"; fi
    uv run pytest --cov $cov_args $verbose test

# Build Sphinx documentation
docs:
    uv run sphinx-build docs {{doc_build_dir}} -j auto

# Auto-build docs with live reload in browser
livedocs open='':
    #!/usr/bin/env sh
    watch_args=""
    for p in {{live_docs_watch}}; do watch_args="$watch_args --watch $p"; done
    ignore_args=""
    for p in {{live_docs_ignore}}; do ignore_args="$ignore_args --ignore $p"; done
    just clean
    uv run \
        sphinx-autobuild docs {{doc_build_dir}} \
        -a \
        --host 0.0.0.0 \
        --port {{live_docs_port}} \
        -j auto \
        $watch_args \
        $ignore_args

# Run linters and code formatters via prek/pre-commit
lint:
    prek run --all-files

# Clean up temporary build + documentation files
clean:
    rm -rf dist build docs/_build docs/modules test-reports


# Build scripts
# ----------------------------------------

# Export taxonomy data
export-taxa:
    ./packaging/export_taxa.sh

# Build pyinstaller package and bundle taxonomy data
build-pyinstaller:
    uv run pyinstaller -y packaging/naturtag.spec
    ./packaging/bundle_taxonomy.sh

# Build all Linux packages
build-linux-pkgs:
    ./packaging/build_fpm.sh
    ./packaging/build_appimage.sh

# Build Flatpak bundle (requires naturtag-linux.tar.gz from build-pyinstaller)
build-flatpak:
    ./packaging/build_flatpak.sh

# Build Windows installer
build-win-installer:
    iscc //DAppVersion=`just version` packaging/naturtag.iss

# Build and validate macOS DMG
build-dmg:
    ./packaging/build_dmg.sh
    ./packaging/validate_dmg.sh

# Get current application version
version:
    @uv run python packaging/get_version.py
