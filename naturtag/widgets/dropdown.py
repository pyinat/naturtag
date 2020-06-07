from os.path import join

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.properties import (
    NumericProperty,
    ListProperty,
    OptionProperty,
    StringProperty,
    ObjectProperty,
    BooleanProperty,
)

import kivymd.material_resources as m_res
from kivymd.theming import ThemableBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import (
    OneLineAvatarIconListItem,
    IRightBodyTouch,
    OneLineListItem,
)

from naturtag.constants import KV_SRC_DIR

Builder.load_file(join(KV_SRC_DIR, 'dropdown.kv'))


class MDMenuItem(OneLineListItem):
    icon = StringProperty()


class MDMenu(ScrollView):
    width_mult = NumericProperty(1)


class AutocompleteDropdownMenu(ThemableBehavior, FloatLayout):
    items = ListProperty()
    width_mult = NumericProperty(1)
    max_height = NumericProperty()
    border_margin = NumericProperty("4dp")
    background_color = ListProperty()
    opening_transition = StringProperty("out_cubic")
    opening_time = NumericProperty(0.2)
    caller = ObjectProperty()
    callback = ObjectProperty()
    position = OptionProperty("auto", options=["auto", "center", "bottom"])
    _start_coords = []
    _calculate_process = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(on_resize=self.check_position_caller)
        self.register_event_type("on_dismiss")
        self.menu = self.ids.md_menu
        self.set_menu_properties()

    def check_position_caller(self, instance, width, height):
        self.set_menu_properties(0)

    def create_menu_items(self):
        """Creates menu items."""
        for data in self.items:
            item = MDMenuItem(
                text=data.get("text", ""),
                icon=data.get("icon", ""),
                divider=data.get("divider", "Full"),
            )
            if self.callback:
                item.bind(on_release=self.callback)
            self.menu.ids.box.add_widget(item)

    def set_menu_properties(self, interval):
        """Sets the size and position for the menu window."""
        if not self.menu.ids.box.children:
            self.create_menu_items()
        # We need to pick a starting point, see how big we need to be, and where to grow to.
        self._start_coords = self.caller.to_window(self.caller.center_x, self.caller.center_y)
        self.target_width = self.caller.width

        self.target_height = sum([dp(56) for i in self.items])
        # If we're over max_height...
        if 0 < self.max_height < self.target_height:
            self.target_height = self.max_height

    def open(self):
        """Animate the opening of a menu window."""

        def open(interval):
            if not self._calculate_complete:
                return
            # Position: center
            self.menu.pos = (
                self._start_coords[0] - self.target_width / 2,
                self._start_coords[1] - self.target_height / 2,
            )
            anim = Animation(
                width=self.target_width,
                height=self.target_height,
                duration=self.opening_time,
                opacity=1,
                transition=self.opening_transition,
            )
            anim.start(self.menu)
            Window.add_widget(self)
            Clock.unschedule(open)
            self._calculate_process = False

        if not self._calculate_process:
            self._calculate_process = True
            Clock.schedule_interval(open, 0)

    def on_touch_down(self, touch):
        if not self.menu.collide_point(*touch.pos):
            self.dispatch("on_dismiss")
            return True
        super().on_touch_down(touch)
        return True

    def on_touch_move(self, touch):
        super().on_touch_move(touch)
        return True

    def on_touch_up(self, touch):
        super().on_touch_up(touch)
        return True

    def on_dismiss(self):
        Window.remove_widget(self)
        self.menu.width = 0
        self.menu.height = 0
        self.menu.opacity = 0

    def dismiss(self):
        self.on_dismiss()
