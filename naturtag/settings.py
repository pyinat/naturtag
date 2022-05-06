""" Basic utilities for reading and writing settings from config files """
import json
from collections import Counter, OrderedDict
from logging import getLogger
from pathlib import Path

import yaml
from attr import define, field
from cattr import Converter
from cattr.preconf import pyyaml

from naturtag.constants import CONFIG_PATH, STORED_TAXA_PATH
from naturtag.validation import convert_int_dict

logger = getLogger().getChild(__name__)


def make_converter() -> Converter:
    converter = pyyaml.make_converter()
    converter.register_unstructure_hook(Path, str)
    converter.register_structure_hook(Path, lambda obj, cls: Path(obj))
    return converter


YamlConverter = make_converter()


@define
class Settings:
    # Display
    dark_mode: bool = field(default=False)
    # TODO:
    # md_primary_palette: str = field(default='Teal')
    # md_accent_palette: str = field(default='Cyan')

    # iNaturalist
    casual_observations: bool = field(default=True)
    locale: str = field(default='en_US')
    preferred_place_id: int = field(default=1)
    username: str = field(default='')

    # Metadata
    common_names: bool = field(default=True)
    create_xmp: bool = field(default=True)
    darwin_core: bool = field(default=True)
    hierarchical_keywords: bool = field(default=False)

    # Photos
    default_dir: Path = field(default=Path('~').expanduser(), converter=Path)
    # TODO:
    # data_dir: Path = field(default=DATA_DIR, converter=Path)
    # favorite_dirs: list[Path] = field(factory=list)

    @classmethod
    def read(cls) -> 'Settings':
        """Read settings from config file"""
        if not CONFIG_PATH.is_file():
            return cls()

        logger.info(f'Settings: Reading settings from {CONFIG_PATH}')
        with open(CONFIG_PATH) as f:
            settings_dict = yaml.safe_load(f)
            return YamlConverter.structure(settings_dict, cl=cls)

    def write(self):
        """Write settings to config file"""
        logger.info(f'Writing settings to {CONFIG_PATH}')
        CONFIG_PATH.mkdir(parents=True, exist_ok=True)
        settings_dict = YamlConverter.unstructure(self)
        with open(CONFIG_PATH, 'w') as f:
            yaml.safe_dump(settings_dict, f)

    @classmethod
    def reset_defaults(cls) -> 'Settings':
        cls().write()
        return cls.read()


# TODO: Separately store loaded history, new history for session; only write (append) new history
def read_stored_taxa() -> dict:
    """Read taxon view history, starred, and frequency

    Returns:
        Stored taxon view history, starred, and frequency
    """
    if not STORED_TAXA_PATH.is_file():
        stored_taxa = {}
    else:
        with open(STORED_TAXA_PATH) as f:
            stored_taxa = json.load(f)

    stored_taxa.setdefault('history', [])
    stored_taxa.setdefault('starred', [])
    stored_taxa['frequent'] = convert_int_dict(stored_taxa.get('frequent', {}))
    stored_taxa['observed'] = convert_int_dict(stored_taxa.get('observed', {}))
    return stored_taxa


def write_stored_taxa(stored_taxa: dict):
    """Write taxon view history to file, along with stats on most frequently viewed taxa

    Args:
        Complete taxon history (including previously stored history)
    """
    # Do a recount/resort before writing
    stored_taxa["frequent"] = OrderedDict(Counter(stored_taxa["history"]).most_common())

    logger.info(
        'Settings: Writing stored taxa: '
        f'{len(stored_taxa["history"])} history items, '
        f'{len(stored_taxa["starred"])} starred items, '
        f'{len(stored_taxa["frequent"])} frequent items, '
        f'{len(stored_taxa["observed"])} observed items'
    )
    with open(STORED_TAXA_PATH, 'w') as f:
        json.dump(stored_taxa, f, indent=4)
    logger.info('Settings: Done')
