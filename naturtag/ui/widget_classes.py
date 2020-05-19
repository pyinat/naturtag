""" Stub classes for custom widgets and screens """
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout

from kivymd.uix.button import MDFloatingActionButton
from kivymd.uix.imagelist import SmartTileWithLabel
from kivymd.uix.list import ILeftBodyTouch
from kivymd.uix.screen import MDScreen
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.tooltip import MDTooltip

# Screen classes
class ImageSelectorScreen(MDScreen):
    pass

class SettingsScreen(MDScreen):
    pass

class MetadataViewScreen(MDScreen):
    pass

class TaxonSearchScreen(MDScreen):
    pass

class ObservationSearchScreen(MDScreen):
    pass


HOME_SCREEN = 'image_selector'
SCREENS = {
    HOME_SCREEN: ImageSelectorScreen,
    'settings': SettingsScreen,
    'metadata': MetadataViewScreen,
    'taxon_search': TaxonSearchScreen,
    'observation_search': ObservationSearchScreen,
}


# Controls & other UI elements
class IconLeftSwitch(ILeftBodyTouch, MDSwitch):
    pass

class TooltipFloatingButton(MDFloatingActionButton, MDTooltip):
    pass

class MetadataTab(BoxLayout, MDTabsBase):
    """ Class for a tab in a MDTabs view"""

class ImageMetaTile(SmartTileWithLabel):
    """ Class that contains an image thumbnail to display plus its associated metadata """
    metadata = ObjectProperty()
    original: StringProperty()
    allow_stretch = False
    box_color = [0, 0, 0, 0.4]

    def __init__(self, metadata, original, **kwargs):
        super().__init__(**kwargs)
        self.metadata = metadata
        self.original = original
