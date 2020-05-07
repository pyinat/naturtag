from logging import getLogger
from os.path import isfile, splitext

from pyexiv2 import Image

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

logger = getLogger(__name__)


def update_all_keywords(path, keywords, hier_keywords=None):
    metadata = {tag: keywords for tag in KEYWORD_TAGS}
    if hier_keywords:
        metadata.update({tag: hier_keywords for tag in HIER_KEYWORD_TAGS})
    update_metadata(path, metadata)

    # Also write XMP tags to sidecar file, if one is present
    xmp_path = splitext(path)[0] + '.xmp'
    if isfile(xmp_path):
        update_metadata(xmp_path, metadata)


def update_metadata(path, metadata):
    """ Update arbitrary EXIF, IPTC, and/or XMP metadata """
    logger.info(f'Writing {len(metadata)} tags to {path}')
    img = Image(path)

    xmp = img.read_xmp() or {}
    xmp.update({k: v for k, v in metadata.items() if k.startswith('Xmp.')})
    img.modify_xmp(xmp)

    # If we're writing to a sidecar file, only write XMP tags
    if path.lower().endswith('.xmp'):
        img.close()
        return

    exif = img.read_exif() or {}
    exif.update({k: v for k, v in metadata.items() if k.startswith('Exif.')})
    img.modify_exif(exif)

    iptc = img.read_iptc() or {}
    iptc.update({k: v for k, v in metadata.items() if k.startswith('Iptc.')})
    img.modify_iptc(iptc)

    img.close()
