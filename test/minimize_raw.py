#!/usr/bin/env python3
"""Create minimized RAW test fixtures for rawpy thumbnail extraction tests.


This script zeroes out sensor pixel data, so total filesize remains the same, but they compress
extremely well in git's object store, and retain enough structure for rawpy's extract_thumb() to work.

- Keep all TIFF metadata and IFD structures intact
- Replace all IFD-referenced JPEG previews with a tiny 16x16 synthetic JPEG
- Update the JPEGLength (tag 514) IFD entry if present
- Zero out raw sensor pixel data (never needed for extract_thumb())
- Write the result to test/sample_data/<original filename>

Usage:
    test/minimize_raw.py path/to/original.RAW
"""

import argparse
import struct
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

from test.analyze_raw import parse_tiff_header, read_ifd, read_offsets_and_lengths

SAMPLE_DATA = Path(__file__).parent / 'sample_data'


def _scan_file(data: bytes) -> tuple[str, dict]:
    """Parse RAW file bytes and return (endian, results).

    results has keys:
      'jpegs'      — list of dicts with offset/length/length_tag_entry_offset
      'raw_regions' — list of dicts with offset/length for raw sensor data
    """
    endian, ifd0_offset = parse_tiff_header(data)

    results: dict = {'jpegs': [], 'raw_regions': []}
    ifd_offset = ifd0_offset
    ifd_index = 0
    while ifd_offset:
        _collect_ifd(data, ifd_offset, endian, f'IFD{ifd_index}', results)
        _, ifd_offset, _ = read_ifd(data, ifd_offset, endian)
        ifd_index += 1

    return endian, results


def _collect_ifd(data: bytes, ifd_offset: int, endian: str, label: str, results: dict) -> None:
    """Recursively walk an IFD, collecting JPEG preview and raw sensor info."""
    entries, _, _ = read_ifd(data, ifd_offset, endian)
    if not entries:
        return

    # Embedded JPEG via tags 513 (offset) / 514 (length)
    if 513 in entries and 514 in entries:
        results['jpegs'].append(
            {
                'label': label,
                'offset': entries[513][2],
                'length': entries[514][2],
                'length_tag_entry_offset': entries[514][3],
            }
        )

    # Raw sensor strips (tags 273/279) and tiles (tags 324/325)
    for offset_tag, length_tag in [(273, 279), (324, 325)]:
        for off, ln in read_offsets_and_lengths(data, entries, offset_tag, length_tag, endian):
            results['raw_regions'].append({'offset': off, 'length': ln})

    # SubIFDs (tag 330)
    if 330 in entries:
        _, cnt, val, _ = entries[330]
        sub_offsets = (
            [val]
            if cnt == 1
            else [struct.unpack_from(endian + 'I', data, val + i * 4)[0] for i in range(cnt)]
        )
        for i, sub_off in enumerate(sub_offsets):
            _collect_ifd(data, sub_off, endian, f'{label}/SubIFD[{i}]', results)


def _make_tiny_jpeg(size: tuple[int, int] = (16, 16), color: str = 'red') -> bytes:
    buf = BytesIO()
    Image.new('RGB', size, color=color).save(buf, format='JPEG')
    return buf.getvalue()


def minimize(src: Path, dest: Path) -> None:
    """Minimize a RAW file by replacing embedded JPEGs and zeroing raw sensor data.

    Reads src, writes the minimized result to dest (may be the same path).
    """
    print(f'Reading {src} ({src.stat().st_size / 1024 / 1024:.1f} MB)...')
    data = bytearray(src.read_bytes())
    endian, results = _scan_file(bytes(data))

    if not results['jpegs'] and not results['raw_regions']:
        raise RuntimeError(
            'No embedded JPEGs or raw sensor regions found — is this a TIFF-based RAW file?'
        )

    tiny_jpeg = _make_tiny_jpeg()

    for jpeg in sorted(results['jpegs'], key=lambda j: j['length'], reverse=True):
        old_offset = jpeg['offset']
        old_len = jpeg['length']
        data[old_offset : old_offset + len(tiny_jpeg)] = tiny_jpeg
        data[old_offset + len(tiny_jpeg) : old_offset + old_len] = b'\x00' * (
            old_len - len(tiny_jpeg)
        )
        print(
            f'  Replaced JPEG [{jpeg["label"]}] @ {old_offset:,}: {old_len:,} → {len(tiny_jpeg)} bytes'
        )

        if jpeg['length_tag_entry_offset'] is not None:
            struct.pack_into(
                endian + 'I', data, jpeg['length_tag_entry_offset'] + 8, len(tiny_jpeg)
            )
            print(f'    Updated IFD tag 514 entry @ {jpeg["length_tag_entry_offset"]:,}')

    for region in results['raw_regions']:
        off, ln = region['offset'], region['length']
        data[off : off + ln] = b'\x00' * ln
        print(f'  Zeroed raw sensor region @ {off:,}: {ln / 1024 / 1024:.1f} MB')

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f'Written {dest} ({dest.stat().st_size / 1024 / 1024:.1f} MB)')


def verify(path: Path) -> None:
    """Verify rawpy can extract a valid thumbnail from the minimized file."""
    import rawpy

    print(f'Verifying {path.name} with rawpy...')
    with rawpy.imread(str(path)) as raw:
        thumb = raw.extract_thumb()

    if thumb.format == rawpy.ThumbFormat.JPEG:
        img = Image.open(BytesIO(bytes(thumb.data)))
        print(f'  OK: {thumb.format}, size={img.size}')
    elif thumb.format == rawpy.ThumbFormat.BITMAP:
        print(f'  OK: {thumb.format}, shape={getattr(thumb.data, "shape", "?")}')
    else:
        raise AssertionError(f'Unexpected thumbnail format: {thumb.format}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Minimize a RAW file for use in test data')
    parser.add_argument('src', type=Path, help='Path to the original RAW file')
    args = parser.parse_args()

    if not args.src.exists():
        print(f'ERROR: File not found: {args.src}', file=sys.stderr)
        sys.exit(1)

    dest = SAMPLE_DATA / args.src.name
    minimize(args.src, dest)
    verify(dest)
    print('Done.')


if __name__ == '__main__':
    main()
