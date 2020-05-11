from os.path import dirname

PKG_DIR = dirname(dirname(__file__))

# Specific XML namespaces to use terms from when processing DwC observation records
# Note: exiv2 will automatically add recognized namespaces when adding properties
DWC_NAMESPACES = {
    "dcterms": "http://purl.org/dc/terms/",
    "dwc": "http://rs.tdwg.org/dwc/terms/",
}

# Basic DwC fields that can be added for a taxon without an observation
MINIMAL_DWC_TERMS = [
    'dwc:kingdom',
    'dwc:phylum',
    'dwc:class',
    'dwc:order',
    'dwc:family',
    'dwc:genus',
    'dwc:species',
    'dwc:scientificName',
    'dwc:taxonRank',
    'dwc:taxonID',
]
