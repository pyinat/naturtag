""" Stub classes for custom widgets and screens """
from kivymd.uix.list import ILeftBodyTouch
from kivymd.uix.screen import MDScreen
from kivymd.uix.selectioncontrol import MDSwitch

class ImageSelectorScreen(MDScreen):
    pass

class SettingsScreen(MDScreen):
    pass

class IconLeftSwitch(ILeftBodyTouch, MDSwitch):
    pass

SCREENS = {'settings': SettingsScreen, 'image_selector': ImageSelectorScreen}
