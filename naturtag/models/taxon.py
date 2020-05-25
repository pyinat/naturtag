from os.path import join
from pyinaturalist.node_api import get_taxa_by_id
from naturtag.constants import TAXON_BASE_URL, ICONS_DIR, ICONIC_TAXA
from naturtag.models.base import JsonModel


class Taxon(JsonModel):
    """ A model containing basic information about a taxon """
    def __init__(self, json_result=None, id=None):
        """
        Construct a Taxon object from an API response result. Accounts for both full and partial
        records from :py:func:`get_taxa` and :py:func:`get_taxa_autocomplete`, respectively.
        Will lazy-load additional info as needed.

        Args:
            json_result (dict): JSON from API response item
            id (int): Initialize with just a taxon ID to fetch remaining info
        """
        super().__init__(json_result=json_result, id=id)

        photo = self.json.get('default_photo') or {}  # Attribute could be present but set to null
        self.photo_url = photo.get('medium_url')
        self.thumbnail_url = photo.get('square_url')
        self._ancestors = None
        self._children = None

    def get_full_record(self, id=None):
        """ If this is a partial record, update with the full record """
        r = get_taxa_by_id(id or self.id)
        self.json = r['results'][0]
        return self.json

    @property
    def common_name(self):
        return self.json.get('preferred_common_name', '')

    @property
    def icon_path(self):
        return get_icon_path(self.iconic_taxon_id)

    @property
    def link(self):
        return f'{TAXON_BASE_URL}/{self.id}'

    @property
    def ancestors(self):
        """ Get this taxon's ancestors as Taxon objects (in descending order of rank) """
        if self._ancestors is None:
            if 'ancestors' not in self.json:
                self.get_full_record()
            self._ancestors = [Taxon(t) for t in self.json.get('ancestors', [])]
        return self._ancestors

    @property
    def parent(self):
        """ Return immediate parent, if any """
        return self.ancestors[-1] if self.ancestors else None

    @property
    def children(self):
        """ Get this taxon's children as Taxon objects (in descending order of rank) """
        if self._children is None:
            # TODO: Determine if it's already a full record but the taxon has no children?
            if 'children' not in self.json:
                self.get_full_record()
            self._children = [Taxon(t) for t in self.json.get('children', [])]
        return self._children


def get_icon_path(id):
    """ An iconic function to return an icon for an iconic taxon """
    if id not in ICONIC_TAXA:
        return None
    return join(ICONS_DIR, f'{ICONIC_TAXA[id]}.png')
