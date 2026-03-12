#!/usr/bin/env python3
"""Analyze the structure of a RAW (TIFF-based) image file.

Useful for understanding where embedded JPEG previews and raw sensor data live,
which is the prerequisite for writing a minimization script for a new camera model.

Usage:
    test/analyze_raw.py path/to/file.RAW
"""

import argparse
import struct
import sys
from io import BytesIO
from pathlib import Path

# TIFF tag names used in the analysis output
TAG_NAMES: dict[int, str] = {
    254: 'NewSubfileType',
    256: 'ImageWidth',
    257: 'ImageLength',
    258: 'BitsPerSample',
    259: 'Compression',
    262: 'PhotometricInterpretation',
    270: 'ImageDescription',
    271: 'Make',
    272: 'Model',
    273: 'StripOffsets',
    277: 'SamplesPerPixel',
    278: 'RowsPerStrip',
    279: 'StripByteCounts',
    282: 'XResolution',
    283: 'YResolution',
    284: 'PlanarConfiguration',
    296: 'ResolutionUnit',
    305: 'Software',
    306: 'DateTime',
    315: 'Artist',
    324: 'TileOffsets',
    325: 'TileByteCounts',
    330: 'SubIFDs',
    513: 'JPEGInterchangeFormat',
    514: 'JPEGInterchangeFormatLength',
    529: 'YCbCrCoefficients',
    530: 'YCbCrSubSampling',
    531: 'YCbCrPositioning',
    532: 'ReferenceBlackWhite',
    700: 'XMP',
    33421: 'CFARepeatPatternDim',
    33422: 'CFAPattern',
    33432: 'Copyright',
    34665: 'ExifIFD',
    34853: 'GPSIFD',
    37500: 'MakerNote',
    50341: 'PrintIM',
    50717: 'BlackLevel',
    50740: 'DNGPrivateData',
}

_SOF_NAMES = {
    0xC0: 'Baseline',
    0xC1: 'Extended sequential',
    0xC2: 'Progressive',
}

COMPRESSION_NAMES: dict[int, str] = {
    1: 'Uncompressed',
    6: 'JPEG (old-style)',
    7: 'JPEG',
    32767: 'Sony ARW',
    32769: 'Packed RAW',
    34892: 'Lossy JPEG',
    34925: 'Packed RAW (lossless)',
}

_MIN_GAP_SIZE = 16


def _compression_str(value: int) -> str:
    name = COMPRESSION_NAMES.get(value, 'Unknown')
    return f'{value} ({name})'


def _append_coverage(results: dict, data_len: int, start: int, end: int, label: str) -> None:
    if 'covered_regions' not in results:
        return
    start = max(0, start)
    end = min(end, data_len)
    if start < end:
        results['covered_regions'].append((start, end, label))


def read_ifd(
    data: bytes, offset: int, endian: str
) -> tuple[dict[int, tuple], int, tuple[int, int]]:
    """Read a TIFF IFD and return (entries_dict, next_ifd_offset, (ifd_start, ifd_end)).

    entries_dict maps tag -> (type, count, value_or_offset, entry_byte_offset)
    """
    if offset + 2 > len(data):
        return {}, 0, (0, 0)
    count = struct.unpack_from(endian + 'H', data, offset)[0]
    entries: dict[int, tuple] = {}
    for i in range(count):
        entry_offset = offset + 2 + i * 12
        if entry_offset + 12 > len(data):
            break
        tag, type_, cnt, value_or_offset = struct.unpack_from(endian + 'HHII', data, entry_offset)
        entries[tag] = (type_, cnt, value_or_offset, entry_offset)
    next_ifd_offset_pos = offset + 2 + count * 12
    next_ifd = (
        struct.unpack_from(endian + 'I', data, next_ifd_offset_pos)[0]
        if next_ifd_offset_pos + 4 <= len(data)
        else 0
    )
    ifd_end = min(offset + 2 + count * 12 + 4, len(data))
    return entries, next_ifd, (offset, ifd_end)


