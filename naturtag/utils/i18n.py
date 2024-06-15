"""Internationalization utilities"""

import json
import sqlite3
from logging import getLogger

from naturtag.constants import DB_PATH, LOCALES_PATH, PathOrStr

logger = getLogger(__name__)


def get_locales(db_path: PathOrStr = DB_PATH) -> dict[str, str]:
    """Get all locale codes represented in the FTS table and their localised names"""
    from babel import Locale, UnknownLocaleError

    with sqlite3.connect(db_path) as conn:
        results = conn.execute('SELECT DISTINCT(language_code) from taxon_fts').fetchall()
        locales = sorted([r[0] for r in results if r[0]])

    locale_dict = {}
    for locale in locales:
        try:
            locale_dict[locale] = Locale.parse(locale.replace('-', '_')).display_name
        except UnknownLocaleError as e:
            logger.warning(e)

    locale_dict.pop('und')  # "Undefined"; seems to be a mix of languages
    return locale_dict


def write_locales(db_path: PathOrStr = DB_PATH):
    locale_dict = get_locales(db_path)
    with open(LOCALES_PATH, 'w') as f:
        f.write(json.dumps(locale_dict))


def read_locales() -> dict[str, str]:
    try:
        with open(LOCALES_PATH) as f:
            return json.loads(f.read())
    except IOError as e:
        logger.warning(e)
        return {'en': 'English'}
