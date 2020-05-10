""" Utilities dealing with writing multiple formats of image metadata """
from logging import getLogger
from os.path import isfile, splitext

from pyexiv2 import Image

# All tags that support regular and hierarchical keyword lists
KEYWORD_TAGS = [
    'Exif.Image.XPSubject',
    'Iptc.Application2.Subject',
    'Xmp.dc.subject',
]
HIER_KEYWORD_TAGS = [
    'Exif.Image.XPKeywords',
    'Iptc.Application2.Keywords',
    'Xmp.lr.hierarchicalSubject',
]

# Minimal XML content needed to create a new XMP file; exiv2 can handle the rest
NEW_XMP_CONTENTS = """
<?xpacket?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="">
</x:xmpmeta>
<?xpacket?>
"""

logger = getLogger(__name__)


def get_keyword_metadata(keywords, hier_keywords=None):
    """
    Given a list of keywords (and optional hierarchical keywords), add them to all appropriate
    XMP, EXIF, and IPTC tags.

    Returns:
        dict: Mapping from qualified tag name to tag value(s)
    """
    metadata = {tag: keywords for tag in KEYWORD_TAGS}
    if hier_keywords:
        metadata.update({tag: hier_keywords for tag in HIER_KEYWORD_TAGS})
    return metadata


def write_metadata(path, metadata, create_xmp=False):
    """ Update arbitrary EXIF, IPTC, and/or XMP metadata """
    logger.info(f'Writing {len(metadata)} tags to {path}')
    img = Image(path)

    write_xmp_sidecar(path, metadata, create_xmp)
    _write_xmp(img, metadata)
    _write_exif(img, metadata)
    _write_iptc(img, metadata)
    img.close()


def write_xmp_sidecar(path, metadata, create_xmp=False):
    """ Write XMP tags to a sidecar file, if one is present, or optionally create a new one """
    xmp_path = splitext(path)[0] + '.xmp'
    if create_xmp:
        create_xmp_sidecar(xmp_path)

    if isfile(xmp_path):
        logger.info(f'Writing subset of tags to {xmp_path}')
        sidecar = Image(xmp_path)
        _write_xmp(sidecar, metadata)
        sidecar.close()
    else:
        logger.info(f'No existing XMP sidecar file found for {path}; skipping')


def create_xmp_sidecar(path):
    """ Create a new XMP sidecar file if one does not already exist """
    if isfile(path):
        return
    logger.info(f'Creating new XMP sidecar file: {path}')
    with open(path, 'w') as f:
        f.write(NEW_XMP_CONTENTS.strip())


# Write to individual metadata formats; further code reuse would be possible, but less readable

def _write_xmp(img, metadata):
    xmp = img.read_xmp() or {}
    xmp.update({k: v for k, v in metadata.items() if k.startswith('Xmp.')})
    img.modify_xmp(xmp)


def _write_exif(img, metadata):
    exif = img.read_exif() or {}
    exif.update({k: v for k, v in metadata.items() if k.startswith('Exif.')})
    img.modify_exif(exif)


def _write_iptc(img, metadata):
    iptc = img.read_iptc() or {}
    iptc.update({k: v for k, v in metadata.items() if k.startswith('Iptc.')})
    img.modify_iptc(iptc)
