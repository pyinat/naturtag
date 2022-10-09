#!/usr/bin/env bash
# Export a subset of SQLite taxon + FTS db into an archive to include in application package

DATA_DIR=$HOME/.local/share/pyinaturalist/
SRC_DB=$DATA_DIR/observations.db
TAXON_CSV=taxon.csv
TAXON_FTS_CSV=taxon_fts.csv
ARCHIVE=assets/taxonomy.tar.gz

echo 'Exporting Taxon table...'
sqlite3 -header -csv $SRC_DB \
    "SELECT id, ancestor_ids, child_ids, iconic_taxon_id, leaf_taxa_count, observations_count, name, parent_id, preferred_common_name, rank FROM taxon \
     WHERE observations_count >= 10 \
     ;" \
    > $TAXON_CSV

echo 'Exporting FTS table...'
sqlite3 -header -csv $SRC_DB \
    "SELECT * \
     FROM taxon_fts \
     WHERE language_code='en' AND count_rank > 1 \
     ;" \
    > $TAXON_FTS_CSV

echo 'Compressing...'
tar -I 'gzip -9' -cvf $ARCHIVE $TAXON_CSV $TAXON_FTS_CSV
rm -v $TAXON_CSV $TAXON_FTS_CSV
