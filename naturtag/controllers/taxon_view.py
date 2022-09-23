"""Components for displaying taxon info"""
import webbrowser
from collections import deque
from logging import getLogger
from typing import Iterator

from pyinaturalist import Taxon
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QGroupBox, QPushButton

from naturtag.app.style import fa_icon
from naturtag.app.threadpool import ThreadPool
from naturtag.constants import SIZE_SM
from naturtag.settings import UserTaxa
from naturtag.widgets import (
    GridLayout,
    HorizontalLayout,
    TaxonImageWindow,
    TaxonInfoCard,
    TaxonList,
)
from naturtag.widgets.layouts import VerticalLayout
from naturtag.widgets.taxon_images import TaxonPhoto

logger = getLogger(__name__)


class TaxonInfoSection(HorizontalLayout):
    """Section to display selected taxon photo and basic info"""

    on_select = Signal(Taxon)  #: A taxon object was selected (from nav or another screen)
    on_select_id = Signal(int)  #: A taxon ID was selected (from 'parent' button)

    def __init__(self, threadpool: ThreadPool):
        super().__init__()
        self.threadpool = threadpool
        self.hist_prev: deque[Taxon] = deque()  # Viewing history for current session only
        self.hist_next: deque[Taxon] = deque()  # Set when loading from history
        self.history_taxon: Taxon = None  # Set when loading from history, to avoid loop
        self.selected_taxon: Taxon = None

        self.group_box = QGroupBox('No taxon selected')
        root = VerticalLayout(self.group_box)
        images = HorizontalLayout()
        root.addLayout(images)
        self.addWidget(self.group_box)
        self.setAlignment(Qt.AlignTop)

        # Medium taxon default photo
        self.image = TaxonPhoto(hover_icon=True)
        self.image.setFixedHeight(395)  # Height of 5 thumbnails + spacing
        self.image.setAlignment(Qt.AlignTop)
        images.addWidget(self.image)

        # Additional taxon thumbnails
        self.thumbnails = GridLayout(n_columns=2)
        self.thumbnails.setSpacing(5)
        self.thumbnails.setAlignment(Qt.AlignTop)
        images.addLayout(self.thumbnails)

        # Back and Forward buttons: We already have the full Taxon object
        button_layout = HorizontalLayout()
        root.addLayout(button_layout)
        self.prev_button = QPushButton('Back')
        self.prev_button.setIcon(fa_icon('ei.chevron-left'))
        self.prev_button.clicked.connect(self.prev)
        self.prev_button.setEnabled(False)
        button_layout.addWidget(self.prev_button)

        self.next_button = QPushButton('Forward')
        self.next_button.setIcon(fa_icon('ei.chevron-right'))
        self.next_button.clicked.connect(self.next)
        self.next_button.setEnabled(False)
        button_layout.addWidget(self.next_button)

        # Parent button: We need to fetch the full Taxon object, so just pass the ID
        self.parent_button = QPushButton('Parent')
        self.parent_button.setIcon(fa_icon('ei.chevron-up'))
        self.parent_button.clicked.connect(self.select_parent)
        self.parent_button.setEnabled(False)
        button_layout.addWidget(self.parent_button)

        # Link button: Open web browser to taxon info page
        self.link_button = QPushButton('View on iNaturalist')
        self.link_button.setIcon(fa_icon('mdi.web', primary=True))
        self.link_button.clicked.connect(lambda: webbrowser.open(self.selected_taxon.url))
        self.link_button.setEnabled(False)
        button_layout.addWidget(self.link_button)

        # Fullscreen image viewer
        self.image_window = TaxonImageWindow()
        self.image.on_click.connect(self.image_window.display_taxon_fullscreen)

    def load(self, taxon: Taxon):
        """Load default photo + additional thumbnails"""
        if self.selected_taxon and taxon.id == self.selected_taxon.id:
            return

        # Append to nav history, unless we just loaded a taxon from history
        if self.selected_taxon and taxon.id != getattr(self.history_taxon, 'id', None):
            self.hist_prev.append(self.selected_taxon)
            self.hist_next.clear()
        logger.debug(
            f'Navigation: {" | ".join([t.name for t in self.hist_prev])} | [{taxon.name}] | '
            f'{" | ".join([t.name for t in self.hist_next])}'
        )

        # Set title and main photo
        self.history_taxon = None
        self.selected_taxon = taxon
        self.group_box.setTitle(taxon.full_name)
        self.image.taxon = taxon
        self.image.set_pixmap_async(
            self.threadpool,
            photo=taxon.default_photo,
            priority=QThread.HighPriority,
        )
        self._update_nav_buttons()

        # Load additional thumbnails
        self.thumbnails.clear()
        for i, photo in enumerate(taxon.taxon_photos[1:11] if taxon.taxon_photos else []):
            thumb = TaxonPhoto(taxon=taxon, idx=i + 1)
            thumb.setFixedSize(*SIZE_SM)
            thumb.on_click.connect(self.image_window.display_taxon_fullscreen)
            thumb.set_pixmap_async(self.threadpool, photo=photo, size='thumbnail')
            self.thumbnails.addWidget(thumb)

    def prev(self):
        if not self.hist_prev:
            return
        self.history_taxon = self.hist_prev.pop()
        self.hist_next.appendleft(self.selected_taxon)
        self.on_select.emit(self.history_taxon)

    def next(self):
        if not self.hist_next:
            return
        self.history_taxon = self.hist_next.popleft()
        self.hist_prev.append(self.selected_taxon)
        self.on_select.emit(self.history_taxon)

    def select_taxon(self, taxon: Taxon):
        self.load(taxon)
        self.on_select.emit(taxon)

    def select_parent(self):
        self.on_select_id.emit(self.selected_taxon.parent_id)

    def _update_nav_buttons(self):
        """Update status and tooltip for 'back', 'forward', 'parent', and 'view on iNat' buttons"""
        self.prev_button.setEnabled(bool(self.hist_prev))
        self.prev_button.setToolTip(self.hist_prev[-1].full_name if self.hist_prev else None)
        self.next_button.setEnabled(bool(self.hist_next))
        self.next_button.setToolTip(self.hist_next[0].full_name if self.hist_next else None)
        self.parent_button.setEnabled(bool(self.selected_taxon.parent))
        self.parent_button.setToolTip(
            self.selected_taxon.parent.full_name if self.selected_taxon.parent else None
        )
        self.link_button.setEnabled(True)
        self.link_button.setToolTip(self.selected_taxon.url)


