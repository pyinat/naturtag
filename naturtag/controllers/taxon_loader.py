"""Not sure where else these functions should go"""
from io import BytesIO
from logging import getLogger
from queue import Queue
from threading import Event, Thread
from time import sleep
from typing import Union
from urllib.parse import urlparse

from kivy.clock import mainthread
from kivy.core.image import Image as CoreImage
from pyinaturalist import Taxon as BaseTaxon
from pyinaturalist import iNatClient
from requests import Session

from naturtag.app import get_app
from naturtag.models import Taxon
from naturtag.widgets import TaxonListItem

logger = getLogger().getChild(__name__)


# TODO: Increment progress when queue item completes
class TaxonBGLoader(Thread):
    def __init__(self, client: iNatClient):
        super().__init__()
        self.client = client
        self.queue = Queue()
        self._stop_event = Event()

    def load_taxon(self, taxon_input: Union[Taxon, int, dict], list_item: TaxonListItem):
        logger.info(f'TaxonBGLoader: Enqueuing taxon: {taxon_input}')
        self.queue.put((taxon_input, list_item))

    def stop(self):
        logger.info(f'TaxonBGLoader: Canceling {self.queue.qsize()} tasks')
        self.queue.queue.clear()
        self._stop_event.set()
        self.join()

    def run(self):
        while True:
            if self._stop_event.is_set():
                break
            elif not self.queue.empty():
                taxon_input, list_item = self.queue.get()
                logger.info(f'TaxonBGLoader: Loading taxon: {taxon_input}')
                self._load_taxon_list_item(taxon_input, list_item)
                self.queue.task_done()
                logger.info(f'TaxonBGLoader: Loaded taxon: {taxon_input}')
            else:
                sleep(0.2)

    def _load_taxon_list_item(self, taxon, list_item):
        taxon = get_taxon(self.client, taxon)
        image = get_taxon_thumbnail(self.client.session, taxon)
        mainthread(list_item.set_taxon)(taxon)
        mainthread(list_item.set_image)(image)
        mainthread(get_app().bind_to_select_taxon)(list_item)


async def get_taxon_list_item(
    client: iNatClient, taxon_input: Union[Taxon, int, dict], **kwargs
) -> TaxonListItem:
    list_item = TaxonListItem(**kwargs)

    def _load_taxon():
        taxon = get_taxon(client, taxon_input)
        image = get_taxon_thumbnail(client.session, taxon)
        mainthread(list_item.set_taxon)(taxon)
        mainthread(list_item.set_image)(image)
        mainthread(get_app().bind_to_select_taxon)(list_item)

    thread = Thread(target=_load_taxon)
    thread.start()
    return list_item


def get_taxon(client: iNatClient, taxon: Union[BaseTaxon, int, dict]) -> Taxon:
    """Get Taxon object by either ID, dict, or existing instance"""
    logger.debug(f'Taxon: Loading: {taxon}')

    if isinstance(taxon, int):
        base_taxon = client.taxa.from_id(taxon).one()
        taxon = Taxon.copy(base_taxon)
    elif isinstance(taxon, dict):
        taxon = Taxon.from_json(taxon)
    logger.debug(f'Taxon: Loaded {taxon}')
    return taxon


# TODO: If some image URLs don't have a filename/extension, use Content-Type instead
def get_taxon_thumbnail(session: Session, taxon: Taxon) -> CoreImage:
    if not taxon.default_photo:
        return CoreImage(taxon.icon_path)

    url = taxon.default_photo.thumbnail_url
    response = session.get(url)
    img_data = BytesIO(response.content)
    return CoreImage(img_data, ext=_get_url_ext(url))


def _get_url_ext(url: str):
    path = urlparse(url).path
    path = path.lower().replace('jpeg', 'jpg')
    return path.split('.')[-1]
