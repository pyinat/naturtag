from datetime import datetime
from unittest.mock import patch

import pytest
from pyinaturalist import Observation, Taxon

from naturtag.metadata.inat_metadata import (
    _get_common_keywords,
    _get_hierarchical_keywords,
    _get_id_keywords,
    _get_taxon_hierarchical_keywords,
    _get_taxonomy_keywords,
    observation_to_metadata,
    tag_images,
)

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
    """Subspecies should appear as the leaf node in hierarchical keywords"""
    keywords = _get_taxon_hierarchical_keywords(SUBSPECIES)
    assert any('Canis familiaris dingo' in k for k in keywords)
    assert keywords[-1] == 'Animalia|Canidae|Canis|Canis familiaris|Canis familiaris dingo'


def test_tag_images__delegates_to_iter():
    with patch(
        'naturtag.metadata.inat_metadata._tag_images_iter', return_value=iter([])
    ) as mock_iter:
        tag_images([], taxon_id=1)

    mock_iter.assert_called_once()
