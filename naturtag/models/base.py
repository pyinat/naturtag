from collections.abc import Collection


class JsonModel:
    """ Class representing a model build from a JSON response object """
    def __init__(self, json_result=None, id=None):
        if not json_result and id:
            json_result = self.get_full_record(id)
        self.json = json_result

        # Set all response attributes as instance attributes, except nested dicts & lists
        for k, v in (json_result or {}).items():
            if isinstance(v, str) or not isinstance(v, Collection):
                self.__setattr__(k, v)

    def get_full_record(self, id=None):
        raise NotImplementedError
