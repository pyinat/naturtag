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

## Build taxonomy db
* Locally build full taxonomy FTS database with `build_taxon_db.py`. For reference, see:
  * [pyinaturalist_convert.dwca](https://pyinaturalist-convert.readthedocs.io/en/stable/modules/dwca.html)
  * [pyinaturalist_convert.taxonomy](https://pyinaturalist-convert.readthedocs.io/en/stable/modules/taxonomy.html)
  * [pyinaturalist_convert.fts](https://pyinaturalist-convert.readthedocs.io/en/stable/modules/fts.html)
* Export subset of db (English language, common species only) with `export_taxa.sh`
  * Commit to repo under `assets/data/taxonomy.tar.gz`
* Export full db with `export_taxa_full.sh`
  * This will create a file `taxonomy-full.tar.gz` to upload later

## Windows Installer
* Update version in `pyproject.toml` and Actual Installer config (`naturtag.aip`)
* On a Windows machine or VM, build the project locally and create an installer with Actual Installer.
* See steps in `build_win.ps1` for details (not fully automated; requires GUI interaction)

## Release
* Create and push new git tag. This will trigger jobs to build packages and create a new GitHub release.
* Most release assets will be built by the CI job, except for the following, which must be uploaded manually:
  * Full taxonomy db (`taxonomy-full.tar.gz`)
  * Windows installer (`naturtag-installer.exe`)
* Publish the GitHub release (by default, it will be created in draft mode)