def parse_tiff_header(data: bytes) -> tuple[str, int]:
    """Return (endian, ifd0_offset) from a TIFF header, or raise ValueError."""
    byte_order = data[:2]
    if byte_order == b'II':
        endian = '<'
    elif byte_order == b'MM':
        endian = '>'
    else:
        raise ValueError(f'Not a TIFF-based RAW file (header bytes: {data[:4].hex()})')
    ifd0_offset = struct.unpack_from(endian + 'I', data, 4)[0]
    return endian, ifd0_offset


def read_offsets_and_lengths(
    data: bytes, entries: dict, offset_tag: int, length_tag: int, endian: str
) -> list[tuple[int, int]]:
    """Read a parallel array of (offset, length) values from two IFD tags.

    Used for strip data (tags 273/279) and tile data (tags 324/325).
    When count==1, the value is stored inline in the IFD entry; otherwise it
    points to an array of LONGs in the file.
    """
    if offset_tag not in entries or length_tag not in entries:
        return []

    def _read_longs(cnt: int, val: int) -> list[int]:
        if cnt == 1:
            return [val]
        return [struct.unpack_from(endian + 'I', data, val + i * 4)[0] for i in range(cnt)]

    _, cnt_o, val_o, _ = entries[offset_tag]
    _, cnt_l, val_l, _ = entries[length_tag]
    return list(zip(_read_longs(cnt_o, val_o), _read_longs(cnt_l, val_l), strict=False))


def _get_string_value(data: bytes, entries: dict, tag: int, endian: str, max_len: int = 40) -> str:
    """Read a short ASCII string value from an IFD entry."""
    if tag not in entries:
        return ''
    type_, cnt, value_or_offset, _ = entries[tag]
    if type_ == 2:  # ASCII
        if cnt <= 4:
            raw = struct.pack(endian + 'I', value_or_offset)[:cnt]
        else:
            raw = data[value_or_offset : value_or_offset + min(cnt, max_len)]
        return raw.rstrip(b'\x00').decode('latin-1', errors='replace')
    return ''


def _detect_jpeg_at(data: bytes, offset: int) -> int | None:
    """Return the JPEG length (up to EOI marker) starting at offset, or None if not a JPEG."""
    if offset + 4 > len(data):
        return None
    if data[offset : offset + 2] != b'\xff\xd8':
        return None
    pos = data.find(b'\xff\xd9', offset + 2)
    return None if pos == -1 else pos - offset + 2


def _jpeg_dimensions(data: bytes, offset: int, length: int) -> tuple[int, int, str] | None:
    """Parse width/height from a JPEG SOF marker."""
    end = offset + length
    pos = offset + 2
    while pos + 4 < end:
        if data[pos] != 0xFF:
            break
        marker = data[pos + 1]
        if marker == 0xD9:
            break
        if marker in _SOF_NAMES:
            if pos + 9 <= end:
                height = struct.unpack_from('>H', data, pos + 5)[0]
                width = struct.unpack_from('>H', data, pos + 7)[0]
                return width, height, _SOF_NAMES[marker]
            break
        seg_len = struct.unpack_from('>H', data, pos + 2)[0] if pos + 4 <= end else 0
        pos += 2 + seg_len
    return None


