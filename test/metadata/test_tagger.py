from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from pyinaturalist import Observation, Taxon

from naturtag.metadata.base import BaseMetadata, _create_sidecar_stub
from naturtag.metadata.derived import (
    DerivedMetadata,
    _get_common_keywords,
    _get_hierarchical_keywords,
    _get_id_keywords,
    _get_taxon_hierarchical_keywords,
    _get_taxonomy_keywords,
)
from naturtag.metadata.tagger import _refresh_tags, observation_to_metadata, tag_images
from naturtag.storage import Settings
from test.conftest import DEMO_IMAGES_DIR, SAMPLE_DATA_DIR

DEMO_IMAGE = DEMO_IMAGES_DIR / '78513963.jpg'

KINGDOM = Taxon(id=1, name='Animalia', rank='kingdom', preferred_common_name='Animals')
FAMILY = Taxon(id=3, name='Rhagionidae', rank='family', preferred_common_name='Snipe Flies')
SPECIES = Taxon(
    id=202860,
    name='Chrysopilus ornatus',
    rank='species',
    preferred_common_name='Ornate Snipe Fly',
    ancestors=[KINGDOM, FAMILY],
)
CANIDAE = Taxon(
    id=4, name='Canidae', rank='family', preferred_common_name='Dogs, Wolves, and Foxes'
)
CANIS = Taxon(id=5, name='Canis', rank='genus', preferred_common_name='Wolves, Dogs')
CANIS_FAMILIARIS = Taxon(
    id=6, name='Canis familiaris', rank='species', preferred_common_name='Domestic Dog'
)
SUBSPECIES = Taxon(
    id=924041,
    name='Canis familiaris dingo',
    rank='subspecies',
    preferred_common_name='Dingo',
    ancestors=[KINGDOM, CANIDAE, CANIS, CANIS_FAMILIARIS],
)
OBSERVATION = Observation(
    id=49459966,
    taxon=SPECIES,
    location=(41.199, -93.657),
    positional_accuracy=10,
    observed_on=datetime(2020, 6, 6),
)


@pytest.mark.parametrize(
    'keywords, expected',
    [
        ([], []),
        (['A', 'B', 'C'], ['A', 'A|B', 'A|B|C']),
        (['Animals'], ['Animals']),
        (['Animals', 'Insects'], ['Animals', 'Animals|Insects']),
    ],
)
def test_get_hierarchical_keywords(keywords, expected):
    assert _get_hierarchical_keywords(keywords) == expected


@pytest.mark.parametrize(
    'obs_id, taxon_id, expected',
    [
        (
            100,
            200,
            [
                'inat:taxon_id=200',
                'dwc:taxonID=200',
                'inat:observation_id=100',
                'dwc:catalogNumber=100',
            ],
        ),
        (None, 200, ['inat:taxon_id=200', 'dwc:taxonID=200']),
        (100, None, ['inat:observation_id=100', 'dwc:catalogNumber=100']),
        (None, None, []),
    ],
)
def test_get_id_keywords(obs_id, taxon_id, expected):
    assert _get_id_keywords(obs_id, taxon_id) == expected


def test_get_taxonomy_keywords():
    keywords = _get_taxonomy_keywords(SPECIES)
    assert 'taxonomy:kingdom=Animalia' in keywords
    assert 'taxonomy:family=Rhagionidae' in keywords
    assert '"taxonomy:species=Chrysopilus ornatus"' in keywords


def test_get_taxonomy_keywords__no_ancestors():
    taxon = Taxon(id=1, name='Animalia', rank='kingdom', ancestors=[])
    assert _get_taxonomy_keywords(taxon) == ['taxonomy:kingdom=Animalia']


def test_get_common_keywords():
    keywords = _get_common_keywords(SPECIES)
    assert 'Animals' in keywords
    assert '"Snipe Flies"' in keywords
    assert '"Ornate Snipe Fly"' in keywords


def test_get_common_keywords__filters_ignored_terms():
    """Common names containing 'allies', 'relatives', etc. should be excluded"""
    taxon = Taxon(
        id=5,
        name='SomeGroup',
        rank='family',
        preferred_common_name='Flies and allies',
        ancestors=[],
    )
    assert _get_common_keywords(taxon) == []


