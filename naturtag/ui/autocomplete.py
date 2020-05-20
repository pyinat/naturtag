# Generic/reusable autocomplete components
# Ideas for autocomplete layout originally taken from:
# https://www.reddit.com/r/kivy/comments/99n2ct/anyone_having_idea_for_autocomplete_feature_in/e4phtf8/
from logging import getLogger

from kivy.clock import Clock
from kivy.properties import BooleanProperty, ObjectProperty
from kivy.uix.behaviors import FocusBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview.layout import LayoutSelectionBehavior

from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField

from naturtag.constants import AUTOCOMPLETE_DELAY, AUTOCOMPLETE_MIN_CHARS

# Set dropdown size large enough for 10 results; if there are any more than that, use scrollbar
DROPDOWN_ITEM_SIZE = 22
MAX_DROPDOWN_SIZE = 10 * 22 + 50

logger = getLogger().getChild(__name__)


class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior, RecycleBoxLayout):
    """ Class that adds selection and focus behaviour to a dropdown list """


class AutocompleteSearch(MDBoxLayout):
    """
    Layout class containing components needed for autocomplete search.
    This manages an input field and a dropdown, so they don't interact with each other directly.
    Also includes rate-limited trigger for input delay (so we don't spam searches on every keypress).

    Must be inherited by a subclass that implements :py:meth:`get_autocomplete`.
    """
    input = ObjectProperty()
    dropdown = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.trigger = Clock.create_trigger(self.callback, AUTOCOMPLETE_DELAY)

    def callback(self, *args):
        """ Autocompletion callback, rate-limited by ``AUTOCOMPLETE_DELAY`` milliseconds """
        seatch_str = self.input.text
        if len(seatch_str) < AUTOCOMPLETE_MIN_CHARS:
            return

        matches = self.get_autocomplete(seatch_str)
        logger.info(f'Found {len(matches)} matches for search string "{seatch_str}"')
        self.dropdown.data = [{'text': i} for i in matches]
        self.height = min(MAX_DROPDOWN_SIZE, (len(matches) * DROPDOWN_ITEM_SIZE) + 50)

    def get_autocomplete(self, search_str):
        """ Autocompletion behavior to be implemented by a subclass """
        raise NotImplementedError

    def update_selection(self, selection):
        """ Intermediate handler to update suggestion text based on dropdown selection """
        logger.info(f'Updating selection: {selection}')
        self.input.suggestion_text = (selection or {}).get('text', '')


class DropdownItem(RecycleDataViewBehavior, MDLabel):
    """ A label that handles click events """
    index = None
    is_selected = BooleanProperty(False)
    selectable = True

    def refresh_view_attrs(self, rv, index, data):
        """ Catch and handle view changes """
        self.index = index
        return super().refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        """ Add selection on click """
        if super().on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, dropdown, index, is_selected):
        """ Respond to the selection of items in the view """
        self.is_selected = is_selected
        # TODO: Is there a better way of referencing AutocompleteSearch than parent.parent.parent?
        if is_selected:
            self.parent.parent.parent.update_selection(dropdown.data[index])


class SearchInput(MDTextField):
    """ A text input field for autocomplete search. """
    def on_text(self, instance, value):
        """ Trigger an autocomplete query, unless one has been triggered immediately prior """
        self.parent.trigger()

    # TODO: Not really working as intended yet
    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        """ Select an autocomplete match with the tab key """
        if self.suggestion_text and keycode[1] == 'tab':
            self.insert_text(self.suggestion_text + ' ')
            return True
        return super().keyboard_on_key_down(window, keycode, text, modifiers)
