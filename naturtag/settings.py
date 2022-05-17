""" Basic utilities for reading and writing settings from config files """
from collections import Counter, OrderedDict
from logging import getLogger
from pathlib import Path
from typing import Optional

import yaml
from attr import define, field
from cattr import Converter
from cattr.preconf import pyyaml

from naturtag.constants import CONFIG_PATH, DEFAULT_WINDOW_SIZE, LOGFILE, USER_TAXA_PATH

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


def doc_field(doc: str = '', **kwargs):
    """
    Create a field for an attrs class that is documented in the class docstring.
    """
    return field(metadata={'doc': doc}, **kwargs)


@define
class Settings(YamlMixin):
    path = CONFIG_PATH

    # Display settings
    dark_mode: bool = field(default=False)
    show_logs: bool = field(default=False)
    window_size: tuple[int, int] = field(default=DEFAULT_WINDOW_SIZE)

    # Logging settings
    log_level: str = field(default='INFO')
    log_level_external: str = field(default='INFO')
    logfile: Path = field(default=LOGFILE, converter=Path)

    # iNaturalist
    all_ranks: bool = doc_field(
        default=False, doc='Show all available taxonomic rank filters on taxon search page'
    )
    casual_observations: bool = doc_field(default=True, doc='Include casual observations in searches')
    locale: str = doc_field(default='en', doc='Locale preference for species common names')
    preferred_place_id: int = doc_field(
        default=1, converter=int, doc='Place preference for regional species common names'
    )
    username: str = doc_field(default='', doc='Your iNaturalist username')

    # Metadata
    common_names: bool = doc_field(default=True, doc='Include common names in taxonomy keywords')
    create_sidecar: bool = doc_field(
        default=True, doc="Create XMP sidecar files if they don't already exist"
    )
    darwin_core: bool = doc_field(
        default=True, doc='Convert species/observation metadata into XMP Darwin Core metadata'
    )
    hierarchical_keywords: bool = doc_field(
        default=False, doc='Generate pipe-delimited hierarchical keyword tags'
    )

    # TODO:
    # data_dir: Path = field(default=DATA_DIR, converter=Path)
    # default_image_dir: Path = field(default=Path('~').expanduser(), converter=Path)
    # starred_image_dirs: list[Path] = field(factory=list)


@define
class UserTaxa(YamlMixin):
    """Relevant taxon IDs stored for the current user"""

    path = USER_TAXA_PATH

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
        self.frequent.setdefault(taxon_id, 0)
        self.frequent[taxon_id] += 1

    def __str__(self):
        sizes = [
            f'History: {len(self.history)}',
            f'Starred: {len(self.starred)}',
            f'Frequent: {len(self.frequent)}',
            f'Observed: {len(self.observed)}',
        ]
        return '\n'.join(sizes)

    @classmethod
    def read(cls) -> 'UserTaxa':
        return super(UserTaxa, cls).read()  # type: ignore
