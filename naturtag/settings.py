""" Basic utilities for reading and writing settings from YAML config """
from logging import getLogger
from os import makedirs
from os.path import isfile
from shutil import copyfile
import yaml
from naturtag.constants import DATA_DIR, CONFIG_PATH, DEFAULT_CONFIG_PATH

logger = getLogger().getChild(__name__)


def read_settings():
    """
    Read settings from the settings file

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