class TaxonomySection(HorizontalLayout):
    """Section to display ancestors and children of selected taxon"""

    def __init__(self, threadpool: ThreadPool, user_taxa: UserTaxa):
        super().__init__()

        self.ancestors_group = self.add_group(
            'Ancestors', min_width=400, max_width=500, policy_min_height=False
        )
        self.ancestors_list = TaxonList(threadpool, user_taxa)
        self.ancestors_group.addWidget(self.ancestors_list.scroller)

        self.children_group = self.add_group(
            'Children', min_width=400, max_width=500, policy_min_height=False
        )
        self.children_list = TaxonList(threadpool, user_taxa)
        self.children_group.addWidget(self.children_list.scroller)

    def load(self, taxon: Taxon):
        """Populate taxon ancestors and children"""
        logger.info(f'Loading {len(taxon.ancestors)} ancestors and {len(taxon.children)} children')

        def get_label(text: str, items: list) -> str:
            return text + (f' ({len(items)})' if items else '')

        self.ancestors_group.set_title(get_label('Ancestors', taxon.ancestors))
        self.ancestors_list.set_taxa(taxon.ancestors)
        self.children_group.set_title(get_label('Children', taxon.children))
        self.children_list.set_taxa(taxon.children)

    @property
    def taxa(self) -> Iterator['TaxonInfoCard']:
        yield from self.ancestors_list.cards
        yield from self.children_list.cards