def _analyze_ifd(
    data: bytes,
    offset: int,
    endian: str,
    label: str,
    depth: int = 0,
    results: dict | None = None,
) -> dict:
    """Recursively analyze an IFD and all sub-IFDs, populating a results dict."""
    if results is None:
        results = {
            'jpegs': [],
            'raw_strips': [],
            'raw_tiles': [],
            'ifds': [],
            'covered_regions': [],
        }

    indent = '  ' * depth
    entries, _, ifd_range = read_ifd(data, offset, endian)
    if not entries:
        return results

    width = entries[256][2] if 256 in entries else 0
    height = entries[257][2] if 257 in entries else 0
    make = _get_string_value(data, entries, 271, endian)
    model = _get_string_value(data, entries, 272, endian)
    compression = entries[259][2] if 259 in entries else None

    ifd_dim_str = f' ({width}×{height})' if width and height else ''
    make_str = ' '.join(filter(None, [make, model]))
    compression_str = f'  compression={_compression_str(compression)}' if compression else ''
    print(
        f'{indent}IFD: {label} @ offset {offset:,}{ifd_dim_str}{f"  {make_str}" if make_str else ""}'
        f'{compression_str}'
    )

    results['ifds'].append({'label': label, 'offset': offset, 'entries': entries})
    _append_coverage(results, len(data), ifd_range[0], ifd_range[1], f'IFD {label}')
    _analyze_jpeg_preview(data, entries, label, indent, results)
    _analyze_raw_regions(data, entries, endian, label, indent, results)
    _print_unknown_tags(entries, indent)

    # SubIFDs (tag 330)
    if 330 in entries:
        type_, cnt, val, _ = entries[330]
        sub_offsets = (
            [val]
            if cnt == 1
            else [struct.unpack_from(endian + 'I', data, val + i * 4)[0] for i in range(cnt)]
        )
        for i, sub_off in enumerate(sub_offsets):
            _analyze_ifd(data, sub_off, endian, f'{label}/SubIFD[{i}]', depth + 1, results)

    _analyze_exif_ifd(data, entries, endian, label, indent, results)

    return results


def _analyze_jpeg_preview(
    data: bytes,
    entries: dict,
    label: str,
    indent: str,
    results: dict,
) -> None:
    if 513 not in entries or 514 not in entries:
        return
    jpeg_offset = entries[513][2]
    jpeg_len = entries[514][2]
    dims = _jpeg_dimensions(data, jpeg_offset, jpeg_len)
    if dims:
        jpeg_dim_str = f'{dims[0]}×{dims[1]}'
        sof_type = dims[2]
    else:
        jpeg_dim_str = 'unknown'
        sof_type = None
    print(
        f'{indent}  JPEG preview: offset={jpeg_offset:,}  length={jpeg_len:,}'
        f' ({jpeg_len / 1024:.1f} KB)  dims={jpeg_dim_str}'
        f'  sof={sof_type or "unknown"}'
    )
    results['jpegs'].append(
        {
            'label': label,
            'offset': jpeg_offset,
            'length': jpeg_len,
            'dims': dims,
            'sof_type': sof_type,
            'length_tag_entry_offset': entries[514][3],
        }
    )
    _append_coverage(
        results, len(data), jpeg_offset, jpeg_offset + jpeg_len, f'JPEG preview ({label})'
    )


def _analyze_raw_regions(
    data: bytes,
    entries: dict,
    endian: str,
    label: str,
    indent: str,
    results: dict,
) -> None:
    strips = read_offsets_and_lengths(data, entries, 273, 279, endian)
    if strips:
        total = sum(ln for _, ln in strips)
        print(
            f'{indent}  Strip data: {len(strips)} strip(s), first offset={strips[0][0]:,},'
            f' total={total:,} bytes ({total / 1024 / 1024:.1f} MB)'
        )
        results['raw_strips'].extend(
            {'label': label, 'offset': off, 'length': ln} for off, ln in strips
        )
        for off, ln in strips:
            _append_coverage(results, len(data), off, off + ln, f'Strip ({label})')

    tiles = read_offsets_and_lengths(data, entries, 324, 325, endian)
    if tiles:
        total = sum(ln for _, ln in tiles)
        print(
            f'{indent}  Tile data: {len(tiles)} tile(s), first offset={tiles[0][0]:,},'
            f' total={total:,} bytes ({total / 1024 / 1024:.1f} MB)'
        )
        results['raw_tiles'].extend(
            {'label': label, 'offset': off, 'length': ln} for off, ln in tiles
        )
        for off, ln in tiles:
            _append_coverage(results, len(data), off, off + ln, f'Tile ({label})')


def _print_unknown_tags(entries: dict, indent: str) -> None:
    unknown = sorted(t for t in entries if t not in TAG_NAMES)
    if unknown:
        print(f'{indent}  Unknown tags: ' + ', '.join(f'{t} ({hex(t)})' for t in unknown))


