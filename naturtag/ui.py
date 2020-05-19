import json
import logging
import os
import sys
from os.path import basename, dirname, join

# Set GL backend before any kivy modules are imported
os.environ['KIVY_GL_BACKEND'] = 'sdl2'

# Disable multitouch emulation before any other kivy modules are imported
from kivy.config import Config
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import ListProperty, StringProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp

from kivymd.app import MDApp
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.imagelist import SmartTileWithLabel
from kivymd.uix.snackbar import Snackbar

from kv.widgets import SCREENS, HOME_SCREEN, SETTINGS_SCREEN, METADATA_SCREEN
from naturtag.app import tag_images
from naturtag.image_metadata import MetaMetadata

logger = logging.getLogger(__name__)
logger.setLevel('INFO')
out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter('[%(levelname)s] %(funcName)s %(asctime)s %(message)s'))
out_hdlr.setLevel(logging.INFO)
logger.addHandler(out_hdlr)

ASSETS_DIR = join(dirname(dirname(__file__)), 'assets', '')
KV_SRC_DIR = join(dirname(dirname(__file__)), 'kv')
IMAGE_FILETYPES = ['*.jpg', '*.jpeg', '*.png', '*.gif']
INIT_WINDOW_SIZE = (1250, 800)
MD_PRIMARY_PALETTE = 'Teal'
MD_ACCENT_PALETTE = 'Cyan'

# Key codes; reference: https://gist.github.com/Enteleform/a2e4daf9c302518bf31fcc2b35da4661
BACKSPACE = 8
F11 = 292

class ImageMetaTile(SmartTileWithLabel):
    metadata = ObjectProperty()


def alert(text, **kwargs):
    Snackbar(text=text, **kwargs).show()


