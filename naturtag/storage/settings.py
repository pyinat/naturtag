"""Utilities for reading and writing settings from config files"""

# TODO: Finish and document portable mode / storing config and data in a user-specified path
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import Optional

import yaml
from attr import define, field
from cattrs import Converter
from cattrs.preconf import pyyaml

from naturtag.constants import APP_DIR, CONFIG_PATH, MAX_DIR_HISTORY, PathOrStr

logger = getLogger().getChild(__name__)


def make_converter() -> Converter:
    """Additional serialization steps not covered by cattrs yaml converter"""
    converter = pyyaml.make_converter()
    converter.register_unstructure_hook(Path, lambda obj: str(obj) if obj else None)
    converter.register_structure_hook(
        Path, lambda obj, cls: Path(obj).expanduser() if obj else None
    )
    converter.register_unstructure_hook(datetime, lambda obj: obj.isoformat() if obj else None)
    converter.register_structure_hook(
        datetime, lambda obj, cls: datetime.fromisoformat(obj) if obj else None
    )
    return converter


YamlConverter = make_converter()


def doc_field(doc: str = '', **kwargs):
    """
    Create a field for an attrs class that is documented in the class docstring.
    """
    return field(metadata={'doc': doc}, **kwargs)


@define
class Settings:
    # Display settings
    dark_mode: bool = field(default=False)

    # Logging settings
    log_level: str = doc_field(default='INFO', doc='Logging level')
    log_level_external: str = field(default='INFO')
    show_logs: bool = doc_field(default=False, doc='Show a tab with application logs')

    # iNaturalist
    all_ranks: bool = doc_field(
        default=False,
        doc='Show all available taxonomic rank filters on taxon search page',
    )
    casual_observations: bool = doc_field(
        default=True, doc='Include taxa from casual observations in user taxa list'
    )
    locale: str = doc_field(default='en', doc='Locale preference for species common names')
    preferred_place_id: int = doc_field(
        default=1,
        converter=int,
        doc='Place preference for regional species common names',
    )
    search_locale: bool = doc_field(
        default=True, doc='Search common names for only your selected locale'
    )
    username: str = doc_field(default='', doc='Your iNaturalist username')

    # Metadata
    common_names: bool = doc_field(default=True, doc='Include common names in taxonomy keywords')
    hierarchical: bool = doc_field(default=True, doc='Generate hierarchical keywords')
    sidecar: bool = doc_field(default=True, doc='Write XMP metadata to sidecar (separate file)')
    exif: bool = doc_field(default=True, doc='Write EXIF metadata to image (embedded)')
    iptc: bool = doc_field(default=True, doc='Write IPTC metadata to image (embedded)')
    xmp: bool = doc_field(default=True, doc='Write XMP metadata to image (embedded)')

    # User data directories
    path: Optional[Path] = doc_field(default=None, doc='Alternate config path')
    default_image_dir: Path = doc_field(
        default=Path('~').expanduser(), doc='Open file chooser in a specific directory'
    )
    use_last_dir: bool = doc_field(
        default=True, doc='Open file chooser in the previously used directory'
    )
    recent_image_dirs: list[Path] = field(factory=list)
    favorite_image_dirs: list[Path] = field(factory=list)

    # Internal
    debug: bool = field(default=False)
    n_worker_threads: int = field(default=1)

    # Shortcuts for application files within the user data dir
    @property
    def data_dir(self) -> Path:
        return self.path.parent  # type: ignore

    @property
    def db_path(self) -> Path:
        return self.data_dir / 'naturtag.db'

    @property
    def image_cache_path(self) -> Path:
        return self.data_dir / 'images.db'

    @property
    def logfile(self) -> Path:
        return self.data_dir / 'naturtag.log'

    @property
    def start_image_dir(self) -> Path:
        """Get the starting directory for image selection, depending on settings"""
        if self.use_last_dir and self.recent_image_dirs:
            return self.recent_image_dirs[0]
        else:
            return self.default_image_dir

    @classmethod
    def read(cls, path: Path = CONFIG_PATH) -> 'Settings':
        """Read settings from config file"""
        # New file; no contents to read
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            return cls(path=path)

        logger.debug(f'Reading settings from {path}')
        with open(path) as f:
            attrs_dict = yaml.safe_load(f)
        obj = YamlConverter.structure(attrs_dict, cl=cls)

        # Config file may be a stub that specifies an alternate path; if so, read from that path
        if obj.path and obj.path != path:
            return cls.read(obj.path)

        obj.path = path
        return obj

    def write(self):
        """Write settings to config file"""
        logger.info(f'Writing settings to {self.path}')
        logger.debug(str(self))
        attrs_dict = YamlConverter.unstructure(self)

        # Only keep 'path' if it's not the default
        if self.path.parent == APP_DIR:
            attrs_dict.pop('path')

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, 'w') as f:
            yaml.safe_dump(attrs_dict, f)

    def add_favorite_dir(self, image_dir: Path):
        if image_dir not in self.favorite_image_dirs:
            self.favorite_image_dirs.append(image_dir)

    def add_recent_dir(self, path: PathOrStr):
        """Add a directory to the list of recent image directories"""
        path = Path(path)
        if path in self.recent_image_dirs:
            self.recent_image_dirs.remove(path)
        self.recent_image_dirs = [path] + self.recent_image_dirs[:MAX_DIR_HISTORY]

    def remove_favorite_dir(self, image_dir: Path):
        if image_dir in self.favorite_image_dirs:
            self.favorite_image_dirs.remove(image_dir)
        self.write()

    def remove_recent_dir(self, image_dir: Path):
        if image_dir in self.recent_image_dirs:
            self.recent_image_dirs.remove(image_dir)

    def reset_defaults(self):
        """Reset all settings to defaults"""
        self.__class__(path=self.path).write()
        self = self.__class__.read(path=self.path)
