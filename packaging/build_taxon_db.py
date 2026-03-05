#!/usr/bin/env python
from pyinaturalist_convert import (
    aggregate_taxon_db,
    enable_logging,
    load_dwca_tables,
    load_fts_taxa,
)

enable_logging('DEBUG')
load_dwca_tables()
df = aggregate_taxon_db()
load_fts_taxa(languages='all')
