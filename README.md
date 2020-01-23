# Taxonomy Keyword Generator

Tools to produce keyword collections based on taxonomy data.

Initial use case: Generate hierarchical keywords from taxonomy data in order to classify
observation photos with a controlled vocabulary for ITPC + XMP metadata.
This is currently a simple proof of concept intended for biological taxonomy, but could possibly
be applied to other forms of hierarchical classification.

This repo contains working scripts to generate taxonomic trees (in JSON format)
from the following sources:
* [iNaturalist observations](https://www.inaturalist.org/observations/export)
* [NCBI taxonomy](https://www.ncbi.nlm.nih.gov/guide/taxonomy/)

## Installation

```
git clone git@github.com:JWCook/taxon-keyword-gen.git && cd taxon-keyword-gen
pip install .
```

## Usage

### iNaturalist

**Use case:** You want hierarchical keywords for just the taxa you have personally observed on
iNaturalist (or based on some other queryable criteria).

First, run an [iNaturalist observation query](https://www.inaturalist.org/observations/export),
save the output to `taxonomy_data/observations.csv`, then run:
```
taxgen-inat
```

### NCBI

**Use case:** You want hierarchical keywords for all of the things

Simply run:
```
taxgen-ncbi
```

![Screenshot](screenshot.png?raw=true)

This will either download the NCBI taxonomic dump files from the FTP site, or reuse them if they've
already been downloaded.

By default, only eukaryotic cellular organisms will be exported, but if you really want to organize
all your photos of viruses or bacteria, you can do that too, I guess.

## Output 

Keywords follow the format `taxonomy:<rank>=<taxon>`.
For example, a complete set of keywords for the common fruit fly would look like:
```
taxonomy:kingdom=Animalia
  taxonomy:phylum=Arthropoda
    taxonomy:subphylum=Hexapoda
      taxonomy:class=Insecta
        taxonomy:order=Diptera
          taxonomy:suborder=Brachycera
            taxonomy:superfamily=Ephydroidea
              taxonomy:family=Drosophilidae
                taxonomy:subfamily=Drosophilinae
                  taxonomy:genus=Drosophila
                    taxonomy:subgenus=Sophophora
                      taxonomy:species=melanogaster
                        "taxonomy:binomial=Drosophila melanogaster"
                          "taxonomy:common=Common Fruit Fly"
```

## TODO

If this actually turns out to be useful, there is lots of room for building on top of this basic
PoC, for example:
* Integrate with iNaturalist API to query and download observation data based on search criteria
* Add features for writing taxonomic info to XMP metadata
* Conveniences to make it easier to import generated keywords into popular photo/metadata editing
  applications that support hierarchical keywords (XnView MP, FastPictureiewer, Lightroom, Daminion, etc.)
    * Add support for FPV keyword synonyms (common name <--> scientific name)
* Make import & export parameters configurable via config file and/or CLI parameters
* Add configurable taxon whitelist/blacklist
* Unit tests, make the code a bit more presentable, etc.
