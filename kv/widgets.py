""" Stub classes for custom widgets and screens """
from kivymd.uix.button import MDFloatingActionButton
from kivymd.uix.list import ILeftBodyTouch
from kivymd.uix.screen import MDScreen
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.tooltip import MDTooltip

class ImageSelectorScreen(MDScreen):
    pass

class SettingsScreen(MDScreen):
    pass

class IconLeftSwitch(ILeftBodyTouch, MDSwitch):
    pass

class TooltipFloatingButton(MDFloatingActionButton, MDTooltip):
    pass

SCREENS = {'settings': SettingsScreen, 'image_selector': ImageSelectorScreen}
