import os
from collections import Mapping
from logging import getLogger
# Set GL backend before any kivy modules are imported
os.environ['KIVY_GL_BACKEND'] = 'sdl2'

from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import DictProperty, StringProperty, BooleanProperty, ObjectProperty, Clock, NumericProperty
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.label import MDLabel

from kivymd.app import MDApp

from naturtag.app.screens import load_kv
from naturtag.constants import AUTOCOMPLETE_DELAY, AUTOCOMPLETE_MIN_CHARS

PADDING = dp(50)
ROW_SIZE = dp(22)
logger = getLogger().getChild(__name__)


class Root(MDBoxLayout):
    pass


class AutocompleteController(MDBoxLayout):
    """
    Class containing all components needed for autocomplete search.
    This manages an input field and a dropdown, so they don't interact with each other directly.
    Also includes rate-limited trigger for input delay (so we don't spam searches on every keypress).

    Must be inherited by a subclass that implements :py:meth:`get_autocomplete`.

    Events:
        on_selection: Called when a result is selected from the dropdown list
    """
    def __init__(self, text_input_kwargs=None, **kwargs):
        """
        Args:
            text_input_kwargs: Optional settings for :py:class:`.MDTextField`
        """
        super().__init__(**kwargs)
        Clock.schedule_once(lambda *x: self._post_init(text_input_kwargs or {}))

    def _post_init(self, text_input_kwargs):
        """ Finish initialization after populating children """
        self.trigger = Clock.create_trigger(self.callback, AUTOCOMPLETE_DELAY)

        # Re-open dropdown after clicking on input again (if there are previous results)
        self.text_input = self.ids.text_input
        self.text_input.bind(
            text=lambda *x: self.trigger(),
            focus=self.on_text_focus,
        )
        self.ids.clear_input_button.bind(on_release=self.reset)

        if text_input_kwargs:
            logger.debug(f'Overriding text input settings: {text_input_kwargs}')
            for k, v in text_input_kwargs.items():
                setattr(self.text_input, k, v)

        self.dropdown_view = self.ids.dropdown_view
        self.ids.dropdown_layout.bind(on_selection=lambda *x: self.update_selection(*x))
        self.ids.clear_input_button.bind(on_release=self.reset)

        self.dropdown_container = self.ids.dropdown_container
        # Re-open dropdown after clicking on input again (if there are previous results)
        self.text_input.bind(focus=self.on_text_focus)

        self.register_event_type('on_selection')

        # Debug buttons
        self.ids.button_up.bind(on_release=self.button_up)
        self.ids.button_down.bind(on_release=self.button_down)

    def button_up(self, *args):
        self.ids.input_layout.pos_hint = {k: v + .05 for k, v in self.ids.input_layout.pos_hint.items()}
        print(self.ids.input_layout.pos_hint)

    def button_down(self, *args):
        self.ids.input_layout.pos_hint = {k: v - .05 for k, v in self.ids.input_layout.pos_hint.items()}
        print(self.ids.input_layout.pos_hint)

    def on_text_focus(self, instance, *args):
        if instance.focus:
            logger.debug('Opening dropdown on text focus')
            self.dropdown_container.open()

    def callback(self, *args):
        """ Autocompletion callback, rate-limited by ``AUTOCOMPLETE_DELAY`` milliseconds """
        logger.debug('Populating autocomplete results')
        search_str = self.text_input.text
        if len(search_str) < AUTOCOMPLETE_MIN_CHARS:
            return

        def get_row(item):
            """ Return a row for dropdown list; use optional metadata if provided """
            if isinstance(item, Mapping):
                return item
            return {'text': item, 'suggestion_text': item, 'metadata': {}}

        matches = self.get_autocomplete(search_str)
        logger.info(f'Found {len(matches)} matches for search string "{search_str}"')
        self.dropdown_view.data = [get_row(i) for i in matches]
        self.dropdown_container.open()
        # self.height = dp(500)

    # TODO: formatting for suggestion_text; smaller text + different color
    def update_selection(self, instance, suggestion_text, metadata):
        """ Intermediate handler to update suggestion text based on dropdown selection """
        self.text_input.suggestion_text = '    ' + suggestion_text
        self.dispatch('on_selection', metadata)
        Clock.schedule_once(self.dropdown_container.dismiss, 0.2)

    def on_selection(self, metadata):
        """  Called when a result is selected from the dropdown list """

    def get_autocomplete(self, search_str):
        return [{'text': f'Text: {search_str}'}] + [{'text': f'Text: {i}'} for i in range(9)]

    def reset(self, *args):
        """ Reset inputs and autocomplete results """
        self.text_input.text = ''
        self.text_input.suggestion_text = ''
        self.dropdown_view.data = []


