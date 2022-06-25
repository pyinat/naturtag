#!/usr/bin/env bash
# Export a subset of a SQLite FTS db to a separate file

DATA_DIR=$HOME/.local/share/pyinaturalist/
SRC_DB=$DATA_DIR/observations.db
TMP_DB=observations.db
TMP_CSV=fts.csv
ARCHIVE=assets/taxon-fts-en.tar.gz

echo 'Exporting...'
sqlite3 -header -csv $SRC_DB \
    "SELECT name, taxon_id, taxon_rank, count_rank, language_code \
     FROM taxon_fts \
     WHERE language_code='en' AND count_rank > 1 \
     ;" \
    > $TMP_CSV

echo 'Importing...'
sqlite3 $TMP_DB \
    "CREATE VIRTUAL TABLE taxon_fts USING \
     fts5(name, taxon_id, taxon_rank UNINDEXED, count_rank UNINDEXED, language_code, \
     prefix=2, prefix=3, prefix=4)"
sqlite3 -csv $TMP_DB ".import $TMP_CSV taxon_fts"
sqlite3 $TMP_DB "ANALYZE taxon_fts;"


echo 'Compressing...'
tar -I 'gzip -9' -cvf $ARCHIVE $TMP_DB
rm $TMP_CSV $TMP_DB
