(cli)=
# {fa}`terminal` CLI
This page describes how to use the Naturtag CLI.

The basic tagging features of naturtag can be used via the command `naturtag`, also aliased to `nt`.
It takes an observation or species, plus some image files, and generates EXIF and XMP metadata to
write to those images. You can see it in action here:
[![asciicast](https://asciinema.org/a/0a6gzpt7AI9QpGoq0OGMDOxqi.svg)](https://asciinema.org/a/0a6gzpt7AI9QpGoq0OGMDOxqi)

## CLI Options

See `naturtag --help` for full usage information. Options:
```yaml
Usage: naturtag [OPTIONS] [IMAGES]...

  Get taxonomy tags from an iNaturalist observation or taxon, and write them
  either to the console or to local image metadata.

Options:
  -f, --flickr-format     Output tags in a Flickr-compatible format
  -o, --observation TEXT  Observation ID or URL
  -t, --taxon TEXT        Taxon ID or URL
  -p, --print             Print existing tags for previously tagged images
  -r, --refresh           Refresh metadata for previously tagged images
  -r, --recursive         Recursively scan subdirectories
  -v, --verbose           Show additional information
  --help                  Show this message and exit.
```

## Metadata Options
Some additional options are available to change which metadata formats to use.
The CLI will use the same {ref}`app-settings` as the app, if available.

You can also directly edit the config file at `settings.yml` in the naturtag data directory. The
location varies by platform, and you can get this info from `naturtag --version`.

## Species & Observation IDs
Either a species or observation may be specified, either by ID or URL.
For example, all the following options will fetch the same taxonomy metadata:
```
naturtag -t 48978
naturtag -t https://www.inaturalist.org/taxa/48978-Dirona-picta
naturtag -o 45524803
naturtag -o https://www.inaturalist.org/observations/45524803
```

The difference is that specifying a species (`-t` / `--taxon`) will fetch only
taxonomy metadata, while specifying an observation (`-o` / `--observation`)
will fetch taxonomy plus observation metadata.

## Species Search
You may also search for species by name, for example `naturtag -t cardinal`.
If there are multiple results, you will be prompted to choose from the top 10 search results:
![Screenshot](../assets/screenshots/cli-taxon-search.png)

## Images
You can provide multiple paths or glob patterns, for example:
```
naturtag -t 48978 2022-01-01.jpg IMG*.jpg
```

Or you can provide a directory containing images. To also scan subdirectories, use
`-r` / `--recursive`:
```
naturtag -t 48978 -r ~/observations
```

### Examples
Just generate keywords from a taxon, without writing to a file:
```ini
$ naturtag -c -t 48978
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

Generate tags for an observation, and write to two images and one sidecar file:
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

See {ref}`metadata` for more details on the metadata than naturtag generates.
