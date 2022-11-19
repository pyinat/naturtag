#!/usr/bin/env bash
# Export all taxonomy data into a SQLite db, including common name text search for all languages
# This is too large to include in naturtag packages, but can be uploaded to GitHub Releases as an
# optional download

DATA_DIR=$HOME/.local/share/pyinaturalist/
SRC_DB=$DATA_DIR/observations.db
DEST_DB=naturtag.db
TAXON_CSV=taxon.csv
TAXON_FTS_CSV=taxon_fts.csv
ARCHIVE=taxonomy_all_languages.tar.gz

echo 'Exporting Taxon table...'
sqlite3 -header -csv $SRC_DB \
    "SELECT * FROM taxon;" \
    > $TAXON_CSV

echo 'Exporting FTS table...'
sqlite3 -header -csv $SRC_DB \
    "SELECT * FROM taxon_fts;" \
    > $TAXON_FTS_CSV

echo 'Importing Taxon table...'
python -c "\
from pyinaturalist_convert.db import DbTaxon, create_table;\
create_table(DbTaxon, '$DEST_DB')"
sqlite3 --csv $DEST_DB ".import $TAXON_CSV taxon"

echo 'Importing FTS table...'
python -c "\
from pyinaturalist_convert.fts import create_taxon_fts_table;\
create_taxon_fts_table('$DEST_DB')"
sqlite3 --csv $DEST_DB ".import $TAXON_FTS_CSV taxon_fts"

echo 'Optimizing tables...'
sqlite3 $DEST_DB "ANALYZE taxon;"
sqlite3 $DEST_DB "ANALYZE taxon_fts;"
sqlite3 $DEST_DB "VACUUM;"

echo 'Compressing...'
tar -I 'gzip -9' -cvf $ARCHIVE $DEST_DB
rm -v $TAXON_CSV $TAXON_FTS_CSV $DEST_DB
