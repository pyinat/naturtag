from collections.abc import Collection

from pyinaturalist.node_api import get_taxa_by_id


class JsonModel:
    """ Class representing a model build from a JSON response object """
    def __init__(self, json_result):
        """ Sets all response attributes as instance attributes, except nested dicts & lists """
        self.json = json_result
        for k, v in (json_result or {}).items():
            if isinstance(v, str) or not isinstance(v, Collection):
                self.__setattr__(k, v)


class Taxon(JsonModel):
    """ A model containing basic information about a taxon """
    def __init__(self, json_result=None, id=None):
        """
        Construct a Taxon object from an API response result. Accounts for both full and partial
        records from :py:func:`get_taxa` and :py:func:`get_taxa_autocomplete`, respectively.
        Will lazy-load additional info as needed.

        Alternatively, this class can be initialized with just an ID to fetch remaining info.
        """
        if not json_result and id:
            json_result = self.get_full_record(id)
        super().__init__(json_result)

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
    def ancestors(self):
        """ Get this taxon's ancestors as Taxon objects (in descending order of rank) """
        if self._ancestors is None:
            if 'ancestors' not in self.json:
                self.get_full_record()
            self._ancestors = [Taxon(t) for t in self.json.get('ancestors', [])]
        return self._ancestors

    @property
    def children(self):
        """ Get this taxon's children as Taxon objects (in descending order of rank) """
        if self._children is None:
            # TODO: Determine if it's already a full record but the taxon has no children?
            if 'children' not in self.json:
                self.get_full_record()
            self._children = [Taxon(t) for t in self.json.get('children', [])]
        return self._children
