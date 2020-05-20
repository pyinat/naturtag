# Ideas for autocomplete layout taken from:
# https://www.reddit.com/r/kivy/comments/99n2ct/anyone_having_idea_for_autocomplete_feature_in/e4phtf8/
import os
from logging import getLogger
os.environ['KIVY_GL_BACKEND'] = 'sdl2'

from kivy.clock import Clock
from kivy.properties import BooleanProperty, ObjectProperty
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview.layout import LayoutSelectionBehavior

from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField

from pyinaturalist.node_api import get_taxa_autocomplete
from naturtag.constants import AUTOCOMPLETE_DELAY, AUTOCOMPLETE_MIN_CHARS

logger = getLogger().getChild(__name__)


class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior, RecycleBoxLayout):
    """ Class to add selection and focus behaviour to a view """

class SelectableLabel(RecycleDataViewBehavior, MDLabel):
    """ A label that handles click events """
    index = None
    selectable = True
    is_selected = BooleanProperty(False)

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

    def apply_selection(self, rv, index, is_selected):
        """ Respond to the selection of items in the view. """
        self.is_selected = is_selected
        if is_selected:
            logger.info(f'selection changed to {rv.data[index]}')  # TODO: debug


class AutocompleteInput(MDTextField):
    dropdown = ObjectProperty()
    suggestion_text = ''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.trigger = Clock.create_trigger(self.callback, AUTOCOMPLETE_DELAY)

    def callback(self, *args):
        matches = self.get_autocomplete(self.text)
        logger.info(f'Found {len(matches)} matches for search string "{self.text}"')
        self.dropdown.data = [{'text': i} for i in matches]
        self.parent.height = min(240, 50 + (len(matches) * 20))

    def get_autocomplete(self, search_str):
        raise NotImplementedError

    def on_text(self, instance, value):
        if len(value) >= AUTOCOMPLETE_MIN_CHARS:
            self.trigger()

    # TODO: Set suggestion_text on select
    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        if self.suggestion_text and keycode[1] == 'tab':
            self.insert_text(self.suggestion_text + ' ')
            return True
        return super().keyboard_on_key_down(window, keycode, text, modifiers)


class TaxonAutocompleteInput(AutocompleteInput):
    def get_autocomplete(self, search_str):
        return get_taxa_autocomplete(q=search_str, minify=True).get('results', [])
