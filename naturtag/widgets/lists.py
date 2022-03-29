from logging import getLogger

from kivy.core.clipboard import Clipboard
from kivy.core.image import Image as CoreImage
from kivy.uix.image import AsyncImage
from kivymd.uix.list import (
    IconRightWidget,
    ILeftBody,
    ILeftBodyTouch,
    ImageLeftWidget,
    IRightBodyTouch,
    MDList,
    ThreeLineAvatarIconListItem,
)
from kivymd.uix.selectioncontrol import MDSwitch

from naturtag.app import alert, get_app
from naturtag.constants import TAXON_ICON_PLACEHOLDER
from naturtag.models import Taxon

logger = getLogger().getChild(__name__)


class SortableList(MDList):
    """List class that can be sorted by a custom sort key"""

    def __init__(self, sort_key=None, **kwargs):
        self.sort_key = sort_key
        super().__init__(**kwargs)

    def sort(self):
        """Sort child items in-place using current sort key"""
        children = self.children.copy()
        self.clear_widgets()
        for child in sorted(children, key=self.sort_key):
            self.add_widget(child)


class SwitchListItemLeft(ILeftBodyTouch, MDSwitch):
    """Switch that works as a list item"""


class SwitchListItemRight(IRightBodyTouch, MDSwitch):
    """Switch that works as a list item"""


# TODO: Create placeholder item with 'loading taxon {id}', then update with full info/image?
class TaxonListItem(ThreeLineAvatarIconListItem):
    """Class that displays condensed taxon info as a list item"""

    def __init__(
        self,
        taxon: Taxon = None,
        image: CoreImage = None,
        disable_button: bool = False,
        highlight_observed: bool = True,
        **kwargs,
    ):
        self.disable_button = disable_button
        self.highlight_observed = highlight_observed
        super().__init__(font_style='H6', text='Loading...', **kwargs)

        if taxon:
            self.set_taxon(taxon)
        if image:
            self.set_image(image)
        # Placeholder thumbnail
        else:
            self.add_widget(ImageLeftWidget(source=TAXON_ICON_PLACEHOLDER))

        # Set right-click event unless disabled
        if not disable_button:
            self.bind(on_touch_down=self._on_touch_down)

    def set_taxon(self, taxon: Taxon):
        """Update taxon info"""
        self.taxon = taxon
        self.text = taxon.name
        self.secondary_text = taxon.rank
        self.tertiary_text = taxon.preferred_common_name

        # Add user icon if taxon has been observed by the user
        if self.highlight_observed and get_app().is_observed(taxon.id):
            self.add_widget(IconRightWidget(icon='account-search'))

    def set_image(self, image: CoreImage):
        self.ids._left_container.clear_widgets()
        self.add_widget(ThumbnailListItem(image=image))

    def _on_touch_down(self, instance, touch):
        """Copy text on right-click"""
        if not self.collide_point(*touch.pos):
            return
        elif touch.button == 'right':
            Clipboard.copy(self.text)
            alert('Copied to clipboard')
        else:
            super().on_touch_down(touch)


# class ThumbnailListItem(ImageLeftWidget):
# class ThumbnailListItem(CachedAsyncImage, ILeftBody):
# class ThumbnailListItem(CustomImage, ILeftBody):
class ThumbnailListItem(AsyncImage, ILeftBody):
    """List item that contains a taxon thumbnail. Can be initialized from either a source or
    existing Image object.
    """

    def __init__(self, source: str = '', image: CoreImage = None, **kwargs):
        super().__init__(source=source, **kwargs)
        if image:
            self.texture = image.texture
            self.reload()
