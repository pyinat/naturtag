import json
from logging import getLogger

from kivy.properties import ListProperty, StringProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp

from kivymd.app import MDApp
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.imagelist import SmartTileWithLabel
from kivymd.uix.snackbar import Snackbar

from naturtag.tagger import tag_images
from naturtag.image_metadata import MetaMetadata
from naturtag.inat_metadata import get_taxon_and_obs_from_metadata
from naturtag.ui.thumbnails import get_thumbnail

logger = getLogger().getChild(__name__)


class ImageMetaTile(SmartTileWithLabel):
    """ Class that contains an image thumbnail to display plus its associated metadata """
    metadata = ObjectProperty()
    allow_stretch = False
    box_color = [0, 0, 0, 0.4]

    def __init__(self, metadata, **kwargs):
        super().__init__(**kwargs)
        self.metadata = metadata


class Controller(BoxLayout):
    """
    Top-level UI element that controls application state and logic,
    excluding screens & navigation, which is managed by ImageTaggerApp
    """
    file_list = ListProperty([])
    file_list_text = StringProperty()
    selected_image = ObjectProperty(None)

    def __init__(self, inputs, image_previews, file_chooser, settings, metadata_tabs, **kwargs):
        super().__init__(**kwargs)
        self.inputs = inputs
        self.image_previews = image_previews
        self.file_chooser = file_chooser
        self.settings = settings
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

    def add_images(self, paths):
        """ Add one or more files selected via a FileChooser """
        for path in paths:
            self.add_image(path=path)

    # TODO: If an image is dragged & dropped onto a different screen, return to home screen
    def add_image(self, window=None, path=None):
        """ Add an image to the current selection, with deduplication """
        if isinstance(path, bytes):
            path = path.decode('utf-8')
        if path in self.file_list:
            return

        # Add to file list
        logger.info(f'Adding image: {path}')
        self.file_list.append(path)
        self.file_list.sort()
        self.inputs.file_list_text_box.text = '\n'.join(self.file_list)

        # Add thumbnail to image preview screen
        metadata = MetaMetadata(path)
        img = ImageMetaTile(
            source=get_thumbnail(path), metadata=metadata, text=metadata.summary
        )
        img.bind(on_touch_down=self.handle_image_click)
        self.image_previews.add_widget(img)

        # Run a search using any relevant tags we found
        self.search_tax_obs(metadata)

    def search_tax_obs(self, metadata):
        taxon, observation = get_taxon_and_obs_from_metadata(metadata)
        # TODO: Just temporary debug output here; need to display this info in the UI
        import json
        print(json.dumps(taxon, indent=4))
        print(json.dumps(observation, indent=4))

    def remove_image(self, image):
        """ Remove an image from file list and image previews """
        logger.info(f'Removing image: {image.metadata.image_path}')
        self.file_list.remove(image.metadata.image_path)
        self.inputs.file_list_text_box.text = '\n'.join(self.file_list)
        self.selected_image = None
        image.parent.remove_widget(image)

    def clear(self):
        """ Clear all image selections """
        logger.info('Clearing image selections')
        self.file_list = []
        self.file_list_text = ''
        self.inputs.file_list_text_box.text = ''
        self.file_chooser.selection = []
        self.image_previews.clear_widgets()

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
            MDApp.get_running_app().switch_screen('metadata')

    def set_metadata_view(self):
        if not self.selected_image:
            return
        # TODO: This is pretty ugly. Ideally this would be a collection of DataTables.
        self.metadata_tabs.combined.text = json.dumps(
            self.selected_image.metadata.combined, indent=4
        )
        self.metadata_tabs.keywords.text = (
            'Normal Keywords:\n'
            + json.dumps(self.selected_image.metadata.keyword_meta.flat_keywords, indent=4)
            + '\n\n\nHierarchical Keywords:\n'
            + self.selected_image.metadata.keyword_meta.hier_keyword_tree_str
        )
        self.metadata_tabs.exif.text = json.dumps(self.selected_image.metadata.exif, indent=4)
        self.metadata_tabs.iptc.text = json.dumps(self.selected_image.metadata.iptc, indent=4)
        self.metadata_tabs.xmp.text = json.dumps(self.selected_image.metadata.xmp, indent=4)

    def run(self):
        """ Run image tagging for selected images and input """
        settings = self.get_settings_dict()
        if not self.file_list:
            alert(f'Select images to tag')
            return
        if not settings['observation_id'] and not settings['taxon_id']:
            alert(f'Select either an observation or an organism to tag images with')
            return
        selected_id = (
            f'Taxon ID: {settings["taxon_id"]}' if settings['taxon_id']
            else f'Observation ID: {settings["observation_id"]}'
        )
        logger.info(f'Tagging {len(self.file_list)} images with metadata for {selected_id}')

        tag_images(
            settings['observation_id'],
            settings['taxon_id'],
            settings['common_names'],
            settings['darwin_core'],
            settings['hierarchical_keywords'],
            settings['create_xmp'],
            self.file_list,
        )
        alert(f'{len(self.file_list)} images tagged with metadata for {selected_id}')


def alert(text, **kwargs):
    Snackbar(text=text, **kwargs).show()
