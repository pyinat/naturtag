from naturtag.metadata import ImageMetadata
from test.conftest import SAMPLE_DATA_DIR


def test_read_metadata():
    img_path = SAMPLE_DATA_DIR / '78513963.jpg'
    meta = ImageMetadata(img_path)
    assert meta.exif['Exif.GPSInfo.GPSLatitudeRef'] == 'N'
    assert meta.xmp['Xmp.dwc.institutionCode'] == 'iNaturalist'
    assert 'taxonomy:class=Insecta' in meta.iptc['Iptc.Application2.Subject']


def test_sidecar_path__default():
    img_path = SAMPLE_DATA_DIR / '78513963.jpg'
    meta = ImageMetadata(img_path)
    assert meta.has_sidecar
    assert meta.sidecar_path.name == '78513963.xmp'


def test_sidecar_path__alt():
    """This image already has a sidecar in the alternate filename format, so that should be used"""
    img_path = SAMPLE_DATA_DIR / 'IMG20200521_141401.jpg'
    meta = ImageMetadata(img_path)
    assert meta.has_sidecar
    assert meta.sidecar_path.name == 'IMG20200521_141401.jpg.xmp'
