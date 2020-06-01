from kivy.properties import StringProperty
from kivy.uix.widget import Widget
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.tab import MDTabsBase, MDTabsLabel
from kivymd.uix.tooltip import MDTooltip

from naturtag.widgets import truncate


class Tab(MDBoxLayout, MDTabsBase):
    """ Class for a tab in a MDTabs view"""


# TODO: Not working
class TooltipTab(MDBoxLayout, MDTabsBase):
    """ Class for a tab in a MDTabs view"""
    tooltip_text = StringProperty()

    def __init__(self, **kwargs):
        self.padding = (0,0,0,0)
        self.tab_label = TooltipTabLabel(tab=self, tooltip_text=truncate(self.tooltip_text))
        Widget.__init__(self, **kwargs)


class TooltipTabLabel(MDTabsLabel, MDTooltip):
    """ Tab Label for MDTabs with tooltop behavior """

