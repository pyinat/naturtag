from naturtag.metadata import ImageMetadata
from test.conftest import DEMO_IMAGES_DIR

DEMO_IMAGE = DEMO_IMAGES_DIR / '78513963.jpg'


def test_read_metadata():
    meta = ImageMetadata(DEMO_IMAGE)
    assert meta.exif['Exif.GPSInfo.GPSLatitudeRef'] == 'N'
    assert meta.xmp['Xmp.dwc.institutionCode'] == 'iNaturalist'
    assert 'taxonomy:class=Insecta' in meta.iptc['Iptc.Application2.Subject']


def test_read_metadata__nonexistent_file():
    meta = ImageMetadata('/nonexistent/path/image.jpg')
    assert meta.exif == {}
    assert meta.iptc == {}
    assert meta.xmp == {}


def test_read_metadata__merges_sidecar():
    """XMP sidecar data should be merged into the image's metadata"""
    meta = ImageMetadata(DEMO_IMAGE)
    assert 'Xmp.dwc.taxonID' in meta.xmp
    assert meta.xmp['Xmp.dwc.taxonID'] == '202860'


def test_sidecar_path__default():
    meta = ImageMetadata(DEMO_IMAGE)
    assert meta.has_sidecar
    assert meta.sidecar_path.name == '78513963.xmp'


def test_sidecar_path__alt():
    """This image already has a sidecar in the alternate filename format, so that should be used"""
    img_path = DEMO_IMAGES_DIR / 'IMG20200521_141401.jpg'
    meta = ImageMetadata(img_path)
    assert meta.has_sidecar
    assert meta.sidecar_path.name == 'IMG20200521_141401.jpg.xmp'


def test_is_sidecar():
    xmp_meta = ImageMetadata(DEMO_IMAGES_DIR / 'example_45524803.xmp')
    assert xmp_meta.is_sidecar is True

    jpg_meta = ImageMetadata(DEMO_IMAGE)
    assert jpg_meta.is_sidecar is False


def test_has_sidecar__false_for_xmp_file():
    """An XMP file itself should not report having a sidecar"""
    meta = ImageMetadata(DEMO_IMAGES_DIR / 'example_45524803.xmp')
    assert meta.has_sidecar is False


def test_filtered_exif():
    """filtered_exif should exclude verbose manufacturer tags"""
    meta = ImageMetadata(DEMO_IMAGE)
    meta.exif['Exif.MakerNote.Something'] = 'hidden'
    meta.exif['Exif.Photo.MakerNote'] = 'also hidden'
    meta.exif['Exif.Image.PrintImageMatching'] = 'also hidden'

    filtered = meta.filtered_exif
    assert 'Exif.GPSInfo.GPSLatitudeRef' in filtered
    assert 'Exif.MakerNote.Something' not in filtered
    assert 'Exif.Photo.MakerNote' not in filtered
    assert 'Exif.Image.PrintImageMatching' not in filtered


def test_simple_exif():
    """simple_exif should join list values into comma-separated strings"""
    meta = ImageMetadata(DEMO_IMAGE)
    meta.exif['Exif.Test.ListTag'] = ['a', 'b', 'c']
    meta.exif['Exif.Test.StringTag'] = 'single'

    simple = meta.simple_exif
    assert simple['Exif.Test.ListTag'] == 'a,b,c'
    assert simple['Exif.Test.StringTag'] == 'single'


def test_update():
    meta = ImageMetadata(DEMO_IMAGE)
    meta.update(
        {
            'Exif.Photo.NewTag': 'exif_value',
            'Iptc.Application2.NewTag': 'iptc_value',
            'Xmp.dc.NewTag': 'xmp_value',
        }
    )
    assert meta.exif['Exif.Photo.NewTag'] == 'exif_value'
    assert meta.iptc['Iptc.Application2.NewTag'] == 'iptc_value'
    assert meta.xmp['Xmp.dc.NewTag'] == 'xmp_value'


def test_update__preserves_existing():
    """update() should not remove existing metadata"""
    meta = ImageMetadata(DEMO_IMAGE)
    original_lat_ref = meta.exif['Exif.GPSInfo.GPSLatitudeRef']
    meta.update({'Exif.Photo.NewTag': 'new_value'})
    assert meta.exif['Exif.GPSInfo.GPSLatitudeRef'] == original_lat_ref
