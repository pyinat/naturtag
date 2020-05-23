from pyinaturalist.node_api import get_observation
from naturtag.constants import OBSERVATION_BASE_URL
from naturtag.models.base import JsonModel


class Observation(JsonModel):
    def __init__(self, json_result=None, id=None):
        """
        Construct an Observation object from an API response from :py:func:`get_observations`.
        Will lazy-load additional info as needed.

        Alternatively, this class can be initialized with just an ID to fetch remaining info.
        """
        super().__init__(json_result=json_result, id=id)