def _analyze_exif_ifd(
    data: bytes,
    entries: dict,
    endian: str,
    label: str,
    indent: str,
    results: dict,
) -> None:
    if 34665 not in entries:
        return
    exif_entries, _, exif_range = read_ifd(data, entries[34665][2], endian)
    _append_coverage(results, len(data), exif_range[0], exif_range[1], f'ExifIFD ({label})')
    _analyze_makernote(data, exif_entries, endian, indent + '  ', results)


def _scan_makernote_ifd_for_jpeg_refs(
    mn_entries: dict, results: dict, indent: str, brand: str
) -> None:
    if not results['jpegs']:
        return

    for jpeg in results['jpegs']:
        jpeg_off = jpeg['offset']
        for tag, (_, _cnt, val, entry_off) in mn_entries.items():
            if val == jpeg_off:
                print(
                    f'{indent}  {brand} MakerNote tag {tag} ({hex(tag)}) = {val}'
                    f' → matches JPEG at {jpeg_off}'
                )
                jpeg['makernote_offset_tag'] = tag
                jpeg['makernote_offset_entry'] = entry_off
            elif val == jpeg['length']:
                print(
                    f'{indent}  {brand} MakerNote tag {tag} ({hex(tag)}) = {val}'
                    f' → matches JPEG length for offset {jpeg_off}'
                )
                jpeg['makernote_length_tag'] = tag
                jpeg['makernote_length_entry'] = entry_off


def _analyze_olympus_makernote(
    data: bytes,
    exif_entries: dict,
    endian: str,
    indent: str,
    results: dict,
) -> None:
    """Check for Olympus MakerNote and its preview image pointers."""
    if 37500 not in exif_entries:
        return
    _, _, mn_offset, _ = exif_entries[37500]
    if not data[mn_offset : mn_offset + 7].startswith(b'OLYMPUS'):
        return
    if mn_offset + 12 > len(data):
        return

    # Olympus MakerNote: 12-byte header ('OLYMPUS\x00II\x03\x00' or similar)
    # followed by a TIFF-style IFD with offsets relative to the MakerNote start
    mn_ifd_rel = struct.unpack_from('<I', data, mn_offset + 8)[0]
    mn_ifd_abs = mn_offset + mn_ifd_rel
    mn_entries, _, _ = read_ifd(data, mn_ifd_abs, endian)

    # Scan for preview offset/length stored in MakerNote tags
    # (tag numbers vary; we search by value matching known JPEG offsets)
    print(f'{indent}Olympus MakerNote @ {mn_offset} (IFD at {mn_ifd_abs})')
    _scan_makernote_ifd_for_jpeg_refs(mn_entries, results, indent, 'Olympus')


def _analyze_sony_makernote(
    data: bytes,
    mn_offset: int,
    endian: str,
    indent: str,
    results: dict,
) -> None:
    """Check Sony MakerNote (12-byte header, IFD at +8)."""
    mn_ifd_abs = mn_offset + 8
    if mn_ifd_abs + 2 > len(data):
        return
    mn_entries, _, _ = read_ifd(data, mn_ifd_abs, endian)
    print(f'{indent}Sony MakerNote @ {mn_offset} (IFD at {mn_ifd_abs})')
    _scan_makernote_ifd_for_jpeg_refs(mn_entries, results, indent, 'Sony')


def _analyze_canon_makernote(
    data: bytes,
    mn_offset: int,
    endian: str,
    indent: str,
    results: dict,
) -> None:
    """Check Canon MakerNote (Canon\\x00 header, IFD at +6)."""
    mn_ifd_abs = mn_offset + 6
    if mn_ifd_abs + 2 > len(data):
        return
    mn_entries, _, _ = read_ifd(data, mn_ifd_abs, endian)
    print(f'{indent}Canon MakerNote @ {mn_offset} (IFD at {mn_ifd_abs})')
    _scan_makernote_ifd_for_jpeg_refs(mn_entries, results, indent, 'Canon')


