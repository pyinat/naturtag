#!/usr/bin/env bash
# Export a subset of SQLite taxon + FTS db into an archive to include in application package

# TODO: CSV compresses a lot better than SQLite. It might be better to package compressed CSV,
# and create and load tables on initial startup

DATA_DIR=$HOME/.local/share/pyinaturalist/
SRC_DB=$DATA_DIR/observations.db
DEST_DB=observations.db
TAXON_CSV=taxon.csv
TAXON_FTS_CSV=taxon_fts.csv
ARCHIVE=assets/taxonomy.tar.gz

echo 'Exporting FTS table...'
sqlite3 -header -csv $SRC_DB \
    "SELECT * \
     FROM taxon_fts \
     WHERE language_code='en' AND count_rank > 1 \
     ;" \
    > $TAXON_FTS_CSV

echo 'Importing FTS table...'
python -c "\
from pyinaturalist_convert.fts import create_fts5_table;\
create_fts5_table('$DEST_DB')"
sqlite3 --csv $DEST_DB ".import $TAXON_FTS_CSV taxon_fts"
sqlite3 $DEST_DB "ANALYZE taxon_fts;"

# TODO: Could export only some specific columns, but then .import command couldn't be used
# SELECT id, ancestor_ids, child_ids, iconic_taxon_id, leaf_taxa_count, observations_count, name, parent_id, preferred_common_name, rank
echo 'Exporting Taxon table...'
sqlite3 -header -csv $SRC_DB \
    "SELECT * FROM taxon \
     WHERE observations_count >= 10 \
     ;" \
    > $TAXON_CSV

echo 'Importing Taxon table...'
python -c "\
from pyinaturalist_convert.db import DbTaxon, create_table;\
create_table(DbTaxon, '$DEST_DB')"
sqlite3 --csv $DEST_DB ".import $TAXON_CSV taxon"
sqlite3 $DEST_DB "ANALYZE taxon;"

echo 'Compressing...'
tar -I 'gzip -9' -cvf $ARCHIVE $TAXON_CSV $TAXON_FTS_CSV
# tar -I 'gzip -9' -cvf $ARCHIVE $DEST_DB
# rm $TAXON_CSV $TAXON_FTS_CSV $DEST_DB
