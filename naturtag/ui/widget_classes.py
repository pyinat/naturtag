""" Stub classes for custom widgets and screens """
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.widget import Widget
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFloatingActionButton
from kivymd.uix.button import MDRoundFlatIconButton
from kivymd.uix.list import MDList, IconRightWidget, ILeftBodyTouch, OneLineListItem
from kivymd.uix.screen import MDScreen
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.tab import MDTabsBase, MDTabsLabel
from kivymd.uix.textfield import MDTextFieldRound
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
class SwitchListItem(ILeftBodyTouch, MDSwitch):
    """ Switch that works as a list item """

class TextInputListItem(OneLineListItem, MDTextFieldRound):
    """ Switch that works as a list item """

class TooltipFloatingButton(MDFloatingActionButton, MDTooltip):
    """ Floating action button class with tooltip behavior """

class TooltipIconButton(MDRoundFlatIconButton, MDTooltip):
    """ Flat button class with icon and tooltip behavior """


class StarButton(IconRightWidget):
    """
    Selectable icon button that optionally toggles between 'selected' and 'unselected' star icons
    """
    taxon_id = NumericProperty()
    is_selected = BooleanProperty()

    def __init__(self, taxon_id, is_selected=False, **kwargs):
        super().__init__(**kwargs)
        self.taxon_id = taxon_id
        self.is_selected = is_selected
        self.custom_icon = 'icon' in kwargs
        self.set_icon()

    def on_press(self):
        self.is_selected = not self.is_selected
        self.set_icon()

    def set_icon(self):
        if not self.custom_icon:
            self.icon = 'star' if self.is_selected else 'star-outline'


class SortableList(MDList):
    """ List class that can be sorted by a custom sort key """
    def __init__(self, sort_key=None, **kwargs):
        self.sort_key = sort_key
        super().__init__(**kwargs)

    def sort(self):
        """ Sort child items in-place using current sort key """
        children = self.children.copy()
        self.clear_widgets()
        for child in sorted(children, key=self.sort_key):
            self.add_widget(child)


class Tab(MDBoxLayout, MDTabsBase):
    """ Class for a tab in a MDTabs view"""


# TODO: Not working
class TooltipTab(MDBoxLayout, MDTabsBase):
    """ Class for a tab in a MDTabs view"""
    tooltip_text = StringProperty()

    def __init__(self, **kwargs):
        self.padding = (0,0,0,0)
        self.tab_label = TooltipTabLabel(tab=self, tooltip_text=self.tooltip_text)
        Widget.__init__(self, **kwargs)


class TooltipTabLabel(MDTabsLabel, MDTooltip):
    """ Tab Label for MDTabs with tooltop behavior """