def _analyze_nikon_makernote(
    data: bytes,
    mn_offset: int,
    mn_length: int,
    endian: str,
    indent: str,
    results: dict,
) -> None:
    """Check Nikon MakerNote (Nikon\\x00 + 4 bytes + embedded TIFF at +10)."""
    embedded_offset = mn_offset + 10
    if embedded_offset + 4 > len(data):
        return
    try:
        embedded_endian, ifd0_offset = parse_tiff_header(data[embedded_offset:])
    except ValueError:
        _analyze_makernote_brute_force(data, mn_offset, mn_length, indent, results)
        return
    mn_ifd_abs = embedded_offset + ifd0_offset
    mn_entries, _, _ = read_ifd(data, mn_ifd_abs, embedded_endian)
    print(f'{indent}Nikon MakerNote @ {mn_offset} (IFD at {mn_ifd_abs})')
    _scan_makernote_ifd_for_jpeg_refs(mn_entries, results, indent, 'Nikon')


def _analyze_makernote_brute_force(
    data: bytes,
    mn_offset: int,
    mn_length: int,
    indent: str,
    results: dict,
) -> None:
    """Scan MakerNote blob for LONG values matching known JPEG offsets/lengths."""
    if not results['jpegs'] or mn_length <= 0:
        return
    end = min(mn_offset + mn_length, len(data))
    print(f'{indent}MakerNote brute-force scan @ {mn_offset} (length {end - mn_offset})')
    known_offsets = {j['offset'] for j in results['jpegs']}
    known_lengths = {j['length'] for j in results['jpegs']}
    for pos in range(mn_offset, end - 3, 4):
        val_le = struct.unpack_from('<I', data, pos)[0]
        val_be = struct.unpack_from('>I', data, pos)[0]
        for val, tag in [(val_le, 'LE'), (val_be, 'BE')]:
            if val in known_offsets:
                print(f'{indent}  {tag} LONG @ {pos:,} = {val} → matches JPEG offset')
            elif val in known_lengths:
                print(f'{indent}  {tag} LONG @ {pos:,} = {val} → matches JPEG length')


def _analyze_makernote(
    data: bytes,
    exif_entries: dict,
    endian: str,
    indent: str,
    results: dict,
) -> None:
    """Dispatch MakerNote analysis based on brand prefix."""
    if 37500 not in exif_entries:
        return
    _type, cnt, mn_offset, _ = exif_entries[37500]
    if mn_offset <= 0 or mn_offset >= len(data):
        return
    prefix = data[mn_offset : mn_offset + 10]
    if prefix.startswith(b'OLYMPUS'):
        _analyze_olympus_makernote(data, exif_entries, endian, indent, results)
    elif prefix.startswith(b'SONY CAM') or prefix.startswith(b'SONY DSC'):
        _analyze_sony_makernote(data, mn_offset, endian, indent, results)
    elif prefix.startswith(b'Canon'):
        _analyze_canon_makernote(data, mn_offset, endian, indent, results)
    elif prefix.startswith(b'Nikon\x00'):
        _analyze_nikon_makernote(data, mn_offset, cnt, endian, indent, results)
    else:
        _analyze_makernote_brute_force(data, mn_offset, cnt, indent, results)


def _run_rawpy(path: Path) -> dict | None:
    """Extract thumbnail with rawpy and return info about what was extracted."""
    try:
        import rawpy
        from PIL import Image
    except ImportError as e:
        print(f'\nrawpy/PIL not available: {e}')
        return None

    try:
        with rawpy.imread(str(path)) as raw:
            thumb = raw.extract_thumb()
    except Exception as e:
        print(f'\nrawpy extraction failed: {e}')
        return None

    info: dict = {'format': str(thumb.format), 'data_length': len(thumb.data)}
    if thumb.format == rawpy.ThumbFormat.JPEG:
        try:
            img = Image.open(BytesIO(bytes(thumb.data)))
            info['dims'] = img.size
        except Exception:
            info['dims'] = None
    elif thumb.format == rawpy.ThumbFormat.BITMAP:
        info['dims'] = (
            (thumb.data.shape[1], thumb.data.shape[0]) if hasattr(thumb.data, 'shape') else None
        )
    return info


