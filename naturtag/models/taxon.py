from pathlib import Path

import attr
from pyinaturalist import ICONIC_TAXA, define_model
from pyinaturalist.models import Taxon as BaseTaxon

from naturtag.constants import ICONIC_TAXA_DIR


# TODO: Move copy() to pyinaturalist.Taxon, reuse in load_full_record()
# TODO: Is there a better way to do this? Like static functions instead of Taxon subclass?
@define_model
class Taxon(BaseTaxon):
    """Taxon subclass with some additional features specific to Naturtag"""

    partial: bool = attr.field(default=True)

    # TODO: Can use and cache .icon_url instead
    @property
    def icon_path(self) -> str:
        return get_icon_path(self.iconic_taxon_id)

    @property
    def parent_taxa(self) -> list['Taxon']:
        """Get this taxon's ancestors (in descending order of rank)"""
        if not self.ancestors and self.partial:
            self.load_full_record()
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
            self.load_full_record()
            self.partial = False
        return self.children or []

    @property
    def child_ids(self) -> list[int]:
        return [t.id for t in self.child_taxa]


def get_icon_path(taxon_id: int) -> Path:
    """An iconic function to return an icon for an iconic taxon"""
    if taxon_id not in ICONIC_TAXA:
        taxon_id = 0
    image_name = ICONIC_TAXA[taxon_id].lower()
    return ICONIC_TAXA_DIR / f'{image_name}.png'
