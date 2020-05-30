""" Basic utilities for reading and writing settings from config files """
from collections import Counter, OrderedDict
from logging import getLogger
from os import makedirs
from os.path import isfile
from shutil import copyfile
from typing import Tuple, List, Dict, Any

import json
import yaml

from naturtag.constants import (
    DATA_DIR,
    CONFIG_PATH,
    DEFAULT_CONFIG_PATH,
    TAXON_HISTORY_PATH,
    TAXON_FREQUENCY_PATH,
    STARRED_TAXA_PATH,
)

logger = getLogger().getChild(__name__)


def read_settings() ->  Dict[str, Any]:
    """  Read settings from the settings file

    Returns:
        Stored config state
    """
    if not isfile(CONFIG_PATH):
        reset_defaults()
    logger.info(f'Reading settings from {CONFIG_PATH}')
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def write_settings(new_config: Dict[str, Any]):
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
def read_stored_taxa() -> Tuple[List[int], List[int], Dict[int, int]]:
    """ Read taxon view history, starred, and frequency

    Returns:
        Stored taxon view history, starred, and frequency
    """
    return (
        read_int_list_file(TAXON_HISTORY_PATH),
        read_int_list_file(STARRED_TAXA_PATH),
        read_int_dict_file(TAXON_FREQUENCY_PATH),
    )


def write_stored_taxa(history: List[int], starred: List[int]):
    """ Write taxon view history to file, along with stats on most frequently viewed taxa

    Args:
        Complete taxon history (including previously stored history)
    """
    logger.info(f'Writing taxon view history ({len(history)} items)')
    with open(TAXON_HISTORY_PATH, 'w') as f:
        f.write('\n'.join(map(str, history)))

    logger.info(f'Writing starred taxa ({len(starred)} items)')
    with open(STARRED_TAXA_PATH, 'w') as f:
        f.write('\n'.join(map(str, set(starred))))

    logger.info('Writing taxon view frequency')
    with open(TAXON_FREQUENCY_PATH, 'w') as f:
        counter = OrderedDict(Counter(history).most_common())
        json.dump(counter, f, indent=4)


def read_int_list_file(path) -> List[int]:
    """ Load a plaintext file containing a list of ints, and skip any invalid (non-int) values """
    if not isfile(STARRED_TAXA_PATH):
        return []
    with open(path) as f:
        lines = (line.strip() for line in f.readlines())
        return [int(line) for line in lines if line and _is_int(line)]


def read_int_dict_file(path) -> Dict[int, int]:
    """ Load a JSON file containing a mapping of int keys and values """
    if not isfile(path):
        return {}
    else:
        with open(path) as f:
            int_dict = json.load(f)
            return {int(k): int(v) for k, v in int_dict.items() if _is_int(k) and _is_int(v)}


def _is_int(value):
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return False
