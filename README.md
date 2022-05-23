# Naturtag

[![Build status](https://github.com/JWCook/naturtag/workflows/Build/badge.svg)](https://github.com/JWCook/naturtag/actions)
[![Documentation Status](https://readthedocs.org/projects/naturtag/badge/?version=latest)](https://naturtag.readthedocs.io)
[![GitHub issues](https://img.shields.io/github/issues/JWCook/naturtag)](https://github.com/JWCook/naturtag/issues)
[![PyPI](https://img.shields.io/pypi/v/naturtag?color=blue)](https://pypi.org/project/naturtag)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/naturtag)](https://pypi.org/project/naturtag)

<br />

[![](assets/naturtag-banner.png)](https://naturtag.readthedocs.io)

Naturtag is a tool for tagging local observation photos with iNaturalist taxonomy & observation metadata.
This includes a basic **command-line interface**, an experimental **graphical interface**, and can
also be used as a **python package**.

See the CLI in action here:
[![asciicast](https://asciinema.org/a/0a6gzpt7AI9QpGoq0OGMDOxqi.svg)](https://asciinema.org/a/0a6gzpt7AI9QpGoq0OGMDOxqi)

# Contents

* [Use Cases](#use-cases)
* [Development Status](#development-status)
* [Python Package](#python-package)
* [CLI](#cli)
    * [Installation](#cli-installation)
    * [Usage](#cli-usage)
    * [Data Sources](#data-sources)
    * [Images](#images)
    * [Keywords](#keywords)
    * [DarwinCore](#darwincore)
    * [Sidecar Files](#sidecar-files)
    * [Hierarchical Keywords](#hierarchical-keywords)
    * [Examples](#examples)
* [GUI](#gui)
    * [Installation](#gui-installation)
    * [Usage](#gui-usage)
    * [Image Selection and Tagging](#image-selection-and-tagging)
    * [Species Search](#species-search)
    * [Saved Species](#saved-species)
    * [Metadata](#metadata)
    * [Settings](#settings)
    * [Keyboard Shortcuts](#keyboard-shortcuts)
* [See Also](#see-also)

## Use Cases
The purpose of this is to take some of the useful information from your own iNaturalist observations
and embed it in your local photo collection.

### Metadata for local photo organization
If you like the way you can search and filter your observations on iNaturalist.org and its mobile
apps, and you wish you could do that with your local photos, naturtag can help.
It can tag your photos with **hierarchical keywords**, which can then be used in a photo viewer or
DAM such as **Lightroom**, [**FastPictureViewer**](https://www.fastpictureviewer.com), or
[**XnViewMP**](https://www.xnview.com/en/xnviewmp).

### Metadata for photo hosting
Naturtag can also simplify tagging photos for photo hosting sites like Flickr. For that use case, this
tool generates keywords in the same format as
[iNaturalist's Flickr Tagger](https://www.inaturalist.org/taxa/flickr_tagger).

### Metadata for other biodiversity tools
Finally, naturtag can improve interoperability with other tools and systems that interact with biodiversity
data. For example, in addition to iNaturalist you may submit observations of certain species to
another biodiversity observation platform with a more specific focus, such as
**eBird**, **BugGuide**, or **Mushroom Observer**. For that use case, this tool supports
[Simple Darwin Core](https://dwc.tdwg.org/simple).

# Development Status
* This is currently just a small hobby project, and still fairly unpolished.
* See [Issues](https://github.com/JWCook/naturtag/issues?q=) for planned features and current progress.
* If you have any suggestions, questions, or requests, please
  [create an issue](https://github.com/JWCook/naturtag/issues/new/choose), or ping me (**@jcook**)
  on the [iNaturalist Community Forum](https://forum.inaturalist.org/c/general/14).
* I am actively working on other libraries that naturtag will benefit from, including
  [requests-cache](https://requests-cache.readthedocs.io),
  [pyinaturalist](https://pyinaturalist.readthedocs.io), and
  [pyinaturalist-convert](https://github.com/JWCook/pyinaturalist-convert).

# Python Package
See [naturtag documentation on ReadTheDocs](https://naturtag.readthedocs.io) for details on the
python package, which lets you use most of naturtag's features in your own scripts or applications.

Generic iNaturalist data access features that aren't specific to naturtag are contributed upstream
to [pyinaturalist](https://pyinaturalist.readthedocs.io/en/stable/).

# CLI

## CLI Installation
Install the latest stable version with pip:
```bash
pip install naturtag
```

Or, if you would like to use the latest development version:
```bash
pip install --pre naturtag
```

## CLI Usage
This package provides the command `naturtag`, also aliased to `nt`.

See `naturtag --help` for full usage information. Basic options:
```yaml
Usage: naturtag [OPTIONS] [IMAGES]...

  Get taxonomy tags from an iNaturalist observation or taxon, and write them
  either to the console or to local image metadata.

Options:
  -c, --common-names      Include common names for all ranks that have them
  -d, --darwin-core       Generate Darwin Core metadata
  -f, --flickr-format     Output tags in a Flickr-compatible format
  -h, --hierarchical      Generate pipe-delimited hierarchical keywords
  -o, --observation TEXT  Observation ID or URL
  -t, --taxon TEXT        Taxon ID or URL
  -x, --create-xmp        Create XMP sidecar file if it doesn't already exist
  -v, --verbose           Show additional information
  --help                  Show this message and exit.
```

### Species & Observation IDs
Either a species or observation may be specified, either by ID or URL.
For example, all the following options will fetch the same taxonomy metadata:
```
naturtag -t 48978
naturtag -t https://www.inaturalist.org/taxa/48978-Dirona-picta
naturtag -o 45524803
naturtag -o https://www.inaturalist.org/observations/45524803
```

The difference is that specifying a species (`-t, --taxon`) will fetch only
taxonomy metadata, while specifying an observation (`-o, --observation`)
will fetch taxonomy plus observation metadata.

### Species Search
You may also search for species by name, for example `naturtag -t cardinal`.
If there are multiple results, you will be prompted to choose from the top 10 search results:

![Screenshot](assets/screenshots/cli-taxon-search.png)

### Images
Multiple paths are supported, as well as glob patterns, for example:
`0001.jpg IMG*.jpg ~/observations/**.jpg`
If no images are specified, the generated keywords will be printed.

### Keywords
Keywords will be generated in the format:
`taxonomy:{rank}={name}`

### DarwinCore
If an observation is specified, DwC metadata will also be generated, in the
form of XMP tags. Among other things, this includes taxonomy tags in the
format:
`dwc:{rank}="{name}"`

### Sidecar Files
By default, XMP tags will be written to a sidecar file if it already exists.
Use the `-x` option to create a new one if it doesn't exist.

### Hierarchical Keywords
If specified (`-h`), hierarchical keywords will be generated. These will be
interpreted as a tree structure by image viewers that support them.

For example, the following keywords:
```bash
Animalia
Animalia|Arthropoda
Animalia|Arthropoda|Chelicerata
Animalia|Arthropoda|Hexapoda
```

Will translate into the following tree structure:
```
Animalia
    ┗━Arthropoda
        ┣━Chelicerata
        ┗━Hexapoda
```

### Examples

Just generate keywords from a taxon, without writing to a file:
```ini
$ naturtag -ct 48978
Fetching taxon 48978
12 parent taxa found
22 keywords generated

taxonomy:kingdom=Animalia
taxonomy:phylum=Mollusca
taxonomy:class=Gastropoda
taxonomy:subclass=Heterobranchia
taxonomy:infraclass=Euthyneura
taxonomy:subterclass=Ringipleura
taxonomy:superorder=Nudipleura
taxonomy:order=Nudibranchia
taxonomy:suborder=Cladobranchia
taxonomy:superfamily=Proctonotoidea
taxonomy:family=Dironidae
taxonomy:genus=Dirona
"taxonomy:species=Dirona picta"
Animals
Molluscs
Gastropods
"Heterobranch Gastropods"
"Euthyneuran Gastropods"
"Nudipleuran Slugs"
Nudibranchs
"Colorful Dirona"
inaturalist:taxon_id=48978
```

Generate both keywords and DarwinCore metadata for an observation, and write to
two images and one XMP sidecar:
```
$ naturtag -co 45524803 img00001.jpg img00002.jpg
Fetching observation 45524803
Fetching taxon 48978
12 parent taxa found
23 keywords generated
Getting darwincore terms for observation 45524803
Writing 39 tags to img00001.jpg
Writing 37 tags to img00001.xmp
Writing 39 tags to img00002.jpg
No existing XMP sidecar file found for img00002.jpg; skipping
```
[See example of XMP metadata generated by this command](assets/example_45524803.xmp).

# GUI
This project also includes a graphical frontend, although it's very early in development.

## GUI Installation
My goal is to get this packaged into more convenient platform-specific builds
(a `.exe` build for Windows, for example), but for now it can take a bit of work to get the GUI
up and running. If you are interested in trying this out and you run into issues, please let me
know and I can help.

To install:
```
pip install naturtag[ui]
```
Some additional dependencies are required on Windows:
```
pip install naturtag[ui-win]
```

To launch, run:
```
python -m naturtag.ui
```

##  GUI Usage

### Image Selection and Tagging
The basic UI components are shown below:
![Screenshot](assets/screenshots/gui-image-selector.png)

1. Drag & drop images or folders into the window.
2. Or, select files via the file browser on the right
3. Enter an iNaturalist observation ID or taxon ID (iNaturalist URLs also work here)
4. Click the 'Run' button in the lower-left to tag the selected images

Other things to do:
* **Middle-click** an image to remove it
* **Right-click** an image for a context menu with more actions
* See [Metadata](#metadata) for more details

### Species Search
In the likely event that you don't already know the taxon ID, click the
'Find a Species' button to go to the taxon search screen. You can start with searching by name,
with autocompletion support:

![Screenshot](assets/screenshots/gui-taxon-search.png)

You can also run a full search using the additional filters. For example, to search for plants
and fungi with 'goose' in either the species or genus name:

![Screenshot](assets/screenshots/gui-taxon-search-results.png)

### Saved Species
The additional tabs on the taxon screen contain:
* History of recently viewed taxa
* Most frequently viewed taxa
* Starred taxa

To save a particular taxon for future reference, click the ✩ icon in the top left of its info panel,
and it will be saved in the ★ tab. These items can be re-ordered via **Right-click** -> **Move to top**.
(Unfortunately, drag-and-drop functionality is not currently possible for list items).

### Metadata
**Right-click** an image and select **Copy Flickr tags** to copy keyword tags compatible with Flickr.
![Screenshot](assets/screenshots/gui-image-context-menu.png)

Also, a very simple metadata view is included. To open it, **Right-click** an image and select
**View metadata**.

![Screenshot](assets/screenshots/gui-metadata.png)

### Settings
There are also some settings to customize the metadata that your images will be tagged with,
as well as iNaturalist info used in search filters. And yes, there is a dark mode, because
why not.

![Screenshot](assets/screenshots/gui-settings.png)

See [CLI Usage](#cli-usage) for more details on these settings.

### Keyboard Shortcuts
Some keyboard shortcuts are included for convenience:

Key(s)          | Action                    | Screen
----            |----                       |----------
Ctrl+O          | Open file chooser         | Image selection
Ctrl+V          | Paste photos or iNat URLs | Image selection
Ctrl+Enter      | Run image tagger          | Image selection
Shift+Ctrl+X    | Clear selected images     | Image selection
Ctrl+Enter      | Run taxon search          | Taxon search
Shift+Ctrl+X    | Clear search filters      | Taxon search
F11             | Toggle fullscreen         | All
Ctrl+Q          | Quit                      | All

# See Also
* For generating keyword _collections_, see the related tool
  [`taxon-keyword-gen`](https://github.com/JWCook/taxon-keyword-gen).
* This project uses [`pyinaturalist`](https://github.com/niconoe/pyinaturalist), a python API
  client for iNaturalist. Refer to that project for more data access tools.
