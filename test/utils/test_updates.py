from unittest.mock import patch

import pytest
import requests

from naturtag.constants import RELEASES_API_URL
from naturtag.utils.updates import check_for_update

RELEASE_URL = 'https://github.com/pyinat/naturtag/releases/tag/v0.8.0'

SAMPLE_RELEASE_RESPONSE = {
    'tag_name': 'v0.8.0',
    'html_url': RELEASE_URL,
    'name': 'v0.8.0',
    'draft': False,
    'prerelease': False,
    'assets': [
        {
            'name': 'naturtag-0.8.0-x86_64.AppImage',
            'browser_download_url': 'https://github.com/pyinat/naturtag/releases/download/v0.8.0/naturtag-0.8.0-x86_64.AppImage',
        },
    ],
}


@pytest.mark.parametrize(
    'current_version, tag_name, expected',
    [
        ('0.7.0', 'v0.8.0', ('0.8.0', RELEASE_URL)),
        ('0.8.0', 'v0.8.0', None),
        ('0.9.0', 'v0.8.0', None),
        ('0.7.0', '0.8.0', ('0.8.0', RELEASE_URL)),
    ],
    ids=['newer_available', 'already_up_to_date', 'ahead_of_latest', 'tag_without_v_prefix'],
)
def test_check_for_update(current_version, tag_name, expected, requests_mock):
    response = {**SAMPLE_RELEASE_RESPONSE, 'tag_name': tag_name}
    requests_mock.get(RELEASES_API_URL, json=response)

    with patch('naturtag.utils.updates.get_version', return_value=current_version):
        result = check_for_update()

    assert result == expected


@pytest.mark.parametrize(
    'mock_kwargs, expected_exc',
    [
        ({'exc': requests.ConnectionError}, requests.ConnectionError),
        ({'status_code': 404}, requests.HTTPError),
    ],
    ids=['network_error', 'http_error'],
)
def test_check_for_update__request_error(mock_kwargs, expected_exc, requests_mock):
    requests_mock.get(RELEASES_API_URL, **mock_kwargs)

    with (
        patch('naturtag.utils.updates.get_version', return_value='0.7.0'),
        pytest.raises(expected_exc),
    ):
        check_for_update()