def test_get_common_keywords__skips_non_common_ranks():
    """Taxa with ranks not in COMMON_RANKS should be excluded"""
    suborder = Taxon(
        id=2, name='Brachycera', rank='suborder', preferred_common_name='Short-horned Flies'
    )
    species = Taxon(
        id=3,
        name='Test species',
        rank='species',
        preferred_common_name='Test Fly',
        ancestors=[suborder],
    )
    keywords = _get_common_keywords(species)
    # suborder is not in COMMON_RANKS, so its common name should be excluded
    assert 'Short-horned Flies' not in keywords
    assert '"Test Fly"' in keywords


def test_observation_to_metadata():
    meta = observation_to_metadata(OBSERVATION)
    assert meta.taxon_id == 202860
    assert meta.observation_id == 49459966
    assert meta.has_coordinates
    lat, lon = meta.coordinates
    assert abs(lat - 41.199) < 0.01
    assert abs(lon - (-93.657)) < 0.01
    assert 'Xmp.dwc.catalogNumber' in meta.xmp


def test_observation_to_metadata__common_names():
    meta = observation_to_metadata(OBSERVATION, common_names=True)
    keywords = meta.keyword_meta.keywords
    assert any('Ornate Snipe Fly' in k for k in keywords)


def test_observation_to_metadata__hierarchical():
    meta = observation_to_metadata(OBSERVATION, hierarchical=True)
    keywords = meta.keyword_meta.keywords
    assert any('|' in k for k in keywords)


def test_observation_to_metadata__hierarchical_and_common_names():
    meta = observation_to_metadata(OBSERVATION, hierarchical=True, common_names=True)
    hier_tags = meta.keyword_meta.hier_keywords
    assert 'Animalia' in hier_tags
    assert 'Animals' in hier_tags


def test_observation_to_metadata__taxon_only():
    obs = Observation(taxon=SPECIES)
    meta = observation_to_metadata(obs)
    assert meta.taxon_id == 202860
    assert meta.observation_id is None


def test_get_taxon_hierarchical_keywords__subspecies():
    keywords = _get_taxon_hierarchical_keywords(SUBSPECIES)
    assert any('Canis familiaris dingo' in k for k in keywords)
    assert keywords[-1] == 'Animalia|Canidae|Canis|Canis familiaris|Canis familiaris dingo'


def test_tag_images__returns_list():
    sentinel = object()
    with patch('naturtag.metadata.tagger._tag_images_iter', return_value=iter([sentinel])):
        result = tag_images([], taxon_id=1)

    assert isinstance(result, list)
    assert result == [sentinel]


@pytest.fixture
def mock_client():
    """A client mock that returns a fixed OBSERVATION for any from_id() lookup."""
    client = MagicMock()
    client.from_id.return_value = OBSERVATION
    return client


@pytest.fixture
def settings(tmp_path):
    return Settings(path=tmp_path / 'settings.yml')


def _tag_raw_jpg_pair(tmp_path, mock_client, settings):
    """Copy a RAW+JPG pair sharing a basename into tmp_path and tag both."""
    jpg = tmp_path / 'photo1.jpg'
    jpg.write_bytes(DEMO_IMAGE.read_bytes())
    raw = tmp_path / 'photo1.ORF'
    raw.write_bytes((SAMPLE_DATA_DIR / 'raw_without_sidecar.ORF').read_bytes())

    results = tag_images([jpg, raw], taxon_id=SPECIES.id, client=mock_client, settings=settings)
    return jpg, raw, results


def test_tag_images__raw_and_jpg_pair_share_sidecar(tmp_path, mock_client, settings):
    """Tagging a RAW+JPG pair (same stem, same dir) writes to a single shared XMP sidecar."""
    jpg, raw, results = _tag_raw_jpg_pair(tmp_path, mock_client, settings)

    shared_sidecar = tmp_path / 'photo1.xmp'
    assert shared_sidecar.is_file()
    assert {m.image_path for m in results} == {jpg, raw}
    assert all(m.sidecar_path == shared_sidecar for m in results)


