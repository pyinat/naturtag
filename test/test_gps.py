from naturtag.metadata.gps_metadata import (
    convert_dwc_coords,
    convert_exif_coords,
    convert_xmp_coords,
    to_exif_coords,
    to_xmp_coords,
)

DECIMAL_DEGREES = (37.76939, 122.48619)


def test_convert_dwc_coords():
    metadata = {
        'Xmp.dwc.decimalLatitude': '37.76939',
        'Xmp.dwc.decimalLongitude': '122.48619',
    }
    assert convert_dwc_coords(metadata) == DECIMAL_DEGREES


def test_convert_exif_coords():
    metadata = {
        'Exif.GPSInfo.GPSLatitude': '37/1 46/1 98399/10000',
        'Exif.GPSInfo.GPSLatitudeRef': 'N',
        'Exif.GPSInfo.GPSLongitude': '122/1 29/1 103199/10000',
        'Exif.GPSInfo.GPSLongitudeRef': 'W',
    }
    assert _approx_equals(convert_exif_coords(metadata), DECIMAL_DEGREES)


def test_convert_exif_coords__negative():
    metadata = {
        'Exif.GPSInfo.GPSLatitude': '37/1 46/1 98399/10000',
        'Exif.GPSInfo.GPSLatitudeRef': 'S',
        'Exif.GPSInfo.GPSLongitude': '122/1 29/1 103199/10000',
        'Exif.GPSInfo.GPSLongitudeRef': 'E',
    }
    assert _approx_equals(convert_exif_coords(metadata), (-37.76939, -122.48619))


def _approx_equals(coords_1, coords_2, epsilon=0.00001):
    return abs(coords_1[0] - coords_2[0]) < epsilon and abs(coords_1[1] - coords_2[1]) < epsilon


def test_convert_xmp_coords():
    metadata = {
        'Xmp.exif.GPSLatitude': '37,46.1639999N',
        'Xmp.exif.GPSLongitude': '122,29.1719999W',
    }
    assert _approx_equals(convert_xmp_coords(metadata), DECIMAL_DEGREES)


def test_convert_xmp_coords__negative():
    metadata = {
        'Xmp.exif.GPSLatitude': '37,46.1639999S',
        'Xmp.exif.GPSLongitude': '122,29.1719999E',
    }
    assert _approx_equals(convert_xmp_coords(metadata), (-37.76939, -122.48619))


def test_convert_coords__invalid():
    assert convert_dwc_coords({'Xmp.dwc.decimalLatitude': 'asdf'}) is None
    assert convert_exif_coords({'Exif.GPSInfo.GPSLatitude': 'asdf'}) is None
    assert convert_xmp_coords({'Xmp.exif.GPSLatitude': 'asdf'}) is None


def test_to_exif_coords():
    assert to_exif_coords(DECIMAL_DEGREES) == {
        'Exif.GPSInfo.GPSLatitude': '37/1 46/1 98039/10000',
        'Exif.GPSInfo.GPSLatitudeRef': 'N',
        'Exif.GPSInfo.GPSLongitude': '122/1 29/1 102839/10000',
        'Exif.GPSInfo.GPSLongitudeRef': 'W',
    }


def test_to_xmp_coords():
    assert to_xmp_coords(DECIMAL_DEGREES) == {
        'Xmp.exif.GPSLatitude': '37,46.16339999999991N',
        'Xmp.exif.GPSLongitude': '122,29.171399999999267W',
    }