class DropdownContainer(MDBoxLayout):
    """ Container layout that wraps dropdown with 'open' and 'dismiss' functionality """
    caller = ObjectProperty()
    layout = ObjectProperty()
    view = ObjectProperty()
    max_height = NumericProperty(500)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(on_resize=self.reset_layout_size)
        self._calculate_complete = False
        self.start_coords = [0, 0]
        self._data = []
        self.is_open = False

    def reset_layout_size(self, *args):
        """ When the window is resized, re-calculate properties """
        self._calculate_complete = False

    def set_layout_size(self):
        self.start_coords = self.caller.to_window(*self.caller.pos)
        print('Coords:', self.start_coords, self.caller.pos, self.caller.center_x, self.caller.center_y)
        # 'default_size' is the size of EACH ROW!? This took HOURS to debug!
        self.layout.default_size = self.caller.width, ROW_SIZE
        # self.layout.pos = PADDING, 0
        self._calculate_complete = True

    def open(self):
        logger.debug(f'Opening dropdown at {self.layout.center_x}, {self.layout.center_y}')
        print('Text pos:', self.caller.center_x, self.caller.center_y)
        if not self._calculate_complete:
            self.set_layout_size()
        # Re-opening without any changes to data
        if self._data and not self.view.data:
            self.view.data = self._data
        self.is_open = True

    def dismiss(self, *args):
        # Temporarily store data and remove from RecycleView to resize it
        self._data = self.view.data
        self.view.data = []
        self.is_open = False


class DropdownLayout(FocusBehavior, LayoutSelectionBehavior, RecycleBoxLayout):
    """
    Class that adds selection and focus behaviour to a dropdown list. Using a RecycleBoxLayout
    because other options (like :py:class:`.MDDropdownList`) are inefficient for frequently
    changing contents.

    Events:
        on_selection: Called when a result is selected from the dropdown list
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_event_type('on_selection')

    def on_selection(self, suggestion_text, metadata):
        """  Called when a result is selected from the dropdown list """


class DropdownItem(RecycleDataViewBehavior, MDLabel):
    """
    A label representing a dropdown item, which handles click events.
    Optionally contains additional metadata to associate with the item.
    """
    index = None
    selectable = True
    is_selected = BooleanProperty(False)
    suggestion_text = StringProperty()
    metadata = DictProperty()

    def refresh_view_attrs(self, rv, index, data):
        """ Catch and handle view changes """
        self.index = index
        return super().refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        """ Add selection on click. ``on_selection`` event is raised here instead of in
        :py:meth:`.apply_selection` in order to handle only real selection events and not
        automatic selection checks.
         """
        if super().on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            logger.debug(f'Selecting item {self.text}')
            self.parent.select_with_touch(self.index, touch)
            self.parent.dispatch('on_selection', self.suggestion_text, self.metadata)
            return True

    def apply_selection(self, dropdown_view, index, is_selected):
        """ Respond to the selection of items in the view """
        self.is_selected = is_selected


class TestApp(MDApp):
    def build(self):
        load_kv('testapp')
        root = Root()
        root.ids.autocomplete_controller.bind(on_selection=lambda *x: print('HOOK:', *x))
        return root


if __name__ == '__main__':
    TestApp().run()
