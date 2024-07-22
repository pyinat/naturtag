"""Components for displaying taxon info"""

import webbrowser
from collections import deque
from logging import getLogger
from typing import Iterator

from pyinaturalist import Taxon
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QGroupBox, QPushButton

from naturtag.constants import SIZE_SM
from naturtag.storage import AppState
from naturtag.widgets import (
    GridLayout,
    HorizontalLayout,
    TaxonImageWindow,
    TaxonInfoCard,
    TaxonList,
    set_pixmap_async,
)
from naturtag.widgets.layouts import VerticalLayout
from naturtag.widgets.style import fa_icon
from naturtag.widgets.taxon_images import TaxonPhoto

logger = getLogger(__name__)


class TaxonInfoSection(HorizontalLayout):
    """Section to display selected taxon photo and basic info"""

    on_select = Signal(Taxon)  #: A taxon was selected for tagging
    on_view_observations = Signal(Taxon)  #: Request to switch to observations tab

    # When selecting a taxon for viewing, a signal is sent to controller instead of handling here,
    #   since there are multiple sections to load (not just this class)
    on_view_taxon = Signal(Taxon)  #: A taxon was selected for viewing (from nav or another screen)
    on_view_taxon_by_id = Signal(int)  #: A taxon ID was selected for viewing (from 'parent' button)

    def __init__(self):
        super().__init__()
        self.hist_prev: deque[Taxon] = deque()  # Viewing history for current session only
        self.hist_next: deque[Taxon] = deque()  # Set when loading from history
        self.history_taxon: Taxon = None  # Set when loading from history, to avoid loop
        self.displayed_taxon: Taxon = None

        self.group_box = QGroupBox('No taxon selected')
        root = VerticalLayout(self.group_box)
        images = HorizontalLayout()
        root.addLayout(images)
        self.addWidget(self.group_box)
        self.setAlignment(Qt.AlignTop)

        # Medium taxon default photo
        self.image = TaxonPhoto(hover_icon=True, hover_event=False)  # Disabled until first load
        self.image.setFixedHeight(395)  # Height of 5 thumbnails + spacing
        self.image.setAlignment(Qt.AlignTop)
        images.addWidget(self.image)

        # Additional taxon thumbnails
        self.thumbnails = GridLayout(n_columns=2)
        self.thumbnails.setSpacing(5)
        self.thumbnails.setAlignment(Qt.AlignTop)
        images.addLayout(self.thumbnails)

        # Button layout
        button_layout = VerticalLayout()
        button_row_1 = HorizontalLayout()
        button_row_2 = HorizontalLayout()
        button_layout.addLayout(button_row_1)
        button_layout.addLayout(button_row_2)
        root.addLayout(button_layout)

        # Back and Forward buttons: We already have the full Taxon object
        self.prev_button = QPushButton('Back')
        self.prev_button.setIcon(fa_icon('ei.chevron-left'))
        self.prev_button.clicked.connect(self.prev)
        self.prev_button.setEnabled(False)
        button_row_1.addWidget(self.prev_button)

        self.next_button = QPushButton('Forward')
        self.next_button.setIcon(fa_icon('ei.chevron-right'))
        self.next_button.clicked.connect(self.next)
        self.next_button.setEnabled(False)
        button_row_1.addWidget(self.next_button)

        # Parent button: Full Taxon object isn't available, so just pass the ID
        self.parent_button = QPushButton('Parent')
        self.parent_button.setIcon(fa_icon('ei.chevron-up'))
        self.parent_button.clicked.connect(self.select_parent)
        self.parent_button.setEnabled(False)
        button_row_1.addWidget(self.parent_button)

        # Select button: Use taxon for tagging
        self.select_button = QPushButton('Select')
        self.select_button.setIcon(fa_icon('fa.tag', primary=True))
        self.select_button.clicked.connect(lambda: self.on_select.emit(self.displayed_taxon))
        self.select_button.setEnabled(False)
        self.select_button.setToolTip('Select this taxon for tagging')
        button_row_2.addWidget(self.select_button)

        # View observations button
        # TODO: Observation filters
        # self.view_observations_button = QPushButton('View Observations')
        self.view_observations_button = QPushButton('')
        # self.view_observations_button.setIcon(fa_icon('fa5s.binoculars', primary=True))
        # self.view_observations_button.clicked.connect(
        #     lambda: self.on_view_observations.emit(self.displayed_taxon.id)
        # )
        self.view_observations_button.setEnabled(False)
        # self.select_button.setToolTip('View your observations of this taxon')
        button_row_2.addWidget(self.view_observations_button)

        # Link button: Open web browser to taxon info page
        self.link_button = QPushButton('View on iNaturalist')
        self.link_button.setIcon(fa_icon('mdi.web', primary=True))
        self.link_button.clicked.connect(lambda: webbrowser.open(self.displayed_taxon.url))
        self.link_button.setEnabled(False)
        button_row_2.addWidget(self.link_button)

        # Fullscreen image viewer
        self.image_window = TaxonImageWindow()
        self.image.on_click.connect(self.image_window.display_taxon_fullscreen)

    def load(self, taxon: Taxon):
        """Load default photo + additional thumbnails"""
        if self.displayed_taxon and taxon.id == self.displayed_taxon.id:
            return

        # Append to nav history, unless we just loaded a taxon from history
        if self.displayed_taxon and taxon.id != getattr(self.history_taxon, 'id', None):
            self.hist_prev.append(self.displayed_taxon)
            self.hist_next.clear()
        logger.debug(
            f'Navigation: {" | ".join([t.name for t in self.hist_prev])} | [{taxon.name}] | '
            f'{" | ".join([t.name for t in self.hist_next])}'
        )

        # Set title and main photo
        self.history_taxon = None
        self.displayed_taxon = taxon
        self.group_box.setTitle(taxon.full_name)
        self.image.hover_event = True
        self.image.taxon = taxon
        set_pixmap_async(
            self.image,
            photo=taxon.default_photo,
            size='medium',
            priority=QThread.HighPriority,
        )
        self._update_buttons()

        # Load additional thumbnails
        self.thumbnails.clear()
        for i, photo in enumerate(taxon.taxon_photos[1:11] if taxon.taxon_photos else []):
            thumb = TaxonPhoto(taxon=taxon, idx=i + 1, rounded=True)
            thumb.setFixedSize(*SIZE_SM)
            thumb.on_click.connect(self.image_window.display_taxon_fullscreen)
            set_pixmap_async(thumb, photo=photo, size='thumbnail')
            self.thumbnails.addWidget(thumb)

    def prev(self):
        if not self.hist_prev:
            return
        self.history_taxon = self.hist_prev.pop()
        self.hist_next.appendleft(self.displayed_taxon)
        self.on_view_taxon.emit(self.history_taxon)

    def next(self):
        if not self.hist_next:
            return
        self.history_taxon = self.hist_next.popleft()
        self.hist_prev.append(self.displayed_taxon)
        self.on_view_taxon.emit(self.history_taxon)

    def select_parent(self):
        self.on_view_taxon_by_id.emit(self.displayed_taxon.parent_id)

    def _update_buttons(self):
        """Update status and tooltip for nav and selection buttons"""
        self.prev_button.setEnabled(bool(self.hist_prev))
        self.prev_button.setToolTip(self.hist_prev[-1].full_name if self.hist_prev else None)
        self.next_button.setEnabled(bool(self.hist_next))
        self.next_button.setToolTip(self.hist_next[0].full_name if self.hist_next else None)
        self.parent_button.setEnabled(bool(self.displayed_taxon.parent))
        self.parent_button.setToolTip(
            self.displayed_taxon.parent.full_name if self.displayed_taxon.parent else None
        )
        self.select_button.setEnabled(True)
        # self.view_observations_button.setEnabled(True)
        self.link_button.setEnabled(True)
        self.link_button.setToolTip(self.displayed_taxon.url)


class TaxonomySection(HorizontalLayout):
    """Section to display ancestors and children of selected taxon"""

    def __init__(self, user_taxa: AppState):
        super().__init__()

        self.ancestors_group = self.add_group(
            'Ancestors', min_width=400, max_width=500, policy_min_height=False
        )
        self.ancestors_list = TaxonList(user_taxa)
        self.ancestors_group.addWidget(self.ancestors_list.scroller)

        self.children_group = self.add_group(
            'Children', min_width=400, max_width=500, policy_min_height=False
        )
        self.children_list = TaxonList(user_taxa)
        self.children_group.addWidget(self.children_list.scroller)

    def load(self, taxon: Taxon):
        """Populate taxon ancestors and children"""
        logger.debug(f'Loading {len(taxon.ancestors)} ancestors and {len(taxon.children)} children')

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
