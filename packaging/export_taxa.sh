#!/usr/bin/env bash
# Export a SQLite taxon + FTS db in two versions:
#   * A minimal English-only subset to include in application package
#   * Full taxonomy data including common names for all languages

DATA_DIR=$HOME/.local/share/pyinaturalist/
SRC_DB=$DATA_DIR/observations.db
TAXON_CSV=taxon.csv
TAXON_FTS_CSV=taxon_fts.csv
MIN_ARCHIVE=assets/data/taxonomy.tar.gz
MIN_OBSERVATIONS=20  # Only export taxa with at least this many RG observations
FULL_DEST_DB=naturtag.db
FULL_ARCHIVE=taxonomy_full.tar.gz

# Minified taxonomy
# ----------------------------------------

echo 'Exporting Taxon table (minified)...'
sqlite3 -header -csv $SRC_DB \
    "SELECT id, ancestor_ids, child_ids, iconic_taxon_id, leaf_taxa_count, \
     observations_count_rg, name, parent_id, preferred_common_name, rank \
     FROM taxon \
     WHERE observations_count_rg >= $MIN_OBSERVATIONS \
     ;" \
    > $TAXON_CSV

echo 'Exporting FTS table (minified)...'
sqlite3 -header -csv $SRC_DB \
    "SELECT * \
     FROM taxon_fts \
     WHERE language_code='en' AND count_rank > 1 \
     ;" \
    > $TAXON_FTS_CSV

echo 'Compressing...'
tar -I 'gzip -9' -cvf $MIN_ARCHIVE $TAXON_CSV $TAXON_FTS_CSV
rm -v $TAXON_CSV $TAXON_FTS_CSV

# Full taxonomy
# ----------------------------------------

echo 'Exporting Taxon table (full)...'
sqlite3 -header -csv $SRC_DB \
    "SELECT * FROM taxon;" \
    > $TAXON_CSV

echo 'Exporting FTS table (full)...'
sqlite3 -header -csv $SRC_DB \
    "SELECT * FROM taxon_fts;" \
    > $TAXON_FTS_CSV

echo 'Importing Taxon table...'
python -c "\
from pyinaturalist_convert.db import DbTaxon, create_table;\
create_table(DbTaxon, '$FULL_DEST_DB')"
sqlite3 --csv $FULL_DEST_DB ".import $TAXON_CSV taxon"

echo 'Importing FTS table...'
python -c "\
from pyinaturalist_convert.fts import create_taxon_fts_table;\
create_taxon_fts_table('$FULL_DEST_DB')"
sqlite3 --csv $FULL_DEST_DB ".import $TAXON_FTS_CSV taxon_fts"

echo 'Optimizing tables...'
sqlite3 $FULL_DEST_DB "ANALYZE taxon;"
sqlite3 $FULL_DEST_DB "ANALYZE taxon_fts;"
sqlite3 $FULL_DEST_DB "VACUUM;"

echo 'Compressing...'
tar -I 'gzip -9' -cvf $FULL_ARCHIVE $FULL_DEST_DB
rm -v $TAXON_CSV $TAXON_FTS_CSV $FULL_DEST_DB