def _scan_unreferenced_jpegs(data: bytes, known_jpeg_offsets: set) -> None:
    """Scan for JPEG markers not referenced by any IFD (e.g. MakerNote-embedded previews)."""
    print('\n--- Scanning for unreferenced JPEG markers (FFD8) ---')
    pos = 0
    found_extra = False
    while pos < len(data) - 1:
        pos = data.find(b'\xff\xd8', pos)
        if pos == -1:
            break
        if pos not in known_jpeg_offsets:
            jpeg_len = _detect_jpeg_at(data, pos)
            if jpeg_len and jpeg_len > 500:  # ignore tiny/spurious matches
                dims = _jpeg_dimensions(data, pos, jpeg_len)
                if dims:
                    dim_str = f'{dims[0]}×{dims[1]}'
                    sof_type = dims[2]
                else:
                    dim_str = 'unknown'
                    sof_type = None
                print(
                    f'  Unreferenced JPEG @ {pos:,}: {jpeg_len:,} bytes'
                    f' ({jpeg_len / 1024:.1f} KB), dims={dim_str}, sof={sof_type or "unknown"}'
                )
                found_extra = True
        pos += 2
    if not found_extra:
        print('  None found.')


def _print_summary(results: dict) -> tuple[dict | None, list]:
    """Print summary of found JPEGs and raw sensor data. Returns (largest_jpeg, all_raw)."""
    print('\n--- Summary ---')
    all_raw = results['raw_strips'] + results['raw_tiles']
    largest = None
    if results['jpegs']:
        largest = max(results['jpegs'], key=lambda j: j['length'])
        print(f'Embedded JPEGs ({len(results["jpegs"])} found):')
        for j in sorted(results['jpegs'], key=lambda x: x['length'], reverse=True):
            dims_str = f'{j["dims"][0]}×{j["dims"][1]}' if j['dims'] else 'unknown'
            marker = ' ← rawpy will pick this (largest)' if j is largest else ''
            print(
                f'  [{j["label"]}] offset={j["offset"]:,}  length={j["length"]:,}'
                f'  dims={dims_str}{marker}'
            )
    else:
        print('No IFD-referenced embedded JPEGs found.')

    if all_raw:
        raw_start = min(r['offset'] for r in all_raw)
        raw_total = sum(r['length'] for r in all_raw)
        print(
            f'\nRaw sensor data: starts at {raw_start:,},'
            f' total {raw_total:,} bytes ({raw_total / 1024 / 1024:.1f} MB)'
        )

    return largest, all_raw


def _print_minimization_params(largest: dict | None, all_raw: list) -> None:
    """Print recommended minimization parameters."""
    print('\n--- Minimization parameters ---')
    if largest:
        print(
            f'  Replace JPEG:        offset={largest["offset"]:,}, old_length={largest["length"]:,}'
        )
        if 'length_tag_entry_offset' in largest:
            print(
                f'  Update IFD tag 514:  entry at byte offset {largest["length_tag_entry_offset"]:,}'
            )
        if 'makernote_length_entry' in largest:
            print(
                f'  Update MakerNote:    length entry at byte offset {largest["makernote_length_entry"]:,}'
            )
    if all_raw:
        raw_start = min(r['offset'] for r in all_raw)
        raw_total = sum(r['length'] for r in all_raw)
        print(
            f'  Zero raw sensor:     from offset {raw_start:,} ({raw_total / 1024 / 1024:.1f} MB)'
        )


