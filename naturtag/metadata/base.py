import re
from logging import getLogger
from pathlib import Path
from typing import Any

import pyexiv2
from pyexiv2 import Image

from naturtag.constants import EXIF_HIDE_PREFIXES, PathOrStr
from naturtag.utils.image_glob import get_sidecar_path, is_raw_path

# Suppress exiv2 thumbnail warnings (log level 3 = error)
pyexiv2.set_log_level(3)

# Minimal XML content needed to create a new XMP file; exiv2 can handle the rest
NEW_XMP_CONTENTS = """
<?xpacket?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="">
</x:xmpmeta>
<?xpacket?>
"""
ARRAY_IDX_PATTERN = re.compile(r'\[\d+\]')

logger = getLogger().getChild(__name__)


class BaseMetadata:
    """Wrapper class for reading & writing basic image metadata with exiv2"""

    def __init__(self, image_path: PathOrStr = ''):
        self.image_path = Path(image_path)
        self.exif, self.iptc, self.xmp = self.read_metadata()

    def read_metadata(self):
        """Read all formats of metadata from image + sidecar file"""
        if not self.image_path.is_file():
            return {}, {}, {}

        exif, iptc, xmp = self._safe_read_metadata(self.metadata_path)

        # For non-RAW files, also merge sidecar data on top of embedded metadata.
        if not self.is_raw and self.has_sidecar:
            s_exif, s_iptc, s_xmp = self._safe_read_metadata(self.sidecar_path)
            exif.update(s_exif)
            iptc.update(s_iptc)
            xmp.update(s_xmp)

        sidecar_str = f' + {self.sidecar_path}' if self.sidecar_path.is_file() else ''
        counts = ' | '.join([f'EXIF: {len(exif)}', f'IPTC: {len(iptc)}', f'XMP: {len(xmp)}'])
        logger.debug(f'Total tags found in {self.image_path}{sidecar_str}: {counts}')

        return exif, iptc, xmp

    def _safe_read_metadata(self, path, encoding='utf-8'):
        """Attempt to read metadata, with error handling"""
        logger.debug(f'Reading metadata from: {path} ({encoding})')
        img = self._read_exiv2_image(path)
        if not img:
            return {}, {}, {}

        try:
            exif = img.read_exif(encoding=encoding)
            iptc = img.read_iptc(encoding=encoding)
            xmp = img.read_xmp(encoding=encoding)
        except UnicodeDecodeError:
            logger.warning(f'Non-UTF-encoded metadata in {path}')
            return self._safe_read_metadata(path, encoding='unicode_escape')
        finally:
            img.close()

        return exif, iptc, xmp

    @staticmethod
    def _read_exiv2_image(path: PathOrStr) -> Image:
        """
        Read an image with basic error handling. Note: Exiv2 ``RuntimeError`` usually means
        corrupted metadata. See: https://dev.exiv2.org/issues/637#note-1
        """
        try:
            return Image(str(path))
        except RuntimeError:
            logger.exception(f'Failed to read corrupted metadata from {path}')
            return None

    @property
    def sidecar_path(self) -> Path:
        """Get the path to a sidecar file for this image. May be in the format:
        * ``{basename}.xmp`` (default)
        * ``{basename}.{ext}.{xmp}`` (used only if it already exists)
        """
        return get_sidecar_path(self.image_path)

    @property
    def metadata_path(self) -> Path:
        """Path used for reading/writing metadata.
        JPG/PNG: use embedded metadata. RAW: use sidecar only.
        """
        return self.sidecar_path if self.is_raw else self.image_path

    @property
    def has_sidecar(self) -> bool:
        return not self.is_sidecar and self.sidecar_path.is_file()

    @property
    def is_sidecar(self) -> bool:
        return self.image_path.suffix.lower() == '.xmp'

    @property
    def is_raw(self) -> bool:
        return is_raw_path(self.image_path)

    @property
    def filtered_exif(self) -> dict[str, Any]:
        """Get EXIF tags, excluding some verbose manufacturer tags that aren't useful to display"""
        return {
            k: v
            for k, v in self.exif.items()
            if not any(k.startswith(prefix) for prefix in EXIF_HIDE_PREFIXES)
        }

    @property
    def simple_exif(self) -> dict[str, str]:
        """Convert all EXIF tags with list values into strings"""
        return {k: ','.join(v) if isinstance(v, list) else v for k, v in self.exif.items()}

    def update(self, new_metadata: dict):
        """Update arbitrary EXIF, IPTC, and/or XMP metadata"""
        logger.debug(f'Updating with {len(new_metadata)} tags')

        def _filter_tags(prefix):
            return {k: v for k, v in new_metadata.items() if k.startswith(prefix)}

        # Split combined metadata into individual formats
        self.exif.update(_filter_tags('Exif.'))
        self.iptc.update(_filter_tags('Iptc.'))
        self.xmp.update(_filter_tags('Xmp.'))

    def write(
        self,
        write_exif: bool = True,
        write_iptc: bool = True,
        write_xmp: bool = True,
        write_sidecar: bool = True,
    ):
        """Write current metadata to image and sidecar"""
        fixed_xmp = self._fix_xmp()
        if self.is_sidecar:
            _create_sidecar_stub(self.image_path)

        # Write to metadata_path (sidecar for RAW, image file for JPEG/PNG)
        if any([write_exif, write_iptc, write_xmp]):
            logger.info(f'Writing metadata to {self.metadata_path}')
            img = self._read_exiv2_image(self.metadata_path)
            if img is None:
                return
            try:
                if write_exif:
                    img.modify_exif(self.simple_exif)
                if write_iptc:
                    img.modify_iptc(self.iptc)
                if write_xmp:
                    img.modify_xmp(fixed_xmp)
            finally:
                img.close()

        # Write sidecar for non-RAW files (RAW already wrote to sidecar via metadata_path)
        if write_sidecar and not self.is_sidecar and not self.is_raw:
            self._write_sidecar(fixed_xmp)

    def _write_sidecar(self, fixed_xmp: dict):
        logger.info(f'Writing metadata to {self.sidecar_path}')
        _create_sidecar_stub(self.sidecar_path)
        sidecar_img = self._read_exiv2_image(self.sidecar_path)
        if sidecar_img is None:
            return
        try:
            sidecar_img.modify_xmp(fixed_xmp)
        finally:
            sidecar_img.close()

    def _fix_xmp(self):
        """Fix some invalid/incompatible XMP tags"""
        for k, v in self.xmp.items():
            # Flatten dict values, like {'lang="x-default"': value} -> value
            if isinstance(v, dict):
                self.xmp[k] = next(iter(v.values()), None)

            # exiv2 can't modify XMP Media Management History (or even write existing values??)
            if k.startswith('Xmp.xmpMM.History'):
                self.xmp[k] = None

            # XMP won't accept both a single value and an array with the same key
            # TODO: This fixes some edge cases, with errors like:
            #   "XMP Toolkit error 102: Composite nodes can't have values"
            # But in other cases, it causes a different error:
            #   "XMP Toolkit error 102: Indexing applied to non-array"
            # elif k.endswith(']') and (nonarray_key := ARRAY_IDX_PATTERN.sub('', k)) in self.xmp:
            #     self.xmp[nonarray_key] = None

        self.xmp = {k: v for k, v in self.xmp.items() if v is not None}
        return self.xmp


def _create_sidecar_stub(path: Path):
    """Create new sidecar file stub, if needed"""
    if not path.is_file():
        with open(path, 'w') as f:
            f.write(NEW_XMP_CONTENTS.strip())
