# {fa}`list` API Reference
This section documents all the modules included in naturtag. Many of these are internal modules,
and likely only relevant if you are interested in contributing to naturtag.

## Main entry points
To use some of the features of naturtag in your own code, the following functions and classes are
the main entry points:

```{eval-rst}
.. currentmodule:: naturtag.metadata.inat_metadata
.. autosummary::
    :nosignatures:

    tag_images
    refresh_tags
```
```{eval-rst}
.. currentmodule:: naturtag.metadata.meta_metadata
.. autosummary::
    :nosignatures:

    MetaMetadata
```

### Examples
Some basic examples:

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

## All Modules
```{toctree}
:maxdepth: 1

modules/naturtag.app
modules/naturtag.controllers
modules/naturtag.metadata
modules/naturtag.widgets

modules/naturtag.cli
modules/naturtag.client
modules/naturtag.settings
modules/naturtag.utils.image_glob
modules/naturtag.utils.thumbnails
```
