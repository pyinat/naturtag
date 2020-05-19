""" Main Kivy application """
import logging
import os
import sys
from os.path import join

# Set GL backend before any kivy modules are imported
os.environ['KIVY_GL_BACKEND'] = 'sdl2'

# Disable multitouch emulation before any other kivy modules are imported
from kivy.config import Config
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivymd.app import MDApp

from naturtag.constants import (
    KV_SRC_DIR, INIT_WINDOW_SIZE, MD_PRIMARY_PALETTE, MD_ACCENT_PALETTE, BACKSPACE, F11)
from naturtag.ui.controller import Controller, alert
from naturtag.ui.search_controller import SearchController
from naturtag.ui.widget_classes import SCREENS, HOME_SCREEN

logger = logging.getLogger('naturtag.' + __name__)
logger.setLevel('DEBUG')
out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter('[%(levelname)s] %(funcName)s %(asctime)s %(message)s'))
out_hdlr.setLevel(logging.INFO)
logger.addHandler(out_hdlr)


class ImageTaggerApp(MDApp):
    """
    Manages window, theme, main screen and navigation state; other application logic is
    handled by Controller
    """
    controller = ObjectProperty()
    nav_drawer = ObjectProperty()
    screen_manager = ObjectProperty()
    toolbar = ObjectProperty()

    def build(self):
        # Init screens and store references to them
        screens = {}
        Builder.load_file(join(KV_SRC_DIR, 'main.kv'))
        for screen_name, screen_cls in SCREENS.items():
            screen_path = join(KV_SRC_DIR, f'{screen_name}.kv')
            Builder.load_file(screen_path)
            screens[screen_name] = screen_cls()
            logger.info(f'Loaded screen {screen_path}')

        # Init controller with references to nested screen objects for easier access
        controller = Controller(
            inputs=screens[HOME_SCREEN].ids,
            image_previews=screens[HOME_SCREEN].ids.image_previews,
            file_chooser=screens[HOME_SCREEN].ids.file_chooser,
            settings=screens['settings'].ids,
            metadata_tabs=screens['metadata'].ids,
        )
        search_controller = SearchController(
            taxon_inputs=screens['taxon_search'].ids.taxon_search_input.ids,
            observation_inputs=screens['observation_search'].ids.observation_search_input.ids,
        )

        # Init screen manager and nav elements
        self.nav_drawer = controller.ids.nav_drawer
        self.screen_manager = controller.ids.screen_manager
        self.toolbar = controller.ids.toolbar
        for screen_name, screen in screens.items():
            self.screen_manager.add_widget(screen)
            if screen_name.endswith('_search'):
                screen.controller = search_controller
            else:
                screen.controller = controller
        self.home()

        # Set some event bindings that can't (easily) by done in kvlang
        controller.settings.dark_mode_chk.bind(active=self.toggle_dark_mode)
        controller.image_previews.bind(minimum_height=controller.image_previews.setter('height'))

        # Set Window and theme settings
        Window.size = INIT_WINDOW_SIZE
        Window.bind(on_dropfile=controller.add_image)
        Window.bind(on_keyboard=self.on_keyboard)
        self.theme_cls.primary_palette = MD_PRIMARY_PALETTE
        self.theme_cls.accent_palette = MD_ACCENT_PALETTE

        alert(  # TODO: make this disappear as soon as an image or another screen is selected
            f'.{" " * 14}Drag and drop images or select them from the file chooser', duration=7
        )
        self.controller = controller
        return controller

    def home(self, *args):
        self.switch_screen(HOME_SCREEN)

    def open_nav(self, *args):
        self.nav_drawer.set_state('open')

    def close_nav(self, *args):
        self.nav_drawer.set_state('close')

    def switch_screen(self, screen_name):
        self.screen_manager.current = screen_name
        self.update_toolbar(screen_name)
        self.close_nav()

    def on_keyboard(self, window, key, scancode, codepoint, modifier):
        """ Handle keyboard shortcuts """
        # logger.info(key, scancode, codepoint, modifier)
        if (modifier, key) == (['ctrl'], BACKSPACE):
            self.home()
        elif (modifier, codepoint) == (['ctrl'], 'o'):
            pass  # TODO: Open kivymd file manager
        elif (modifier, codepoint) == (['ctrl'], 'q'):
            self.stop()
        elif (modifier, codepoint) == (['ctrl'], 'r'):
            self.controller.run()
        elif (modifier, codepoint) == (['ctrl'], 's'):
            self.switch_screen('settings')
        elif (modifier, codepoint) == (['shift', 'ctrl'], 'x'):
            self.controller.clear()
        elif key == F11:
            self.toggle_fullscreen()

    def update_toolbar(self, screen_name):
        """ Modify toolbar in-place so it can be shared by all screens """
        self.toolbar.title = screen_name.title().replace('_', ' ')
        if screen_name == HOME_SCREEN:
            self.toolbar.left_action_items = [['menu', self.open_nav]]
            self.toolbar.right_action_items = [
                ['fullscreen', self.toggle_fullscreen],
                ['dots-vertical', self.open_settings],
            ]
        else:
            self.toolbar.left_action_items = [["arrow-left", self.home]]
            self.toolbar.right_action_items = []

    def toggle_dark_mode(self, switch=None, is_active=False):
        """ Toggle between light and dark themes """
        self.theme_cls.theme_style = 'Dark' if is_active else 'Light'

    def toggle_fullscreen(self, *args):
        """ Enable or disable fullscreen, and change icon"""
        if Window.fullscreen:
            Window.fullscreen = 0
            icon = 'fullscreen'
        else:
            Window.fullscreen = 'auto'
            icon = 'fullscreen-exit'
        self.toolbar.right_action_items[0] = [icon, self.toggle_fullscreen]


def main():
    ImageTaggerApp().run()


if __name__ == '__main__':
    main()
