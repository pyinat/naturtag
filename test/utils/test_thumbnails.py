"""Tests for thumbnail generation utilities"""

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from PIL import Image

from naturtag.utils.thumbnails import _open_raw_image, generate_thumbnail
from test.conftest import SAMPLE_DATA_DIR

SAMPLE_RAW_FILES = [SAMPLE_DATA_DIR / 'IMG20210310_120958.ORF', SAMPLE_DATA_DIR / 'DSC05627.ARW']


@pytest.fixture
def sample_image(tmp_path):
    """Create a sample image file for testing"""
    img = Image.new('RGB', (300, 200), color='blue')
    img_path = tmp_path / 'test.jpg'
    img.save(img_path)
    return img_path


def _make_jpeg_bytes(size: tuple[int, int] = (100, 100), color: str = 'red') -> bytes:
    buf = BytesIO()
    Image.new('RGB', size, color=color).save(buf, format='JPEG')
    return buf.getvalue()


@pytest.fixture
def mock_rawpy():
    """Mock rawpy module - patched at builtins level since it's lazy-imported"""
    import sys
    from enum import Enum

    mock = MagicMock()

    # Create mock ThumbFormat enum to match rawpy's API
    class MockThumbFormat(Enum):
        JPEG = 0
        BITMAP = 1
        UNKNOWN = 2

    mock.ThumbFormat = MockThumbFormat
    sys.modules['rawpy'] = mock
    yield mock
    # Remove all rawpy submodules so real rawpy can re-import cleanly in later tests
    for key in [k for k in sys.modules if k == 'rawpy' or k.startswith('rawpy.')]:
        del sys.modules[key]


def _setup_rawpy_mock(mock_rawpy, thumb_data, thumb_format_enum):
    """Helper to set up rawpy mock with thumbnail data"""
    mock_raw = MagicMock()
    # MagicMock.__enter__ returns a new mock by default, not self — wire it explicitly
    mock_raw.__enter__ = MagicMock(return_value=mock_raw)
    mock_raw.__exit__ = MagicMock(return_value=False)
    # rawpy returns a Thumbnail namedtuple with .format and .data
    thumb = MagicMock()
    thumb.format = thumb_format_enum
    thumb.data = thumb_data
    mock_raw.extract_thumb.return_value = thumb
    mock_rawpy.imread.return_value = mock_raw
    return mock_raw


@pytest.mark.parametrize(
    'thumb_data, thumb_format, expected_size, expected_mode',
    [
        (
            _make_jpeg_bytes((100, 100)),
            'JPEG',
            (100, 100),
            'RGB',
        ),
        (
            np.full((100, 100, 3), [255, 0, 0], dtype=np.uint8),
            'BITMAP',
            (100, 100),
            'RGB',
        ),
    ],
)
def test_open_raw_image__mock_raw(
    mock_rawpy, thumb_data, thumb_format, expected_size, expected_mode
):
    """Test extracting JPEG and BITMAP thumbnails from a mock raw file"""
    _setup_rawpy_mock(mock_rawpy, thumb_data, mock_rawpy.ThumbFormat[thumb_format])

    result = _open_raw_image(Path('test.ORF'))
    assert isinstance(result, Image.Image)
    assert result.size == expected_size
    assert result.mode == expected_mode
    mock_rawpy.imread.assert_called_once_with('test.ORF')


@pytest.mark.parametrize('raw_path', SAMPLE_RAW_FILES)
def test_open_raw_image__real_raw(raw_path):
    """Integration test with real (but minimized) RAW files"""
    result = _open_raw_image(raw_path)

    assert isinstance(result, Image.Image)
    assert result.mode == 'RGB'
    width, height = result.size
    assert width > 0 and height > 0

    # Verify thumbnail can be saved and reloaded without corruption
    buffer = BytesIO()
    result.save(buffer, format='JPEG')
    buffer.seek(0)
    reloaded = Image.open(buffer)
    assert reloaded.size == result.size


def test_open_raw_image_imread_error(mock_rawpy):
    """Test that exceptions propagate when imread fails"""
    mock_rawpy.imread.side_effect = OSError('No thumbnail found')

    with pytest.raises(OSError, match='No thumbnail found'):
        _open_raw_image(Path('test.ORF'))


def test_open_raw_image_no_thumbnail(mock_rawpy):
    """Test that LibRawNoThumbnailError is converted to a friendly ValueError"""

    # Define a real exception class so it can be raised as a side_effect
    class FakeLibRawNoThumbnailError(Exception):
        pass

    mock_rawpy.LibRawNoThumbnailError = FakeLibRawNoThumbnailError

    mock_raw = MagicMock()
    mock_raw.__enter__ = MagicMock(return_value=mock_raw)
    mock_raw.__exit__ = MagicMock(return_value=False)
    mock_raw.extract_thumb.side_effect = FakeLibRawNoThumbnailError
    mock_rawpy.imread.return_value = mock_raw

    with pytest.raises(ValueError, match='No embedded thumbnail found in RAW file'):
        _open_raw_image(Path('test.ORF'))


def test_open_raw_image_unsupported_format(mock_rawpy):
    """Test that an unsupported ThumbFormat enum value raises ValueError"""
    _setup_rawpy_mock(mock_rawpy, b'', mock_rawpy.ThumbFormat.UNKNOWN)

    with pytest.raises(ValueError, match='Unsupported thumbnail format'):
        _open_raw_image(Path('test.ORF'))


def test_generate_thumbnail_regular_file_unchanged(sample_image):
    """Test that regular (non-RAW) file thumbnail generation still works"""
    result = generate_thumbnail(sample_image)
    assert result is not None
    assert result.width() == 200  # Cropped to square (short edge)
    assert result.height() == 200
    color = result.pixelColor(0, 0)
    assert (
        color.blue() > color.red() and color.blue() > color.green()
    )  # Verify dominant channel is blue


def test_generate_thumbnail__mock_raw(sample_image, mock_rawpy):
    """Test end-to-end thumbnail generation for RAW file"""
    _setup_rawpy_mock(
        mock_rawpy, _make_jpeg_bytes((100, 100), color='green'), mock_rawpy.ThumbFormat.JPEG
    )

    raw_path = sample_image.parent / 'test.ORF'
    sample_image.rename(raw_path)

    result = generate_thumbnail(raw_path)
    assert result is not None
    assert result.width() == 100
    assert result.height() == 100
    mock_rawpy.imread.assert_called_once_with(str(raw_path))


@pytest.mark.parametrize('raw_path', SAMPLE_RAW_FILES)
def test_generate_thumbnail__real_raw(raw_path):
    """RAW file -> rawpy extraction -> PIL -> Qt QImage"""
    result = generate_thumbnail(raw_path)

    assert result is not None
    assert result.width() > 0
    assert result.height() > 0
