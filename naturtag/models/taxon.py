import attr
from pyinaturalist import ICONIC_TAXA, define_model, get_taxa_by_id
from pyinaturalist.models import Taxon as BaseTaxon

from naturtag.atlas import get_atlas_uri
from naturtag.constants import ATLAS_APP_ICONS


@define_model
class Taxon(BaseTaxon):
    partial: bool = attr.field(default=True)

    @classmethod
    def from_id(cls, id: int):
        """Lookup and create a new Taxon object from an ID"""
        r = get_taxa_by_id(id)
        return cls.from_json(r['results'][0])

    def update_from_full_record(self):
        t = Taxon.from_id(self.id)
        for key in attr.fields_dict(self.__class__).keys():
            setattr(self, key, getattr(t, key))

    @property
    def icon_path(self) -> str:
        return get_icon_path(self.iconic_taxon_id)

    @property
    def parent_taxa(self) -> list['Taxon']:
        """Get this taxon's ancestors (in descending order of rank)"""
        if not self.ancestors and self.partial:
            self.update_from_full_record()
            self.partial = False
        return self.ancestors or []

    @property
    def parent(self):
        """Return immediate parent, if any"""
        return self.parent_taxa[-1] if self.parent_taxa else None

    @property
    def child_taxa(self) -> list['Taxon']:
        """Get this taxon's children (in descending order of rank)"""
        if not self.children and self.partial:
            self.update_from_full_record()
            self.partial = False
        return self.children or []

    @property
    def child_ids(self) -> list[int]:
        return [t.id for t in self.child_taxa]


def get_icon_path(taxon_id: int) -> str:
    """An iconic function to return an icon for an iconic taxon"""
    if taxon_id not in ICONIC_TAXA:
        taxon_id = 0
    image_id = ICONIC_TAXA[taxon_id].lower()
    return get_atlas_uri(ATLAS_APP_ICONS, image_id)