def _print_coverage_map(data: bytes, covered: list[tuple[int, int, str]]) -> None:
    print('\n--- Coverage map ---')
    if not covered:
        print('  No coverage data.')
        return

    data_len = len(data)
    regions = _normalize_regions(covered, data_len)
    if not regions:
        print('  No coverage data.')
        return

    merged = _merge_regions(regions)

    covered_bytes = sum(end - start for start, end in merged)
    percent = covered_bytes / data_len * 100 if data_len else 0
    print(f'  Covered: {covered_bytes:,} bytes ({percent:.1f}%) across {len(merged)} region(s).')

    gaps = _find_gaps(merged, data_len)
    gaps = [(s, e) for s, e in gaps if (e - s) >= _MIN_GAP_SIZE]
    if not gaps:
        print(f'  No gaps >= {_MIN_GAP_SIZE} bytes.')
        return

    gaps_sorted = sorted(gaps, key=lambda g: g[1] - g[0], reverse=True)
    print(f'  Gaps (>= {_MIN_GAP_SIZE} bytes), largest first:')
    for start, end in gaps_sorted:
        gap_len = end - start
        print(f'    {gap_len:,} bytes @ {start:,}..{end - 1:,}')


def _normalize_regions(covered: list[tuple[int, int, str]], data_len: int) -> list[tuple[int, int]]:
    regions = []
    for start, end, _label in covered:
        start = max(0, start)
        end = min(end, data_len)
        if start < end:
            regions.append((start, end))
    return regions


def _merge_regions(regions: list[tuple[int, int]]) -> list[tuple[int, int]]:
    regions = sorted(regions, key=lambda r: r[0])
    merged = [regions[0]]
    for start, end in regions[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _find_gaps(merged: list[tuple[int, int]], data_len: int) -> list[tuple[int, int]]:
    gaps = []
    gap_start = 0
    for start, end in merged:
        if start > gap_start:
            gaps.append((gap_start, start))
        gap_start = end
    if gap_start < data_len:
        gaps.append((gap_start, data_len))
    return gaps


def analyze(path: Path) -> None:
    print(f'{"=" * 60}')
    print(f'File: {path}')
    print(f'Size: {path.stat().st_size:,} bytes ({path.stat().st_size / 1024 / 1024:.1f} MB)')
    print(f'{"=" * 60}\n')

    data = path.read_bytes()

    try:
        endian, ifd0_offset = parse_tiff_header(data)
    except ValueError as e:
        print(f'ERROR: {e}')
        return

    endian_name = 'little-endian (II)' if endian == '<' else 'big-endian (MM)'
    magic = struct.unpack_from(endian + 'H', data, 2)[0]
    print(f'TIFF header: {endian_name}, magic={magic} ({hex(magic)}), IFD0 @ {ifd0_offset:,}\n')

    # Walk the top-level IFD chain
    results: dict = {
        'jpegs': [],
        'raw_strips': [],
        'raw_tiles': [],
        'ifds': [],
        'covered_regions': [(0, 8, 'TIFF header')],
    }
    ifd_offset = ifd0_offset
    ifd_index = 0
    while ifd_offset:
        _analyze_ifd(data, ifd_offset, endian, f'IFD{ifd_index}', depth=0, results=results)
        _, ifd_offset, _ = read_ifd(data, ifd_offset, endian)
        ifd_index += 1

    _print_coverage_map(data, results.get('covered_regions', []))

    known_jpeg_offsets = {j['offset'] for j in results['jpegs']}
    _scan_unreferenced_jpegs(data, known_jpeg_offsets)

    # rawpy extraction
    print('\n--- rawpy extraction ---')
    rawpy_info = _run_rawpy(path)
    if rawpy_info:
        dims_str = f', dims={rawpy_info["dims"]}' if rawpy_info.get('dims') else ''
        print(f'  Format: {rawpy_info["format"]}')
        print(f'  Data length: {rawpy_info["data_length"]:,} bytes{dims_str}')

    largest, all_raw = _print_summary(results)
    _print_minimization_params(largest, all_raw)


def main() -> None:
    parser = argparse.ArgumentParser(description='Analyze TIFF-based RAW file structure')
    parser.add_argument('path', type=Path, help='Path to RAW file (.ARW, .ORF, .CR2, .NEF, etc.)')
    args = parser.parse_args()

    if not args.path.exists():
        print(f'ERROR: File not found: {args.path}', file=sys.stderr)
        sys.exit(1)

    analyze(args.path)


if __name__ == '__main__':
    main()
