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
from kivy.uix.image import Image
from kivymd.app import MDApp

from naturtag.constants import (
    KV_SRC_DIR,
    INIT_WINDOW_SIZE,
    MD_PRIMARY_PALETTE,
    MD_ACCENT_PALETTE,
    ATLAS_APP_ICONS,
    ATLAS_TAXON_ICONS,
    BACKSPACE,
    F11,
)
from naturtag.ui.image_selector_controller import ImageSelectorController, alert
from naturtag.ui.settings_controller import SettingsController
from naturtag.ui.taxon_selection_controller import TaxonSelectionController
from naturtag.ui.taxon_view_controller import TaxonViewController
from naturtag.ui.screens import HOME_SCREEN, Root, load_screens

logger = getLogger().getChild(__name__)


class ControllerProxy:
    """ The individual controllers need to talk to each other sometimes.
    Any such interactions go through this class so they don't talk to each other directly.
    """
    image_selector_controller = ObjectProperty()
    taxon_selection_controller = ObjectProperty()
    taxon_view_controller = ObjectProperty()
    settings_controller = ObjectProperty()

    # def __init__(self, *args, **kwargs):
    #     pass

    def init_controllers(self, screens):
        # Init controllers with references to nested screen objects
        self.image_selector_controller = ImageSelectorController(screens[HOME_SCREEN].ids, screens['metadata'].ids)
        self.settings_controller = SettingsController(screens['settings'].ids)
        self.taxon_selection_controller = TaxonSelectionController(screens['taxon'].ids)
        self.taxon_view_controller = TaxonViewController(screens['taxon'].ids)
        # observation_search_controller = ObservationSearchController(screens['observation'].ids)

        # Proxy methods
        self.is_starred = self.taxon_selection_controller.is_starred
        self.add_star = self.taxon_selection_controller.add_star
        self.remove_star = self.taxon_selection_controller.remove_star
        self.stored_taxa = self.settings_controller.stored_taxa
        self.select_taxon = self.taxon_view_controller.select_taxon
        self.update_history = self.taxon_selection_controller.update_history

        # This part uses a lot of RAM, so do this last
        self.taxon_selection_controller.init_stored_taxa()


class NaturtagApp(MDApp, ControllerProxy):
    """ Manages window, theme, main screen and navigation state; other application logic is
    handled by Controller
    """
    root = ObjectProperty()
    nav_drawer = ObjectProperty()
    screen_manager = ObjectProperty()
    toolbar = ObjectProperty()

    @staticmethod
    def _add_screen(screen_name):
        screen_path = join(KV_SRC_DIR, f'{screen_name}.kv')
        Builder.load_file(screen_path)
        logger.debug(f'Init: Loaded screen {screen_path}')

    def build(self):
        # Init screens and store references to them
        screens = load_screens()
        self.root = Root()
        ControllerProxy.init_controllers(self, screens)

        # Init screen manager and nav elements
        self.nav_drawer = self.root.ids.nav_drawer
        self.screen_manager = self.root.ids.screen_manager
        self.toolbar = self.root.ids.toolbar
        for screen_name, screen in screens.items():
            self.screen_manager.add_widget(screen)
        self.set_theme_mode()
        self.home()
        # self.switch_screen('taxa')

        # Set Window and theme settings
        Window.size = INIT_WINDOW_SIZE
        Window.bind(on_dropfile=lambda x, y: self.image_selector_controller.add_images(y))
        Window.bind(on_keyboard=self.on_keyboard)
        Window.bind(on_request_close=self.on_request_close)
        self.theme_cls.primary_palette = MD_PRIMARY_PALETTE
        self.theme_cls.accent_palette = MD_ACCENT_PALETTE

        # Preload atlases so they're immediately available in Kivy cache
        Image(source=f'{ATLAS_APP_ICONS}/')
        # Image(source=f'{ATLAS_TAXON_ICONS}/')

        # alert(  # TODO: make this disappear as soon as an image or another screen is selected
        #     f'.{" " * 14}Drag and drop images or select them from the file chooser', duration=7
        # )
        return self.root

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
        """ Save any unsaved settings before exiting """
        self.settings_controller.save_settings()
        self.stop()

    def on_keyboard(self, window, key, scancode, codepoint, modifier):
        """ Handle keyboard shortcuts """
        if (modifier, key) == (['ctrl'], BACKSPACE):
            self.home()
        elif (modifier, codepoint) == (['ctrl'], 'o'):
            pass  # TODO: Open kivymd file manager
        elif (modifier, codepoint) == (['ctrl'], 'q'):
            self.on_request_close()
        elif (modifier, codepoint) == (['ctrl'], 'r'):
            self.image_selector_controller.run()
        elif (modifier, codepoint) == (['ctrl'], 's'):
            self.switch_screen('settings')
        elif (modifier, codepoint) == (['ctrl'], 't'):
            self.switch_screen('taxa')
        elif (modifier, codepoint) == (['shift', 'ctrl'], 'x'):
            self.image_selector_controller.clear()
        elif key == F11:
            self.toggle_fullscreen()

    def update_toolbar(self, screen_name):
        """ Modify toolbar in-place so it can be shared by all screens """
        self.toolbar.title = screen_name.title().replace('_', ' ')
        if screen_name == HOME_SCREEN:
            self.toolbar.left_action_items = [['menu', self.open_nav]]
        else:
            self.toolbar.left_action_items = [["arrow-left", self.home]]
        self.toolbar.right_action_items = [
            ['fullscreen', self.toggle_fullscreen],
            ['dots-vertical', self.open_settings],
        ]

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
    NaturtagApp().run()


if __name__ == '__main__':
    main()
