#!/usr/bin/env bash
# Import previously exported taxonomy data into a SQLite db
# Currently unused; for reference only

DATA_DIR=$HOME/.local/share/pyinaturalist/
DEST_DB=observations.db
TAXON_CSV=taxon.csv
TAXON_FTS_CSV=taxon_fts.csv

echo 'Importing FTS table...'
python -c "\
from pyinaturalist_convert.fts import create_fts5_table;\
create_fts5_table('$DEST_DB')"
sqlite3 --csv $DEST_DB ".import $TAXON_FTS_CSV taxon_fts"
sqlite3 $DEST_DB "ANALYZE taxon_fts;"

echo 'Importing Taxon table...'
python -c "\
from pyinaturalist_convert.db import DbTaxon, create_table;\
create_table(DbTaxon, '$DEST_DB')"
sqlite3 --csv $DEST_DB ".import $TAXON_CSV taxon"
sqlite3 $DEST_DB "ANALYZE taxon;"
