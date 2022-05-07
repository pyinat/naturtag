""" Basic utilities for reading and writing settings from config files """
from collections import Counter, OrderedDict
from logging import getLogger
from pathlib import Path
from typing import Optional

import yaml
from attr import define, field
from cattr import Converter
from cattr.preconf import pyyaml

from naturtag.constants import CONFIG_PATH, STORED_TAXA_PATH

logger = getLogger().getChild(__name__)


def make_converter() -> Converter:
    converter = pyyaml.make_converter()
    converter.register_unstructure_hook(Path, str)
    converter.register_structure_hook(Path, lambda obj, cls: Path(obj))
    return converter


YamlConverter = make_converter()


class YamlMixin:
    """Attrs class mixin that converts to and from a YAML file"""

    path: Path

    @classmethod
    def read(cls) -> 'YamlMixin':
        """Read settings from config file"""
        if not cls.path.is_file():
            return cls()

        logger.info(f'Reading {cls.__name__} from {cls.path}')
        with open(cls.path) as f:
            attrs_dict = yaml.safe_load(f)
            return YamlConverter.structure(attrs_dict, cl=cls)

    def write(self):
        """Write settings to config file"""
        logger.info(f'Writing {self.__class__.__name__} to {self.path}')
        logger.debug(str(self))
        self.path.parent.mkdir(parents=True, exist_ok=True)

        attrs_dict = YamlConverter.unstructure(self)
        with open(self.path, 'w') as f:
            yaml.safe_dump(attrs_dict, f)

    @classmethod
    def reset_defaults(cls) -> 'YamlMixin':
        cls().write()
        return cls.read()


@define
class Settings(YamlMixin):
    path = CONFIG_PATH

    # Display
    dark_mode: bool = field(default=False)
    show_logs: bool = field(default=False)
    # TODO:
    # md_primary_palette: str = field(default='Teal')
    # md_accent_palette: str = field(default='Cyan')

    # iNaturalist
    casual_observations: bool = field(default=True)
    locale: str = field(default='en_US')
    preferred_place_id: int = field(default=1, converter=int)
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


@define
class UserTaxa(YamlMixin):
    """Relevant taxon IDs stored for the current user"""

    path = Path(str(STORED_TAXA_PATH).replace('json', 'yml'))

    history: list[int] = field(factory=list)
    starred: list[int] = field(factory=list)
    observed: dict[int, int] = field(factory=dict)
    _frequent: Optional[dict[int, int]] = None

    @property
    def frequent(self) -> dict[int, int]:
        if self._frequent is None:
            self._frequent = OrderedDict(Counter(self.history).most_common())
        return self._frequent

    def append_history(self, taxon_id: int):
        self.history.append(taxon_id)
        self._frequent = None

    def __str__(self):
        sizes = [
            f'History: {len(self.history)}',
            f'Starred: {len(self.starred)}',
            f'Frequent: {len(self.frequent)}',
            f'Observed: {len(self.observed)}',
        ]
        return '\n'.join(sizes)
