"""Not sure where else these functions should go"""
from io import BytesIO
from logging import getLogger
from typing import Tuple
from urllib.parse import urlparse

from kivy.clock import mainthread
from kivy.core.image import Image as CoreImage
from kivy.uix.widget import Widget
from pyinaturalist import iNatClient
from requests import Response, Session

from naturtag.kv_app import get_app
from naturtag.loaders import BackgroundThread, BatchLoader
from naturtag.models import Taxon
from naturtag.widgets import TaxonListItem

logger = getLogger().getChild(__name__)


class TaxonBatchLoader(BatchLoader):
    """Loads batches of TaxonListItems. This class only handles creating UI objects in the main
    thread, and then passes them to be populated with data by :py:class:`.TaxonBGThread`.
    """

    def __init__(self, **kwargs):
        super().__init__(worker_callback=self.load_taxon_list_item, **kwargs)

    async def load_taxon_list_item(self, taxon_id: int, parent: Widget = None, **kwargs) -> Widget:
        """Initialize taxon UI elements"""
        logger.debug(f'TaxonBatchLoader: Processing item: {taxon_id}')
        widget = TaxonListItem(taxon_id=taxon_id, **kwargs)
        get_app().taxon_bg_thread.load_taxon(taxon_id, widget)

        if parent:
            parent.add_widget(widget)
        get_app().bind_to_select_taxon(widget)
        await self.increment_progress()
        return widget


# TODO: Increment progress when TaxonBGThread.process_queue_item() completes, instead of when
#   TaxonBatchLoader.load_widget() completes
class TaxonBGThread(BackgroundThread):
    """A continuously running background thread responsible for downloading taxon metadata and
    images. Can be accessed via `get_app().taxon_bg_thread`.
    """

    def __init__(self, client: iNatClient):
        super().__init__()
        self.client = client

    def load_taxon(self, taxon_id: int, list_item: TaxonListItem):
        logger.debug(f'TaxonBGLoader: Enqueuing taxon: {taxon_id}')
        self.queue.put((taxon_id, list_item))

    def process_queue_item(self, queue_item: Tuple[int, TaxonListItem]):
        taxon_id, list_item = queue_item
        taxon = get_taxon(self.client, taxon_id)
        image = get_taxon_thumbnail(self.client.session, taxon)

        mainthread(list_item.set_taxon)(taxon)
        mainthread(list_item.set_image)(image)
        mainthread(get_app().bind_to_select_taxon)(list_item)


def get_taxon(client: iNatClient, taxon_id: int) -> Taxon:
    """Get Taxon object by either ID, dict, or existing instance"""
    logger.debug(f'Taxon: Loading: {taxon_id}')
    base_taxon = client.taxa.from_id(taxon_id).one()
    taxon = Taxon.copy(base_taxon)
    logger.debug(f'Taxon: Loaded {taxon}')
    return taxon


def get_taxon_thumbnail(session: Session, taxon: Taxon) -> CoreImage:
    if not taxon.default_photo:
        return CoreImage(taxon.icon_path)

    url = taxon.default_photo.thumbnail_url
    response = session.get(url)
    img_data = BytesIO(response.content)
    return CoreImage(img_data, ext=_get_url_ext(response, url))


def _get_url_ext(response: Response, url: str):
    """Get the file extension from either the Content-Type header or the URL"""
    content_type = response.headers.get('Content-Type')
    if content_type:
        ext = content_type.split('/')[-1]
    else:
        ext = urlparse(url).path.split('.')[-1]
    return ext.lower().replace('jpeg', 'jpg')
