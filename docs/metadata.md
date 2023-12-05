<!-- TODO: This is just a rough draft. Needs more details and editing. -->

(metadata)=
# {fa}`code` Metadata
This page describes the formats and types of metadata that naturtag generates.

## Metadata formats
```{note}
By default, naturtag writes to all of the formats described below.
If needed, you can change this behavior in {ref}`app-settings`.
```

### Embedded formats
Naturtag supports the following metadata formats (embedded in the original image file):
* [EXIF](https://exiftool.org/TagNames/EXIF.html)
* [IPTC](https://exiftool.org/TagNames/IPTC.html)
* [XMP](https://exiftool.org/TagNames/XMP.html)

Each of these formats have different capabilities, and different tools that are compatible with
them. Depending on which applications or websites you use for viewing/managing/hosting photos, you
may want to enable some of these formats but not others.

```{warning}
After using naturtag, you can manually edit your image metadata using any other tool, but it's not
recommended to use multiple tools to edit metadata for the same file, if it contains multiple
metadata formats.

For example, some tools may use EXIF only, while others may use a combination of EXIF and XMP.
```

### Sidecar files
A sidecar file can be saved alongside a photo that contains all XMP metadata.
This has the advantage of non-destructive edits (not needing to modify the original image file),
and also lets you associate the metadata with a RAW image file.

The sidecar will have the same filename as the image, but with a `.xmp` extension. For example:
```bash
2022_01_01_02_52_13_polistes_rubiginosus.jpg
2022_01_01_02_52_13_polistes_rubiginosus.raw
2022_01_01_02_52_13_polistes_rubiginosus.xmp
```

```{note}
Many (but not all) photo viewers and managers support sidecar files.
If you want to use _only_ sidecar files, first check whether your other tools support them.
```

## Metadata types
Naturtag generates the following types of metadata:

### Basic Keywords
These are basic keywords for both scientific and common names.

For example:
```
Animalia
Arthropoda
Arachnida
...
Animals
Arthropods
Spiders
...
```

### Structured Keywords
These are keywords will in the format: `taxonomy:{rank}={name}`

For example:
```ini
taxonomy:kingdom=Animalia
taxonomy:phylum=Arthropoda
taxonomy:subphylum=Hexapoda
taxonomy:class=Insecta
taxonomy:subclass=Pterygota
taxonomy:order=Hymenoptera
taxonomy:suborder=Apocrita
taxonomy:infraorder=Aculeata
taxonomy:superfamily=Vespoidea
taxonomy:family=Vespidae
taxonomy:subfamily=Polistinae
taxonomy:tribe=Polistini
taxonomy:genus=Polistes
taxonomy:subgenus=Fuscopolistes
taxonomy:species=Polistes rubiginosus
```


### Hierarchical Keywords
Hierarchical keywords are interpreted as a tree structure by tools that support them.

For example, the following keywords:
```
Animalia
Animalia|Arthropoda
Animalia|Arthropoda|Chelicerata
Animalia|Arthropoda|Hexapoda
```

Will translate into a tree structure that looks like:
```
Animalia
    ┗━Arthropoda
        ┣━Chelicerata
        ┗━Hexapoda
```

### Darwin Core
[Darwin Core](https://dwc.tdwg.org/terms/) (DwC) is an exchange format commonly used to transfer
observation data between different biodiversity systems (like [GBIF](https://www.gbif.org)).

There is also an [XMP namespace](https://www.exiftool.org/TagNames/DarwinCore.html) which enables
this information to be stored in image metadata. Naturtag can use this to save all relevant information about an iNaturalist observation, in addition to taxonomy.

```{note}
See the `.xmp` files in the [demo_images](https://github.com/pyinat/naturtag/tree/main/assets/demo_images) folder for some examples.
```
