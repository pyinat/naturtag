import shutil

import pytest

from naturtag.metadata import BaseMetadata
from test.conftest import DEMO_IMAGES_DIR, SAMPLE_DATA_DIR

DEMO_IMAGE = DEMO_IMAGES_DIR / '78513963.jpg'


def test_read_metadata():
    meta = BaseMetadata(DEMO_IMAGE)
    assert meta.exif['Exif.GPSInfo.GPSLatitudeRef'] == 'N'
    assert meta.xmp['Xmp.dwc.institutionCode'] == 'iNaturalist'
    assert 'taxonomy:class=Insecta' in meta.iptc['Iptc.Application2.Subject']


def test_read_metadata__nonexistent_file():
    meta = BaseMetadata('/nonexistent/path/image.jpg')
    assert meta.exif == {}
    assert meta.iptc == {}
    assert meta.xmp == {}


def test_read_metadata__merges_sidecar():
    """XMP sidecar data should be merged into the image's metadata"""
    meta = BaseMetadata(DEMO_IMAGE)
    assert 'Xmp.dwc.taxonID' in meta.xmp
    assert meta.xmp['Xmp.dwc.taxonID'] == '202860'


@pytest.mark.parametrize(
    'image_name, expected_sidecar_name',
    [
        ('78513963.jpg', '78513963.xmp'),
        ('IMG20200521_141401.jpg', 'IMG20200521_141401.jpg.xmp'),  # alternate format: image.ext.xmp
    ],
)
def test_sidecar_path(image_name, expected_sidecar_name):
    meta = BaseMetadata(DEMO_IMAGES_DIR / image_name)
    assert meta.has_sidecar
    assert meta.sidecar_path.name == expected_sidecar_name


def test_is_sidecar():
    xmp_meta = BaseMetadata(DEMO_IMAGES_DIR / 'example_45524803.xmp')
    assert xmp_meta.is_sidecar is True

    jpg_meta = BaseMetadata(DEMO_IMAGE)
    assert jpg_meta.is_sidecar is False


def test_has_sidecar__false_for_xmp_file():
    """An XMP file itself should not report having a sidecar"""
    meta = BaseMetadata(DEMO_IMAGES_DIR / 'example_45524803.xmp')
    assert meta.has_sidecar is False


def test_filtered_exif():
    """filtered_exif should exclude verbose manufacturer tags"""
    meta = BaseMetadata(DEMO_IMAGE)
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
    meta = BaseMetadata(DEMO_IMAGE)
    meta.exif['Exif.Test.ListTag'] = ['a', 'b', 'c']
    meta.exif['Exif.Test.StringTag'] = 'single'

    simple = meta.simple_exif
    assert simple['Exif.Test.ListTag'] == 'a,b,c'
    assert simple['Exif.Test.StringTag'] == 'single'


def test_update():
    meta = BaseMetadata(DEMO_IMAGE)
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
    meta = BaseMetadata(DEMO_IMAGE)
    original_lat_ref = meta.exif['Exif.GPSInfo.GPSLatitudeRef']
    meta.update({'Exif.Photo.NewTag': 'new_value'})
    assert meta.exif['Exif.GPSInfo.GPSLatitudeRef'] == original_lat_ref


def test_metadata_path__raw_returns_sidecar():
    meta = BaseMetadata(SAMPLE_DATA_DIR / 'raw_with_sidecar.ORF')
    assert meta.metadata_path == meta.sidecar_path


def test_metadata_path__jpg_returns_self():
    meta = BaseMetadata(DEMO_IMAGE)
    assert meta.metadata_path == meta.image_path


def test_write__lr_hierarchical_subject_uses_rdf_bag(tmp_path):
    """lr:hierarchicalSubject should be written as rdf:Bag, not rdf:Seq"""
    img_copy = tmp_path / DEMO_IMAGE.name
    shutil.copy(DEMO_IMAGE, img_copy)

    meta = BaseMetadata(img_copy)
    meta.xmp['Xmp.lr.hierarchicalSubject'] = ['Animalia', 'Animalia|Arthropoda']
    meta.write(write_exif=False, write_iptc=False, write_xmp=True, write_sidecar=False)

    import pyexiv2

    img = pyexiv2.Image(str(img_copy))
    try:
        raw = img.read_raw_xmp()
    finally:
        img.close()

    assert '<rdf:Bag>' in raw
    # Ensure no rdf:Seq wraps lr:hierarchicalSubject specifically
    lr_start = raw.index('lr:hierarchicalSubject')
    lr_end = raw.index('/lr:hierarchicalSubject')
    lr_block = raw[lr_start:lr_end]
    assert '<rdf:Bag>' in lr_block
    assert '<rdf:Seq>' not in lr_block
