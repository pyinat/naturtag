""" Basic utilities for reading and writing settings from config files """
from collections import Counter
from logging import getLogger
from os import makedirs
from os.path import isfile
from shutil import copyfile

import json
import yaml

from naturtag.constants import (
    DATA_DIR,
    CONFIG_PATH,
    DEFAULT_CONFIG_PATH,
    TAXON_HISTORY_PATH,
    TAXON_FREQUENCY_PATH,
)

logger = getLogger().getChild(__name__)


def read_settings():
    """  Read settings from the settings file

    Returns:
        dict: Stored config state
    """
    if not isfile(CONFIG_PATH):
        reset_defaults()
    logger.info(f'Reading settings to {CONFIG_PATH}')
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def write_settings(new_config):
    """  Write updated settings to the settings file

    Args:
        new_config (dict): Updated config state
    """
    # First re-read current config, in case it changed on disk (manual edits)
    # And update on a per-section basis so we don't overwrite with an empty section
    settings = read_settings()
    logger.info(f'Writing settings to {CONFIG_PATH}')
    for k, v in new_config.items():
        settings[k].update(v)

    with open(CONFIG_PATH, 'w') as f:
        yaml.safe_dump(settings, f)


def reset_defaults():
    """ Reset settings to defaults """
    logger.info(f'Resetting {CONFIG_PATH} to defaults')
    makedirs(DATA_DIR, exist_ok=True)
    copyfile(DEFAULT_CONFIG_PATH, CONFIG_PATH)


# TODO: Is there a better file format for taxon history than just a plain text file? JSON list? sqlite?
# TODO: Separately store loaded history, new history for session; only write (append) new history
def read_taxon_history():
    """ Read taxon view history and frequency

    Returns:
        ``list, dict``: Stored taxon history as a sequence of ints, and taxon frequecy dict
    """
    # Load history, and skip any invalid (non-int) values
    if not isfile(TAXON_HISTORY_PATH):
        history = []
    else:
        with open(TAXON_HISTORY_PATH) as f:
            lines = (line.strip() for line in f.readlines())
            history = [int(line) for line in lines if line and _is_int(line)]

    # Load frequency, and skip any invalid (non-int) keys and values
    if not isfile(TAXON_FREQUENCY_PATH):
        frequency = {}
    else:
        with open(TAXON_FREQUENCY_PATH) as f:
            frequency = json.load(f)
            frequency = {int(k): int(v) for k, v in frequency.items() if _is_int(k) and _is_int(v)}

    return history, frequency


def write_taxon_history(history):
    """ Write taxon view history to file, along with stats on most frequently viewed taxa

    Args:
        history: Complete taxon history (including previously stored history)
    """
    logger.info(f'Writing taxon view history ({len(history)} items)')
    with open(TAXON_HISTORY_PATH, 'w') as f:
        f.write('\n'.join(map(str, history)))

    from collections import OrderedDict
    logger.info('Writing taxon view frequency')
    with open(TAXON_FREQUENCY_PATH, 'w') as f:
        counter = OrderedDict(Counter(history).most_common())
        json.dump(counter, f, indent=4)


def _is_int(value):
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return False
