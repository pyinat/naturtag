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

from kivymd.app import MDApp as App
from kivymd.uix.imagelist import SmartTileWithLabel
from kivymd.uix.snackbar import Snackbar

from kv.widgets import SCREENS
from naturtag.app import tag_images
from naturtag.metadata_reader import MetaMetadata

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


class ImageMetaTile(SmartTileWithLabel):
    metadata = ObjectProperty()


class Controller(BoxLayout):
    """
    Top-level UI element that controls most app behavior, except for window/theme behavior,
    which is controlled by ImageTaggerApp
    """
    file_list = ListProperty([])
    file_list_text = StringProperty()
    selected_image_table = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize screens and store references to them
        for name, cls in SCREENS.items():
            Builder.load_file(join(KV_SRC_DIR, f'{name}.kv'))
            new_screen = cls()
            new_screen.controller = self
            self.ids.screen_manager.add_widget(new_screen)
            self.__setattr__(f'{name}_screen', new_screen)

        # Add additional references to some nested objects for easier access
        self.settings = self.settings_screen.ids
        self.inputs = self.image_selector_screen.ids
        self.image_previews = self.image_selector_screen.ids.image_previews
        self.file_chooser = self.image_selector_screen.ids.file_chooser

        # Automatically adjust image preview layout
        self.image_previews.bind(minimum_height=self.image_previews.setter('height'))

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
        img = ImageMetaTile(source=path, metadata=metadata,  text=metadata.summary)
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
        """ Event handler for clicking an image """
        if not instance.collide_point(*touch.pos):
            return
        elif touch.button == 'right':
            self.remove_image(instance)
        # TODO: Implement metadata view
        else:
            print('left mouse clicked')

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
        if not settings['observation_id'] and not settings['taxon_id']:
            Snackbar(text=f'First select either an observation or an organism').show()
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
        Snackbar(text=f'{len(self.file_list)} images tagged with metadata for {selected_id}').show()


class ImageTaggerApp(App):
    toolbar = ObjectProperty()

    def build(self):
        Builder.load_file(join(KV_SRC_DIR, 'main.kv'))

        # Window and theme settings
        controller = Controller()
        Window.bind(on_dropfile=controller.add_image)
        Window.size = INIT_WINDOW_SIZE
        self.theme_cls.primary_palette = MD_PRIMARY_PALETTE
        self.theme_cls.accent_palette = MD_ACCENT_PALETTE
        controller.settings.dark_mode_chk.bind(active=self.toggle_dark_mode)

        controller.ids.screen_manager.current = 'image_selector'
        self.toolbar = controller.ids.toolbar
        # controller.ids.screen_manager.current = 'settings'
        # TODO: Better help text that disappears as soon as an image or another screen is selected
        Snackbar(
            text=f'.{" " * 14}Drag and drop images or select them from the file chooser',
            duration=10
        ).show()
        return controller

    def toggle_dark_mode(self, switch=None, is_active=False):
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
