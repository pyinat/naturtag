import json
from logging import getLogger

from kivy.properties import ListProperty, StringProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp

from kivymd.app import MDApp
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.snackbar import Snackbar

from naturtag.image_glob import get_images_from_paths
from naturtag.tagger import tag_images
from naturtag.models.meta_metadata import MetaMetadata
from naturtag.inat_metadata import get_taxon_and_obs_from_metadata
from naturtag.thumbnails import get_thumbnail
from naturtag.ui import get_app
from naturtag.ui.image import ImageMetaTile

logger = getLogger().getChild(__name__)


class ImageSelectorController(BoxLayout):
    """ Controller class to manage image slector screen """
    file_list = ListProperty([])
    file_list_text = StringProperty()
    selected_image = ObjectProperty(None)

    def __init__(self, image_selector_screen, metadata_screen, **kwargs):
        super().__init__(**kwargs)
        self.inputs = image_selector_screen
        self.image_previews = image_selector_screen.image_previews
        self.file_chooser = image_selector_screen.file_chooser
        self.metadata_screen = metadata_screen

        # Bind widget events
        self.inputs.clear_button.bind(on_release=self.clear)
        self.inputs.debug_button.bind(on_release=self.get_state)
        # self.inputs.debug_button.bind(on_release=self.open_table)
        self.inputs.load_button.bind(on_release=self.add_file_chooser_images)
        self.inputs.run_button.bind(on_release=self.run)
        self.file_chooser.bind(on_submit=self.add_file_chooser_images)

    def add_file_chooser_images(self, *args):
        """ Add one or more files and/or dirs selected via a FileChooser """
        self.add_images(self.file_chooser.selection)

    def add_images(self, paths):
        """ Add one or more files and/or dirs """
        for path in get_images_from_paths(paths):
            self.add_image(path=path)

    # TODO: If an image is dragged & dropped onto a different screen, return to home screen
    def add_image(self, path):
        """ Add an image to the current selection, with deduplication """
        if path in self.file_list:
            return

        # Add to file list
        logger.info(f'Main: Adding image {path}')
        self.file_list.append(path)
        self.file_list.sort()
        self.inputs.file_list_text_box.text = '\n'.join(self.file_list)

        # Add thumbnail to image preview screen
        metadata = MetaMetadata(path)
        img = ImageMetaTile(source=get_thumbnail(path), metadata=metadata, text=metadata.summary)
        img.bind(on_touch_down=self.handle_image_click)
        self.image_previews.add_widget(img)

        # Run a search using any relevant tags we found
        self.search_tax_obs(metadata)

    def search_tax_obs(self, metadata):
        taxon, observation = get_taxon_and_obs_from_metadata(metadata)

        # Select a taxon discovered from tags, unless one has already been selected
        if taxon:
            get_app().select_taxon(taxon_dict=taxon, if_empty=True)

        if taxon:
            self.inputs.taxon_id_input.text = str(taxon['id'])
        # TODO: Just temporary debug output here; need to display this info in the UI
        if observation:
            logger.debug('Main: ' + json.dumps(observation, indent=4))

    def remove_image(self, image):
        """ Remove an image from file list and image previews """
        logger.info(f'Main: Removing image {image.metadata.image_path}')
        self.file_list.remove(image.metadata.image_path)
        self.inputs.file_list_text_box.text = '\n'.join(self.file_list)
        self.selected_image = None
        image.parent.remove_widget(image)

    def clear(self, *args):
        """ Clear all image selections """
        logger.info('Main: Clearing image selections')
        self.file_list = []
        self.file_list_text = ''
        self.inputs.file_list_text_box.text = ''
        self.file_chooser.selection = []
        self.image_previews.clear_widgets()

    def get_input_dict(self):
        return {
            "observation_id": int(self.inputs.observation_id_input.text or 0),
            "taxon_id": int(self.inputs.taxon_id_input.text or 0),
        }

    def get_state(self, *args):
        logger.info(
            'Main:',
            f'IDs: {self.ids}\n'
            f'Files:\n{self.file_list_text}\n'
            f'Input: {self.get_input_dict()}\n'
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
        self.metadata_screen.combined.text = json.dumps(
            self.selected_image.metadata.combined, indent=4
        )
        self.metadata_screen.keywords.text = (
            'Normal Keywords:\n'
            + json.dumps(self.selected_image.metadata.keyword_meta.flat_keywords, indent=4)
            + '\n\n\nHierarchical Keywords:\n'
            + self.selected_image.metadata.keyword_meta.hier_keyword_tree_str
        )
        self.metadata_screen.exif.text = json.dumps(self.selected_image.metadata.exif, indent=4)
        self.metadata_screen.iptc.text = json.dumps(self.selected_image.metadata.iptc, indent=4)
        self.metadata_screen.xmp.text = json.dumps(self.selected_image.metadata.xmp, indent=4)

    def run(self, *args):
        """ Run image tagging for selected images and input """
        inputs = self.get_input_dict()
        if not self.file_list:
            alert(f'Select images to tag')
            return
        if not inputs['observation_id'] and not inputs['taxon_id']:
            alert(f'Select either an observation or an organism to tag images with')
            return
        selected_id = (
            f'Taxon ID: {inputs["taxon_id"]}' if inputs['taxon_id']
            else f'Observation ID: {inputs["observation_id"]}'
        )
        logger.info(f'Main: Tagging {len(self.file_list)} images with metadata for {selected_id}')

        # TODO: Is there a better way to access settings?
        metadata_settings = MDApp.get_running_app().settings_controller.metadata

        tag_images(
            inputs['observation_id'],
            inputs['taxon_id'],
            metadata_settings['common_names'],
            metadata_settings['darwin_core'],
            metadata_settings['hierarchical_keywords'],
            metadata_settings['create_xmp'],
            self.file_list,
        )
        alert(f'{len(self.file_list)} images tagged with metadata for {selected_id}')

    # TODO: for testing only
    @staticmethod
    def open_table(self):
        MDDataTable(
            column_data=[
                ("No.", dp(30)),  ("Column 1", dp(30)), ("Column 2", dp(30)),
                ("Column 3", dp(30)), ("Column 4", dp(30)), ("Column 5", dp(30)),
            ],
            row_data=[(f"{i + 1}", "2.23", "3.65", "44.1", "0.45", "62.5") for i in range(50)],
        ).open()


def alert(text, **kwargs):
    Snackbar(text=text, **kwargs).show()