def test_tag_images__raw_pre_existing_alt_sidecar_not_shared_with_jpg(
    tmp_path, mock_client, settings
):
    """Documents a known limitation: if the RAW file already has a sidecar under the alternate
    ``{ext}.xmp`` naming (used to disambiguate multiple raw formats sharing a stem), a
    newly-paired jpg doesn't discover it and writes its own separate default-named sidecar
    instead of sharing it.
    """
    alt_sidecar = tmp_path / 'photo1.ORF.xmp'
    _create_sidecar_stub(alt_sidecar)

    jpg, raw, results = _tag_raw_jpg_pair(tmp_path, mock_client, settings)

    default_sidecar = tmp_path / 'photo1.xmp'
    assert alt_sidecar.is_file()
    assert default_sidecar.is_file()
    by_path = {m.image_path: m for m in results}
    assert by_path[raw].sidecar_path == alt_sidecar
    assert by_path[jpg].sidecar_path == default_sidecar


def test_tag_images__raw_and_jpg_pair_writes_sidecar_once(tmp_path, mock_client, settings):
    """Tagging a RAW+JPG pair only writes their shared sidecar"""
    with patch.object(BaseMetadata, '_write_sidecar') as mock_write_sidecar:
        _tag_raw_jpg_pair(tmp_path, mock_client, settings)

    mock_write_sidecar.assert_not_called()


@pytest.mark.parametrize('pass_failed_paths', [False, True], ids=['no_out_param', 'with_out_param'])
def test_tag_images__one_path_failure_does_not_drop_other_results(
    tmp_path, mock_client, settings, pass_failed_paths
):
    """A write failure on one path (e.g. a locked/corrupted file) doesn't discard results already
    produced for other paths in the same batch. When the optional failed_paths out-param is
    provided, it also collects the failed path."""
    jpg = tmp_path / 'a.jpg'
    jpg.write_bytes(DEMO_IMAGE.read_bytes())
    other = tmp_path / 'b.jpg'
    other.write_bytes(DEMO_IMAGE.read_bytes())

    original_write = BaseMetadata.write

    def flaky_write(self, *args, **kwargs):
        if self.image_path == jpg:
            raise RuntimeError('simulated corrupt file')
        return original_write(self, *args, **kwargs)

    failed_paths = [] if pass_failed_paths else None
    with patch.object(DerivedMetadata, 'write', flaky_write):
        results = tag_images(
            [jpg, other],
            taxon_id=SPECIES.id,
            client=mock_client,
            settings=settings,
            failed_paths=failed_paths,
        )

    assert {m.image_path for m in results} == {other}
    if pass_failed_paths:
        assert failed_paths == [jpg]


def test_tag_images__jpg_embedded_only_xmp_not_copied_to_shared_sidecar(
    tmp_path, mock_client, settings
):
    """Documents a known limitation: if a jpg has XMP tags embedded directly in the file
    that were never copied into any sidecar, tagging it together with a paired RAW file no
    longer propagates those jpg-embedded-only tags into the shared sidecar, since the jpg's
    own sidecar write (which used to copy them there) is now skipped as redundant.
    """
    jpg = tmp_path / 'photo1.jpg'
    jpg.write_bytes(DEMO_IMAGE.read_bytes())
    raw = tmp_path / 'photo1.ORF'
    raw.write_bytes((SAMPLE_DATA_DIR / 'raw_without_sidecar.ORF').read_bytes())

    pre_existing = DerivedMetadata(jpg)
    pre_existing.update({'Xmp.dc.identifier': 'pre-existing embedded tag'})
    pre_existing.write(write_exif=False, write_iptc=False, write_xmp=True, write_sidecar=False)

    tag_images([jpg, raw], taxon_id=SPECIES.id, client=mock_client, settings=settings)

    shared_sidecar = tmp_path / 'photo1.xmp'
    sidecar_meta = DerivedMetadata(shared_sidecar)
    assert 'Xmp.dc.identifier' not in sidecar_meta.xmp

    jpg_meta = DerivedMetadata(jpg)
    assert jpg_meta.xmp.get('Xmp.dc.identifier') == 'pre-existing embedded tag'


