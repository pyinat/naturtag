# Controlled Vocabulary Taxonomy Generator

Utilities for working with taxonomy data.

Initial use case: Generate hierarchical keywords from taxonomy data in order to classify
observation photos with controlled vocabulary ITPC + XMP tags.
This is currently just a proof of concept intended for biological taxonomy, but could possibly be
applied to other forms of hierarchical classification.

This repo contains working scripts to generate taxonomic trees (in JSON format)
from the following sources:
* [iNaturalist observations](https://www.inaturalist.org/observations/export)
* [NCBI taxonomy](https://www.ncbi.nlm.nih.gov/guide/taxonomy/)

## Installation

This is not currently published onpypi.
```
git clone git@github.com:JWCook/cv-taxonomy-gen.git && cd cv-taxonomy-gen
pip install .
```

## Usage

### iNaturalist

First, run an [iNaturalist observation query](https://www.inaturalist.org/observations/export),
save the output to `taxonomy_data/observations.csv`, then run:
```
./inat_export.py
```

### NCBI

Simply run:
```
./ncbi_export.py
```

![Screenshot](screenshot.png?raw=true)

This will either download the NCBI taxonomic dump files from the FTP site, or reuse them if they've
already been downloaded.

By default, only eukaryotic cellular organisms will be exported, but if you really want to organize
all your photos of viruses or bacteria, you can do that too, I guess.

## Output 

Tags follow the format `taxonomy:<rank>=<taxon>`.
For example, a complete set of tags for the common fruit fly would look like:
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
* Integrate with iNaturalist API to query and download observation data
* Conveniences to make it easier to import generated keywords into popular photo/metadata editing
  applications that support hierarchical keywords (XnViewMP, Lightroom, Daminion, etc.)
* Make import & export parameters configurable via config file and/or CLI parameters
* Unit tests, make the code a bit more presentable, etc.
