""" Custom widgets and stub classes """
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.widget import Widget

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFloatingActionButton
from kivymd.uix.button import MDRoundFlatIconButton
from kivymd.uix.list import MDList, IconRightWidget, ILeftBodyTouch, OneLineListItem
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.tab import MDTabsBase, MDTabsLabel
from kivymd.uix.textfield import MDTextFieldRound
from kivymd.uix.tooltip import MDTooltip

from naturtag.constants import MAX_LABEL_CHARS


class SwitchListItem(ILeftBodyTouch, MDSwitch):
    """ Switch that works as a list item """

class TextInputListItem(OneLineListItem, MDTextFieldRound):
    """ Switch that works as a list item """

class TooltipFloatingButton(MDFloatingActionButton, MDTooltip):
    """ Floating action button class with tooltip behavior """

class TooltipIconButton(MDRoundFlatIconButton, MDTooltip):
    """ Flat button class with icon and tooltip behavior """


class DropdownTextField(MDDropdownMenu):
    """ A dropdown menu class that includes basic interaction with a text input field """
    def __init__(self, *args, text_input=None, text_items=None, add_none_item=True, **kwargs):
        """
        Adds an extra ``text_items`` parameter for text-only items, ``text_input`` instead of
        ``caller``, just to be more explicit, and some size defaults
        """
        # Convert str list to dict, if specified
        if text_items:
            kwargs['items'] = [{'text': i} for i in text_items]
        # Add a 'None' item to the top of the list to deselect it
        if add_none_item:
            kwargs['items'].insert(0, {'text': 'None'})

        kwargs['callback'] = self.set_rank_input
        kwargs['caller'] = text_input
        kwargs.setdefault('max_height', 400)
        kwargs.setdefault('width_mult', 4)
        kwargs.setdefault('hor_growth', 'right')

        self.text_input = text_input
        self.text_input.bind(focus=self.open_on_focus)
        super().__init__(*args, **kwargs)

    def open_on_focus(self, instance, *args):
        """ Open the dropdown if the given instance has focus """
        # Setting the text input before losing focus coerces the 'hint text' to behave as expected
        self.text_input.text = self.text_input.text or '  '
        if instance.focus:
            self.open()

    def on_dismiss(self):
        super().on_dismiss()
        # If we set whitespace as a placeholder but didn't select anything, revert
        if self.text_input.text == '  ':
            self.text_input.text = ''

    def set_rank_input(self, dropdown_item):
        """ On clicking a dropdown item, populate the text field's text """
        # Selecting the 'None' item removes any previous selection
        self.text_input.text = dropdown_item.text.replace('None', '')
        self.dismiss()


# TODO: Debug root cause of rogue tooltips!
class HideableTooltip(MDTooltip):
    """
    This is a workaround for unexpected bahvior with tooltips and tabs. If a HideableTooltip is
    in an unselected tab, it will always report that the mouse cursor does not intersect it.
    """
    def __init__(self, is_visible_callback, **kwargs):
        self.is_visible_callback = is_visible_callback
        super().__init__(**kwargs)

    def on_mouse_pos(self, *args):
        if self.is_visible_callback():
            super().on_mouse_pos(*args)


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
        self.tab_label = TooltipTabLabel(tab=self, tooltip_text=truncate(self.tooltip_text))
        Widget.__init__(self, **kwargs)


class TooltipTabLabel(MDTabsLabel, MDTooltip):
    """ Tab Label for MDTabs with tooltop behavior """


def truncate(text):
    """ Truncate a label string to not exceed maximum length """
    if len(text) > MAX_LABEL_CHARS:
        text = text[:MAX_LABEL_CHARS - 2] + '...'
    return text
