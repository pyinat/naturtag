import pytest

from naturtag.metadata.meta_metadata import MetaMetadata, get_inaturalist_ids, simplify_keys
from test.conftest import DEMO_IMAGES_DIR

DEMO_IMAGE = DEMO_IMAGES_DIR / '78513963.jpg'


@pytest.mark.parametrize(
    'input_dict, expected',
    [
        ({'my_namespace:Sub_Family': 'Panorpinae'}, {'subfamily': 'Panorpinae'}),
        ({'Xmp.dwc.taxonID': '12345'}, {'xmp.dwc.taxonid': '12345'}),
        ({'UPPER_CASE': 'val'}, {'uppercase': 'val'}),
        ({'a:b:c': 'val'}, {'c': 'val'}),
        ({}, {}),
    ],
)
def test_simplify_keys(input_dict, expected):
    assert simplify_keys(input_dict) == expected


@pytest.mark.parametrize(
    'metadata, expected_taxon, expected_obs',
    [
        ({'taxonid': '202860', 'catalognumber': '49459966'}, 202860, 49459966),
        ({'taxonid': '12345'}, 12345, None),
        ({'catalognumber': '67890'}, None, 67890),
        ({'dwc:taxonid': '100', 'dwc:catalognumber': '200'}, 100, 200),
        ({'observationid': '111'}, None, 111),
        ({}, None, None),
    ],
)
def test_get_inaturalist_ids(metadata, expected_taxon, expected_obs):
    taxon_id, observation_id = get_inaturalist_ids(metadata)
    assert taxon_id == expected_taxon
    assert observation_id == expected_obs


def test_attrs():
    meta = MetaMetadata(DEMO_IMAGE)

    assert meta.taxon_id == 202860
    assert meta.observation_id == 49459966
    assert meta.has_taxon is True
    assert meta.has_observation is True
    assert meta.has_coordinates is True
    assert meta.has_any_tags is True
    lat, lon = meta.coordinates
    assert abs(lat - 41.199) < 0.01
    assert abs(lon - (-93.657)) < 0.01
    assert '2020-06-06' in meta.date
    assert meta.taxon_url == 'https://www.inaturalist.org/taxa/202860'
    assert meta.observation_url == 'https://www.inaturalist.org/observations/49459966'
    combined = meta.combined
    assert any(k.startswith('Exif.') for k in combined)
    assert any(k.startswith('Xmp.') for k in combined)
    simplified = meta.simplified
    assert simplified['taxonid'] == '202860'
    assert simplified['catalognumber'] == '49459966'
    assert simplified['kingdom'] == 'Animalia'
    summary = meta.summary
    assert 'Chrysopilus ornatus' in summary
    assert '78513963' in summary


def test_to_observation():
    meta = MetaMetadata(DEMO_IMAGE)
    obs = meta.to_observation()
    assert obs.taxon.id == 202860
    assert obs.id == 49459966


def test_empty_metadata():
    meta = MetaMetadata()
    assert meta.taxon_id is None
    assert meta.observation_id is None
    assert meta.has_taxon is False
    assert meta.has_observation is False
    assert meta.has_coordinates is False


def test_update__refreshes_derived_properties():
    meta = MetaMetadata(DEMO_IMAGE)
    assert meta.taxon_id == 202860
    meta.update({'Xmp.dwc.taxonID': '999999'})
    assert meta.combined['Xmp.dwc.taxonID'] == '999999'


def test_update__empty_is_noop():
    meta = MetaMetadata(DEMO_IMAGE)
    original_taxon_id = meta.taxon_id
    meta.update({})
    assert meta.taxon_id == original_taxon_id


def test_update_coordinates():
    meta = MetaMetadata(DEMO_IMAGE)
    new_coords = (51.5074, -0.1278)
    meta.update_coordinates(new_coords)
    assert meta.coordinates == new_coords

    meta.update_coordinates(None)
    assert meta.has_coordinates is False
