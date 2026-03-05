# Packaging
This directory contains scripts and config for building Naturtag packages. They are wrapped with simpler commands in `justfile`; see `just -l` for a list.

Artifacts:
* PyInstaller packages (Windows, macOS, Linux)
* Installer executable (Windows)
* DMG package (macOS)
* DEB package (Linux: Debian and derivatives)
* RPM package (Linux: Fedora and derivatives)
* pacman package (Linux: Arch and derivatives)
* AppImage package (Linux: Distro-agnostic)
* Taxonomy full text search database (optional download)

# Release steps

## Build taxonomy db
* Locally build full taxonomy FTS database with `build_taxon_db.py`. For reference, see:
  * [pyinaturalist_convert.dwca](https://pyinaturalist-convert.readthedocs.io/en/stable/modules/dwca.html)
  * [pyinaturalist_convert.taxonomy](https://pyinaturalist-convert.readthedocs.io/en/stable/modules/taxonomy.html)
  * [pyinaturalist_convert.fts](https://pyinaturalist-convert.readthedocs.io/en/stable/modules/fts.html)
* Run `export_taxa.sh` to export:
  * Subset (English language, common species only): commit to `assets/data/taxonomy.tar.gz`
  * Full db: upload to `taxonomy-full.tar.gz` to GitHub Releases

## Release
* Create and push new git tag. This will trigger jobs to build packages and create a new GitHub release.
* Most release assets will be built by the CI job, except for the following, which must be uploaded manually:
  * Full taxonomy db (`taxonomy-full.tar.gz`)
* Publish the GitHub release (by default, it will be created in draft mode)