class Controller(BoxLayout):
    """
    Top-level UI element that controls application state and logic,
    excluding screens & navigation, which is managed by ImageTaggerApp
    """
    file_list = ListProperty([])
    file_list_text = StringProperty()
    selected_image = ObjectProperty(None)

    def __init__(self, settings, inputs, image_previews, file_chooser, metadata_tabs, **kwargs):
        super().__init__(**kwargs)
        self.settings = settings
        self.inputs = inputs
        self.image_previews = image_previews
        self.file_chooser = file_chooser
        self.metadata_tabs = metadata_tabs

    # TODO: for testing only
    def open_table(self):
        MDDataTable(
            column_data=[
                ("No.", dp(30)),  ("Column 1", dp(30)), ("Column 2", dp(30)),
                ("Column 3", dp(30)), ("Column 4", dp(30)), ("Column 5", dp(30)),
            ],
            row_data=[ (f"{i + 1}", "2.23", "3.65", "44.1", "0.45", "62.5") for i in range(50)],
        ).open()

    def add_image(self, window=None, path=None):
        """ Add an image to the current selection, with deduplication """
        if isinstance(path, bytes):
            path = path.decode('utf-8')
        if path in self.file_list:
            return

        # Update file list
        logger.info(f'Adding image: {path}')
        self.file_list.append(path)
        self.file_list.sort()
        self.inputs.file_list_text_box.text = '\n'.join(self.file_list)

        # Update image previews
        metadata = MetaMetadata(path)
        img = ImageMetaTile(source=path, metadata=metadata, text=metadata.summary)
        img.bind(on_touch_down=self.handle_image_click)
        self.image_previews.add_widget(img)

    def add_images(self, paths):
        """ Add one or more files selected via a FileChooser """
        for path in paths:
            self.add_image(path=path)

    def remove_image(self, image):
        """ Remove an image from file list and image previews """
        self.file_list.remove(image.source)
        self.inputs.file_list_text_box.text = '\n'.join(self.file_list)
        self.selected_image = None
        image.parent.remove_widget(image)

    # TODO: Apply image file glob patterns to dir
    def add_dir_selection(self, dir):
        print(dir)

    def get_settings_dict(self):
        return {
            'common_names': self.settings.common_names_chk.active,
            'hierarchical_keywords': self.settings.hierarchical_keywords_chk.active,
            'darwin_core': self.settings.darwin_core_chk.active,
            'create_xmp': self.settings.create_xmp_chk.active,
            'dark_mode': self.settings.dark_mode_chk.active,
            "observation_id": int(self.inputs.observation_id_input.text or 0),
            "taxon_id": int(self.inputs.taxon_id_input.text or 0),
        }

    def get_state(self):
        logger.info(
            f'IDs: {self.ids}\n'
            f'Files:\n{self.file_list_text}\n'
            f'Config: {self.get_settings_dict()}\n'
        )

    def handle_image_click(self, instance, touch):
        """ Event handler for clicking an image; either remove or open image details """
        if not instance.collide_point(*touch.pos):
            return
        elif touch.button == 'right':
            self.remove_image(instance)
        else:
            self.selected_image = instance
            self.set_metadata_view()
            MDApp.get_running_app().switch_screen(METADATA_SCREEN)

    def set_metadata_view(self):
        if not self.selected_image:
            return
        # TODO: This is pretty ugly. Ideally this would be a collection of DataTables.
        self.metadata_tabs.combined.text = json.dumps(self.selected_image.metadata.combined, indent=4)
        self.metadata_tabs.keywords.text = (
            'Normal Keywords:\n' +
            json.dumps(self.selected_image.metadata.keyword_meta.flat_keywords, indent=4) +
            '\n\n\nHierarchical Keywords:\n' +
            self.selected_image.metadata.keyword_meta.hier_keyword_tree_str
        )
        self.metadata_tabs.exif.text = json.dumps(self.selected_image.metadata.exif, indent=4)
        self.metadata_tabs.iptc.text = json.dumps(self.selected_image.metadata.iptc, indent=4)
        self.metadata_tabs.xmp.text = json.dumps(self.selected_image.metadata.xmp, indent=4)

    def reset(self):
        """ Clear all image selections """
        logger.info('Clearing image selections')
        self.file_list = []
        self.file_list_text = ''
        self.file_chooser.selection = []
        self.image_previews.clear_widgets()

    def run(self):
        """ Run image tagging for selected images and input """
        settings = self.get_settings_dict()
        if not self.file_list:
            alert(f'Select images to tag')
            return
        if not settings['observation_id'] and not settings['taxon_id']:
            alert(f'Select either an observation or an organism to tag images with')
            return
        tag_images(
            settings['observation_id'],
            settings['taxon_id'],
            settings['common_names'],
            settings['darwin_core'],
            settings['hierarchical_keywords'],
            settings['create_xmp'],
            self.file_list,
        )

        selected_id = (
            f'Taxon ID: {settings["observation_id"]}' if settings['observation_id']
            else f'Observation ID: {settings["observation_id"]}'
        )
        alert(f'{len(self.file_list)} images tagged with metadata for {selected_id}')


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
            Builder.load_file(join(KV_SRC_DIR, f'{screen_name}.kv'))
            screens[screen_name] = screen_cls()

        # Init controller with references to nested screen objects for easier access
        controller = Controller(
            settings=screens[SETTINGS_SCREEN].ids,
            inputs=screens[HOME_SCREEN].ids,
            image_previews=screens[HOME_SCREEN].ids.image_previews,
            file_chooser=screens[HOME_SCREEN].ids.file_chooser,
            metadata_tabs=screens[METADATA_SCREEN].ids,
        )

        # Init screen manager and nav elements
        self.nav_drawer = controller.ids.nav_drawer
        self.screen_manager = controller.ids.screen_manager
        self.toolbar = controller.ids.toolbar
        for screen in screens.values():
            self.screen_manager.add_widget(screen)
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
            f'.{" " * 14}Drag and drop images or select them from the file chooser', duration=10)
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
        print(key, scancode, codepoint, modifier)
        if (modifier, key) == (['ctrl'], BACKSPACE):
            self.home()
        elif (modifier, codepoint) == (['ctrl'], 'o'):
            pass  # TODO: Open kivymd file manager
        elif (modifier, codepoint) == (['ctrl'], 'q'):
            self.stop()
        elif (modifier, codepoint) == (['ctrl'], 'r'):
            self.controller.run()
        elif (modifier, codepoint) == (['ctrl'], 's'):
            self.switch_screen(SETTINGS_SCREEN)
        elif (modifier, codepoint) == (['shift', 'ctrl'], 'x'):
            self.controller.reset()
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


if __name__ == '__main__':
    ImageTaggerApp().run()
