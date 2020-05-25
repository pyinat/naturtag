""" Main Kivy application """
import os
from logging import getLogger
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
from naturtag.ui.settings_controller import SettingsController
from naturtag.ui.taxon_search_controller import TaxonSearchController
from naturtag.ui.observation_search_controller import ObservationSearchController
from naturtag.ui.widget_classes import SCREENS, HOME_SCREEN

logger = getLogger().getChild(__name__)


class ImageTaggerApp(MDApp):
    """
    Manages window, theme, main screen and navigation state; other application logic is
    handled by Controller
    """
    controller = ObjectProperty()
    taxon_search_controller = ObjectProperty()
    settings_controller = ObjectProperty
    nav_drawer = ObjectProperty()
    screen_manager = ObjectProperty()
    toolbar = ObjectProperty()

    def build(self):
        # Init screens and store references to them
        screens = {}
        Builder.load_file(join(KV_SRC_DIR, 'main.kv'))
        Builder.load_file(join(KV_SRC_DIR, 'autocomplete.kv'))
        for screen_name, screen_cls in SCREENS.items():
            screen_path = join(KV_SRC_DIR, f'{screen_name}.kv')
            Builder.load_file(screen_path)
            screens[screen_name] = screen_cls()
            logger.info(f'Loaded screen {screen_path}')

        # Init controllers with references to nested screen objects for easier access
        self.controller = Controller(screens[HOME_SCREEN].ids, screens['metadata'].ids)
        self.taxon_search_controller = TaxonSearchController(screens['taxon_search'].ids)
        # observation_search_controller = ObservationSearchController(observation_screen=screens['observation_search'].ids)
        self.settings_controller = SettingsController(screens['settings'].ids)

        # Init screen manager and nav elements
        self.nav_drawer = self.controller.ids.nav_drawer
        self.screen_manager = self.controller.ids.screen_manager
        self.toolbar = self.controller.ids.toolbar
        for screen_name, screen in screens.items():
            self.screen_manager.add_widget(screen)
        self.set_theme_mode()
        self.home()
        # self.switch_screen('taxon_search')

        # Set some event bindings that can't (easily) by done in kvlang
        self.settings_controller.screen.dark_mode_chk.bind(active=self.set_theme_mode)
        self.controller.image_previews.bind(minimum_height=self.controller.image_previews.setter('height'))

        # Set Window and theme settings
        Window.size = INIT_WINDOW_SIZE
        Window.bind(on_dropfile=lambda x, y: self.controller.add_images(y))
        Window.bind(on_keyboard=self.on_keyboard)
        Window.bind(on_request_close=self.on_request_close)
        self.theme_cls.primary_palette = MD_PRIMARY_PALETTE
        self.theme_cls.accent_palette = MD_ACCENT_PALETTE

        # alert(  # TODO: make this disappear as soon as an image or another screen is selected
        #     f'.{" " * 14}Drag and drop images or select them from the file chooser', duration=7
        # )
        return self.controller

    def home(self, *args):
        self.switch_screen(HOME_SCREEN)

    def open_nav(self, *args):
        self.nav_drawer.set_state('open')

    def close_nav(self, *args):
        self.nav_drawer.set_state('close')

    def switch_screen(self, screen_name):
        # If we're leaving the Settings screen, save any changes
        if self.screen_manager.current == 'settings':
            self.settings_controller.save_settings()

        self.screen_manager.current = screen_name
        self.update_toolbar(screen_name)
        self.close_nav()

    def on_request_close(self, *args):
        """ Save any usaved settings before exiting """
        self.settings_controller.save_settings()
        self.stop()

    def on_keyboard(self, window, key, scancode, codepoint, modifier):
        """ Handle keyboard shortcuts """
        # logger.info(key, scancode, codepoint, modifier)
        if (modifier, key) == (['ctrl'], BACKSPACE):
            self.home()
        elif (modifier, codepoint) == (['ctrl'], 'o'):
            pass  # TODO: Open kivymd file manager
        elif (modifier, codepoint) == (['ctrl'], 'q'):
            self.on_request_close()
        elif (modifier, codepoint) == (['ctrl'], 'r'):
            self.controller.run()
        elif (modifier, codepoint) == (['ctrl'], 's'):
            self.switch_screen('settings')
        elif (modifier, codepoint) == (['ctrl'], 't'):
            self.switch_screen('taxon_search')
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

    def set_theme_mode(self, switch=None, is_active=None):
        """ Set light or dark themes, based on either toggle switch or settings """
        if is_active is None:
            is_active = self.settings_controller.display['dark_mode']
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
