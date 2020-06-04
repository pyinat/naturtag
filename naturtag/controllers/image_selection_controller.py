import asyncio
import json
from logging import getLogger

from kivy.properties import ListProperty, StringProperty, ObjectProperty

from naturtag.app import alert, get_app
from naturtag.image_glob import get_images_from_paths
from naturtag.inat_metadata import get_taxon_and_obs_from_metadata
from naturtag.models.meta_metadata import MetaMetadata
from naturtag.tagger import tag_images
from naturtag.thumbnails import get_thumbnail
from naturtag.widgets import ImageMetaTile

logger = getLogger().getChild(__name__)


class ImageSelectionController:
    """ Controller class to manage image selector screen """
    def __init__(self, screen, **kwargs):
        self.context_menu = screen.context_menu
        self.inputs = screen
        self.image_previews = screen.image_previews
        self.file_chooser = screen.file_chooser
        self.file_list = []
        self.file_list_text = ''

        # Context menu item events
        self.context_menu.ids.view_taxon_ctx.bind(on_release=self.view_taxon)
        # self.context_menu.ids.view_observation_ctx.bind(on_release=self.view_observation)
        self.context_menu.ids.view_metadata_ctx.bind(on_release=self.view_metadata)
        self.context_menu.ids.copy_flickr_tags_ctx.bind(on_release=lambda x: x.selected_image.copy_flickr_tags())
        self.context_menu.ids.remove_ctx.bind(on_release=lambda x: self.remove_image(x.selected_image))

        # Other widget events
        self.inputs.taxon_id_input.bind(on_text_validate=self.on_taxon_id)
        self.inputs.clear_button.bind(on_release=self.clear)
        # self.inputs.clear_button.bind(on_release=lambda *x: get_app().show_progress())
        self.inputs.debug_button.bind(on_release=self.get_state)
        # self.inputs.debug_button.bind(on_release=self.open_table)
        self.inputs.load_button.bind(on_release=self.add_file_chooser_images)
        self.inputs.run_button.bind(on_release=self.run)
        self.file_chooser.bind(on_submit=self.add_file_chooser_images)

    def add_file_chooser_images(self, *args):
        """ Add one or more files and/or dirs selected via a FileChooser """
        self.add_images(self.file_chooser.selection)

    def add_images(self, paths):
        """ Add one or more files and/or dirs, with deduplication """
        results = asyncio.run(self.load_images(paths))
        self.select_first_result(results)

    def add_image(self, path):
        """ Add an image to the current selection """
        self.add_images([path])

    async def load_images(self, paths):
        return await asyncio.gather(*[self.load_image(path=path) for path in get_images_from_paths(paths)])

    # TODO: Use tasks to load incremental results in the UI
    async def load_image(self, path):
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
        img.bind(on_touch_down=self.on_image_click)
        self.image_previews.add_widget(img)

        # Run a search using any relevant tags we found
        # TODO: async HTTP requests
        taxon, observation = get_taxon_and_obs_from_metadata(metadata)
        await asyncio.sleep(0)
        return taxon, observation

    def select_photo_taxon(self, taxon_id):
        self.inputs.taxon_id_input.text = str(taxon_id)

    def select_photo_observation(self, observation_id):
        self.inputs.observation_id_input.text = str(observation_id)

    def select_first_result(self, results):
        """ Select the first taxon and/or observations discovered from tags, if any """
        if not results:
            return
        taxa, observations = zip(*results)

        taxon = next(filter(None, taxa), None)
        if taxon:
            self.select_photo_taxon(taxon['id'])
            get_app().select_taxon(taxon_dict=taxon, if_empty=True)

        # TODO: Display this info in the UI after observation search/view screens are implemented
        observation = next(filter(None, observations), None)
        if observation:
            self.select_photo_observation(observation['id'])
            logger.debug('Main: ' + json.dumps(observation, indent=4))
        #     get_app().select_observation(observation_dict=observation, if_empty=True)

    def remove_image(self, image):
        """ Remove an image from file list and image previews """
        logger.info(f'Main: Removing image {image.metadata.image_path}')
        self.file_list.remove(image.metadata.image_path)
        self.inputs.file_list_text_box.text = '\n'.join(self.file_list)
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

    def on_image_click(self, instance, touch):
        """ Event handler for clicking an image """
        if not instance.collide_point(*touch.pos):
            return
        # Right-click: Open context menu for the image
        elif touch.button == 'right':
            self.context_menu.show(*get_app().root_window.mouse_pos)
            self.context_menu.ref = instance
            # Enable 'view taxon/observation' menu items, if applicable
            self.context_menu.ids.view_taxon_ctx.disabled = not instance.metadata.taxon_id
            self.context_menu.ids.view_observation_ctx.disabled = not instance.metadata.observation_id
            self.context_menu.ids.copy_flickr_tags_ctx.disabled = not instance.metadata.keyword_meta.flickr_tags
        # Middle-click: remove image
        elif touch.button == 'middle':
            self.remove_image(instance)
        # Left-click: # TODO: larger image view
        else:
            pass

    # TODO: reuse Taxon object previously found by load_image; needs a bit of refactoring
    @staticmethod
    def view_taxon(instance):
        get_app().switch_screen('taxon')
        get_app().select_taxon(id=instance.metadata.taxon_id)

    @staticmethod
    def view_metadata(instance):
        get_app().switch_screen('metadata')
        get_app().load_metadata(instance.metadata)

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

        metadata_settings = get_app().metadata
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

    @staticmethod
    def on_taxon_id(input):
        """ Handle entering a taxon ID and pressing Enter """
        get_app().switch_screen('taxon')
        get_app().select_taxon(id=int(input.text))

    # TODO: for testing only
    # from kivy.metrics import dp
    # from kivymd.uix.datatables import MDDataTable
    # @staticmethod
    # def open_table(self):
    #     MDDataTable(
    #         column_data=[
    #             ("No.", dp(30)),  ("Column 1", dp(30)), ("Column 2", dp(30)),
    #             ("Column 3", dp(30)), ("Column 4", dp(30)), ("Column 5", dp(30)),
    #         ],
    #         row_data=[(f"{i + 1}", "2.23", "3.65", "44.1", "0.45", "62.5") for i in range(50)],
    #     ).open()
