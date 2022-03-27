"""Not sure where else these functions should go"""
from io import BytesIO
from logging import getLogger
from threading import Thread
from typing import Union

from kivy.clock import mainthread
from kivy.core.image import Image as CoreImage
from pyinaturalist import Taxon as BaseTaxon
from pyinaturalist import iNatClient
from requests import Session

from naturtag.app import get_app
from naturtag.models import Taxon
from naturtag.widgets import TaxonListItem

logger = getLogger().getChild(__name__)


# TODO: Run a single background thread that accepts tasks from a queue
async def get_taxon_list_item(
    client: iNatClient, taxon_input: Union[Taxon, int, dict], **kwargs
) -> TaxonListItem:
    list_item = TaxonListItem(**kwargs)

    def _load_taxon():
        taxon = get_taxon(client, taxon_input)
        mainthread(list_item.set_taxon)(taxon)

        image = get_taxon_thumbnail(client.session, taxon)
        mainthread(list_item.set_image)(image)
        mainthread(get_app().bind_to_select_taxon)(list_item)

    thread = Thread(target=_load_taxon)
    thread.start()
    return list_item


# def _load_taxon_list_item(client, taxon, list_item):
#     taxon = get_taxon(client, taxon)
#     image = get_taxon_thumbnail(client.session, taxon)
#     list_item.set_taxon(taxon)
#     list_item.set_image(image)
#     return TaxonListItem(taxon, image=image)


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


def get_taxon_thumbnail(session: Session, taxon: Taxon) -> CoreImage:
    url = taxon.default_photo.thumbnail_url or taxon.icon_path
    response = session.get(url)
    ext = url.split('.')[-1]
    img_data = BytesIO(response.content)
    return CoreImage(img_data, ext=ext)
