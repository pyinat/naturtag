# flake8: noqa: E402, F401
# isort: skip_file
from typing import TYPE_CHECKING
from PySide6.QtWidgets import QApplication


if TYPE_CHECKING:
    from naturtag.app import NaturtagApp


def get_app() -> 'NaturtagApp':
    return QApplication.instance()


from naturtag.controllers.base_controller import BaseController
from naturtag.controllers.image_gallery import ImageGallery
from naturtag.controllers.image_controller import ImageController
from naturtag.controllers.observation_search import ObservationSearch
from naturtag.controllers.observation_view import ObservationInfoSection
from naturtag.controllers.observation_controller import ObservationController
from naturtag.controllers.taxon_search import TaxonSearch
from naturtag.controllers.taxon_view import TaxonInfoSection, TaxonomySection
from naturtag.controllers.taxon_controller import TaxonController