def test_refresh_tags__no_raw_path_refreshes_only_companion(tmp_path, mock_client, settings):
    """Without a raw_path, refresh behaves as it did before RAW+JPG pairing existed."""
    jpg = tmp_path / 'photo1.jpg'
    jpg.write_bytes(DEMO_IMAGE.read_bytes())
    tag_images([jpg], taxon_id=SPECIES.id, client=mock_client, settings=settings)

    result = _refresh_tags(DerivedMetadata(jpg), mock_client, settings)

    assert result.image_path == jpg
    assert (tmp_path / 'photo1.xmp').is_file()


def test_refresh_tags__refreshes_paired_raw_file(tmp_path, mock_client, settings):
    """Refreshing a card's companion path also refreshes its paired RAW file's metadata, via
    their shared sidecar."""
    jpg, raw, _ = _tag_raw_jpg_pair(tmp_path, mock_client, settings)

    result = _refresh_tags(DerivedMetadata(jpg), mock_client, settings, raw_path=raw)

    assert result.image_path == jpg
    raw_metadata = DerivedMetadata(raw)
    assert raw_metadata.taxon_id == SPECIES.id
    assert raw_metadata.sidecar_path == result.sidecar_path


def test_refresh_tags__paired_raw_shares_single_observation_fetch(tmp_path, mock_client, settings):
    """Refreshing a paired RAW+JPG card fetches the observation once, not once per path."""
    jpg, raw, _ = _tag_raw_jpg_pair(tmp_path, mock_client, settings)
    mock_client.from_id.reset_mock()

    _refresh_tags(DerivedMetadata(jpg), mock_client, settings, raw_path=raw)

    mock_client.from_id.assert_called_once()


def test_refresh_tags__paired_raw_dedupes_sidecar_write(tmp_path, mock_client, settings):
    """Refreshing a RAW+JPG pair only writes their shared sidecar once, not twice."""
    jpg, raw, _ = _tag_raw_jpg_pair(tmp_path, mock_client, settings)

    with patch.object(BaseMetadata, '_write_sidecar') as mock_write_sidecar:
        _refresh_tags(DerivedMetadata(jpg), mock_client, settings, raw_path=raw)

    mock_write_sidecar.assert_not_called()


def test_refresh_tags__does_not_leak_companion_only_metadata_to_raw(
    tmp_path, mock_client, settings
):
    """Refreshing a paired RAW+JPG card only propagates the observation-derived data to the RAW
    file, not any of the companion's own pre-existing, unrelated metadata."""
    jpg, raw, _ = _tag_raw_jpg_pair(tmp_path, mock_client, settings)

    # Add metadata to the JPG's own file that has nothing to do with the observation
    jpg_only = DerivedMetadata(jpg)
    jpg_only.update({'Xmp.dc.identifier': 'jpg-only tag'})
    jpg_only.write(write_exif=False, write_iptc=False, write_xmp=True, write_sidecar=False)

    _refresh_tags(DerivedMetadata(jpg), mock_client, settings, raw_path=raw)

    raw_metadata = DerivedMetadata(raw)
    assert 'Xmp.dc.identifier' not in raw_metadata.xmp


def test_refresh_tags__companion_write_failure_returns_none(tmp_path, mock_client, settings):
    """A write failure on the companion path aborts the refresh and returns None."""
    jpg = tmp_path / 'photo1.jpg'
    jpg.write_bytes(DEMO_IMAGE.read_bytes())
    tag_images([jpg], taxon_id=SPECIES.id, client=mock_client, settings=settings)

    with patch.object(DerivedMetadata, 'write', side_effect=RuntimeError('simulated corrupt file')):
        result = _refresh_tags(DerivedMetadata(jpg), mock_client, settings)

    assert result is None


def test_refresh_tags__raw_write_failure_does_not_discard_companion_result(
    tmp_path, mock_client, settings
):
    """A write failure on the paired RAW file doesn't discard the companion's already-successful
    refresh result."""
    jpg, raw, _ = _tag_raw_jpg_pair(tmp_path, mock_client, settings)

    original_write = BaseMetadata.write

    def flaky_write(self, *args, **kwargs):
        if self.image_path == raw:
            raise RuntimeError('simulated corrupt RAW file')
        return original_write(self, *args, **kwargs)

    with patch.object(DerivedMetadata, 'write', flaky_write):
        result = _refresh_tags(DerivedMetadata(jpg), mock_client, settings, raw_path=raw)

    assert result is not None
    assert result.image_path == jpg
