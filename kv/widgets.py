""" Stub classes for custom widgets and screens """
from kivy.uix.boxlayout import BoxLayout

from kivymd.uix.button import MDFloatingActionButton
from kivymd.uix.list import ILeftBodyTouch
from kivymd.uix.screen import MDScreen
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.tooltip import MDTooltip

class ImageSelectorScreen(MDScreen):
    pass

class SettingsScreen(MDScreen):
    pass

class IconLeftSwitch(ILeftBodyTouch, MDSwitch):
    pass

class TooltipFloatingButton(MDFloatingActionButton, MDTooltip):
    pass

class MetadataTab(BoxLayout, MDTabsBase):
    """ Class for a tab in a MDTabs view"""

class MetadataViewScreen(MDScreen):
    pass


HOME_SCREEN = 'image_selector'
SETTINGS_SCREEN = 'settings'
METADATA_SCREEN = 'metadata_view'
SCREENS = {
    SETTINGS_SCREEN: SettingsScreen,
    HOME_SCREEN: ImageSelectorScreen,
    METADATA_SCREEN: MetadataViewScreen,
}
