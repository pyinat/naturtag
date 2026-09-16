#!/usr/bin/env python
# Download, convert, and aggregate taxonomy data from iNat DwC-A export
from pyinaturalist_convert import (
    aggregate_taxon_db,
    enable_logging,
    load_dwca_tables,
    load_fts_taxa,
    vacuum_analyze,
)

enable_logging('DEBUG')
load_dwca_tables()
df = aggregate_taxon_db()
vacuum_analyze(['observation', 'taxon'], show_spinner=True, fast=True)
load_fts_taxa(languages='all')
