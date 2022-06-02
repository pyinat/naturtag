# Naturtag

[![Build status](https://github.com/JWCook/naturtag/workflows/Build/badge.svg)](https://github.com/JWCook/naturtag/actions)
[![Documentation Status](https://readthedocs.org/projects/naturtag/badge/?version=latest)](https://naturtag.readthedocs.io)
[![GitHub issues](https://img.shields.io/github/issues/JWCook/naturtag)](https://github.com/JWCook/naturtag/issues)
[![PyPI](https://img.shields.io/pypi/v/naturtag?color=blue)](https://pypi.org/project/naturtag)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/naturtag)](https://pypi.org/project/naturtag)


<!-- RTD-IGNORE -->
<br />

[![](assets/naturtag-banner.png)](https://naturtag.readthedocs.io)

## Contents
- [Summary](#summary)
- [Use Cases](#use-cases)
- [Installation](#installation)
- [Usage](#usage)
  - [GUI](#gui)
  - [CLI](#cli)
  - [Library](#library)
- [Development Status](#development-status)
<!-- END-RTD-IGNORE -->

## Summary
Naturtag is a tool for tagging image files with iNaturalist taxonomy & observation metadata.
This includes a basic **command-line interface**, a work-in-progress **desktop application**,
and can also be used as a **python library**.

## Use Cases
Naturtag takes useful information from your own iNaturalist observations and embeds it in your local
photo collection, mainly using [XMP](https://en.wikipedia.org/wiki/Extensible_Metadata_Platform) and
[EXIF](https://en.wikipedia.org/wiki/Exif) metadata. This has a variety of uses, including:

### Local photo organization
If you like the way you can search and filter your observations on iNaturalist.org and its mobile
apps, and you wish you could do that with your local photos, naturtag can help.
It can tag your photos with **hierarchical keywords**, which can then be used in a photo viewer or
DAM such as [**Lightroom**](https://millennialdiyer.com/articles/photography/lightroom-keyword-hierarchy/), [**FastPictureViewer**](https://www.fastpictureviewer.com), or
[**XnViewMP**](https://www.xnview.com/en/xnviewmp).

### Photo hosting
Naturtag can also simplify tagging photos for photo hosting sites like Flickr. For that use case, this
tool generates keywords in the same format as
[iNaturalist's Flickr Tagger](https://www.inaturalist.org/taxa/flickr_tagger).

### Other biodiversity tools
Finally, naturtag can improve interoperability with other tools and systems that interact with biodiversity
data. For example, in addition to iNaturalist you might submit some observations to another
platform with a more specific focus, such as **eBird**, **BugGuide**, or **Mushroom Observer**.
For that use case, this tool supports [Simple Darwin Core](https://dwc.tdwg.org/simple).

## Installation
* First, [install python 3.10](https://www.python.org/downloads/) if you don't have it yet.
* It's recommended to install into a [virtual environment](https://docs.python.org/3/library/venv.html).
* Then, install with pip:
```bash
pip install naturtag
```

## Usage

### GUI
The main interface for this project is still a work in progress. Soon this will be packaged into
more convenient platform-specific builds, but for now it must be installed and launched from the
command line.

To launch, run:
```
python -m naturtag.app.app
```

It includes an interface for selecting and tagging images:

![Screenshot](assets/screenshots/image-selector.png)

And tools to search and browse species to tag your images with:

![Screenshot](assets/screenshots/taxon-search.png)

See [GUI documentation](https://naturtag.readthedocs.io/en/latest/gui.html) for more details.

### CLI
Naturtag also includes a command-line interface. It takes an observation or species, plus some image
files, and generates EXIF and XMP metadata to write to those images. You can see it in action here:
[![asciicast](https://asciinema.org/a/0a6gzpt7AI9QpGoq0OGMDOxqi.svg)](https://asciinema.org/a/0a6gzpt7AI9QpGoq0OGMDOxqi)

See [CLI documentation](https://naturtag.readthedocs.io/en/latest/cli.html) for more details.

### Library
You can also import `naturtag` as a python library, and use its main features in your own scripts or
applications. Basic examples:
```python
from naturtag import tag_images, refresh_tags

# Tag images with full observation metadata
tag_images(['img1.jpg', 'img2.jpg'], observation_id=1234)

# Tag images with taxonomy metadata only
tag_images(['img1.jpg', 'img2.jpg'], taxon_id=1234)

# Glob patterns are also supported
tag_images(['~/observations/*.jpg'], taxon_id=1234)

# Refresh previously tagged images with latest observation and taxonomy metadata
refresh_tags(['~/observations/'], recursive=True)
```

See [API Reference](https://naturtag.readthedocs.io/en/latest/reference.html) for more details.


## Development Status
* See [Issues](https://github.com/JWCook/naturtag/issues?q=) for planned features and current progress.
* If you have any suggestions, questions, or requests, please
  [create an issue](https://github.com/JWCook/naturtag/issues/new/choose), or ping me (**@jcook**)
  on the [iNaturalist Community Forum](https://forum.inaturalist.org/c/general/14).
* When I'm not working on this, I'm usually working on other libraries that naturtag benefits from, including
  [requests-cache](https://requests-cache.readthedocs.io),
  [pyinaturalist](https://pyinaturalist.readthedocs.io), and
  [pyinaturalist-convert](https://github.com/JWCook/pyinaturalist-convert).
