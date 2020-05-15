import logging
import os
import sys
os.environ['KIVY_GL_BACKEND'] = 'sdl2'

from kivymd.app import MDApp as App
from kivy.core.window import Window
from kivy.properties import DictProperty, ListProperty, StringProperty, ObjectProperty, BooleanProperty
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.imagelist import SmartTileWithLabel as ImageTile

logger = logging.getLogger(__name__)
logger.setLevel('INFO')
out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter('[%(levelname)s] %(name)s %(funcName)s %(asctime)s %(message)s'))
out_hdlr.setLevel(logging.INFO)
logger.addHandler(out_hdlr)

INIT_WINDOW_SIZE = (1250, 800)
IMAGE_FILETYPES = ['*.jpg', '*.jpeg', '*.png', '*.gif']

class ContentNavigationDrawer(BoxLayout):
    screen_manager = ObjectProperty()
    nav_drawer = ObjectProperty()


class Controller(BoxLayout):
    common_names = BooleanProperty()
    hierarchical_keywords = BooleanProperty()
    create_xmp = BooleanProperty()
    observation_id = StringProperty()
    taxon_id = StringProperty()
    file_list = ListProperty([])
    file_list_text = StringProperty('')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Adjust image preview layout
        self.ids.image_previews.bind(minimum_height=self.ids.image_previews.setter('height'))
        self.ids.filechooser.filters = IMAGE_FILETYPES

    def add_image(self, window=None, path=None):
        """ Add an image to the current selection, with deduplication """
        if isinstance(path, bytes):
            path = path.decode('utf-8')

        if path not in self.file_list:
            logger.info(f'Adding image: {path}')
            self.file_list.append(path)
            self.ids.image_previews.add_widget(ImageTile(source=path))
            self.file_list.sort()
            self.file_list_text = '\n'.join(self.file_list)

    def add_images(self, paths):
        """ Add one or more files selected via a FileChooser """
        for path in paths:
            self.add_image(path=path)

    def add_dir_selection(self, dir):
        print(dir)

    def get_state(self):
        logger.info(
            f'IDs: {self.ids}\nFiles:\n{self.file_list_text}\n'
            f'Config: {self.common_names, self.hierarchical_keywords, self.create_xmp}\n'
            f'Inputs: {self.observation_id, self.taxon_id}'
        )
        print(self.ids.filechooser.filters)

    def reset(self):
        """ Clear all image selections """
        self.file_list = []
        self.file_list_text = ''
        self.ids.filechooser.selection = []
        self.ids.image_previews.clear_widgets()

    @property
    def selected_files(self):
        return '\n'.join(self.file_list)

class Metadata(Widget):
    exif = DictProperty({})
    iptc = DictProperty({})
    xmp = DictProperty({})


class ImageTaggerApp(App):
    def build(self):
        controller = Controller()
        Window.bind(on_dropfile=controller.add_image)
        Window.size = INIT_WINDOW_SIZE
        controller.ids.screen_manager.current = 'main'
        return controller


if __name__ == '__main__':
    ImageTaggerApp().run()
