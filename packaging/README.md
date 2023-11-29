# Packaging
This directory contains scripts and config for building Naturtag packages in the following formats:
* PyInstaller executable (Windows, macOS, Linux)
* Installer executable (Windows)
* DMG package (macOS)
* DEB package (Linux, Debian and derivatives)
* RPM package (Linux, Fedora and derivatives)
* Snap package (Linux)
* Taxonomy full text search database (optional download)

# Release steps
* Locally build full taxonomy FTS database (See: https://pyinaturalist-convert.readthedocs.io/en/stable/modules/fts.html)
* Export subset of db (English language, common species only) with `export_taxa.sh`
  * Commit to repo under `assets/data/taxonomy.tar.gz`
* Update version in `pyproject.toml` and Actual Installer config (`naturtag.aip`)
* Create and push new git tag. This will trigger jobs to build packages and create a new GitHub release.
* Export full db with `export_taxa_full.sh`
  * After the release jobs complete, manually upload this to the release assets
