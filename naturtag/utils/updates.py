from importlib.metadata import version as pkg_version

import requests
from packaging.version import Version

from naturtag.constants import RELEASES_API_URL


def check_for_update() -> tuple[str, str] | None:
    """Check if a newer version of Naturtag is available on GitHub.

    Returns:
        A ``(latest_version, release_url)`` tuple if a newer version exists,
        or ``None`` if the installed version is already up-to-date.

    Raises:
        requests.RequestException: On network errors.
        KeyError: If the response JSON is missing expected fields.
    """
    response = requests.get(RELEASES_API_URL, timeout=20)
    response.raise_for_status()
    data = response.json()

    tag = data['tag_name'].lstrip('v')
    release_url = data['html_url']

    current = Version(get_version())
    latest = Version(tag)

    if latest > current:
        return (tag, release_url)
    return None


def get_version() -> str:
    return pkg_version('naturtag')
