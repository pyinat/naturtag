"""Components for searching for taxa"""
from logging import getLogger
from typing import Optional

from pyinaturalist import RANKS, IconPhoto
from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGroupBox,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from naturtag.app.style import fa_icon
from naturtag.client import INAT_CLIENT
from naturtag.constants import SELECTABLE_ICONIC_TAXA
from naturtag.settings import Settings
from naturtag.widgets import GridLayout, HorizontalLayout, PixmapLabel, TaxonAutocomplete, VerticalLayout

logger = getLogger(__name__)


ignore_terms = ['sub', 'super', 'infra', 'epi', 'hybrid']
COMMON_RANKS = [r for r in RANKS if not any([k in r for k in ignore_terms])][::-1]


class TaxonSearch(VerticalLayout):
    """Taxon search"""

    new_results = Signal(list)
    reset_results = Signal()

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.setAlignment(Qt.AlignTop)

        # Taxon name autocomplete
        self.autocomplete = TaxonAutocomplete()
        group_box = QGroupBox('Search')
        group_box.setFixedWidth(400)
        group_box.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        group_box.setLayout(self.autocomplete)
        self.addWidget(group_box)

        # Category inputs
        categories = VerticalLayout()
        group_box = QGroupBox('Categories')
        group_box.setFixedWidth(400)
        group_box.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        group_box.setLayout(categories)
        self.addWidget(group_box)
        self.iconic_taxon_filters = IconicTaxonFilters()
        categories.addWidget(self.iconic_taxon_filters)

        # Rank inputs
        self.ranks = VerticalLayout()
        group_box = QGroupBox('Rank')
        group_box.setFixedWidth(400)
        group_box.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        group_box.setLayout(self.ranks)
        self.addWidget(group_box)
        self.reset_ranks()

        # Clear exact rank after selecting min or max, and vice versa
        self.min_rank.dropdown.activated.connect(self.exact_rank.reset)
        self.max_rank.dropdown.activated.connect(self.exact_rank.reset)
        self.exact_rank.dropdown.activated.connect(self.min_rank.reset)
        self.exact_rank.dropdown.activated.connect(self.max_rank.reset)

        # Search/reset buttons
        button_layout = HorizontalLayout()
        search_button = QPushButton('Search')
        search_button.setIcon(fa_icon('fa.search'))
        search_button.clicked.connect(self.search)
        button_layout.addWidget(search_button)

        reset_button = QPushButton('Reset')
        reset_button.setIcon(fa_icon('mdi.backspace'))
        reset_button.clicked.connect(self.reset)
        button_layout.addWidget(reset_button)
        self.addLayout(button_layout)

    def search(self):
        """Search for taxa with the currently selected filters"""
        taxa = INAT_CLIENT.taxa.search(
            q=self.autocomplete.search_input.text(),
            taxon_id=self.iconic_taxon_filters.selected_iconic_taxa,
            rank=self.exact_rank.text,
            min_rank=self.min_rank.text,
            max_rank=self.max_rank.text,
            preferred_place_id=self.settings.preferred_place_id,
            locale=self.settings.locale,
        ).limit(20)
        logger.debug('\n'.join([str(t) for t in taxa]))
        self.new_results.emit(taxa)

    def reset(self):
        """Reset all search filters"""
        self.autocomplete.search_input.setText('')
        self.iconic_taxon_filters.reset()
        self.reset_ranks()
        self.reset_results.emit()

    def reset_ranks(self):
        self.exact_rank = RankList('Exact', all_ranks=self.settings.all_ranks)
        self.min_rank = RankList('Minimum', all_ranks=self.settings.all_ranks)
        self.max_rank = RankList('Maximum', all_ranks=self.settings.all_ranks)
        self.ranks.clear()
        self.ranks.addLayout(self.exact_rank)
        self.ranks.addLayout(self.min_rank)
        self.ranks.addLayout(self.max_rank)


class IconicTaxonFilters(QWidget):
    """Filters for iconic taxa"""

    selected_taxon = Signal(int)

    def __init__(self):
        super().__init__()
        self.button_layout = GridLayout(n_columns=6)
        self.setLayout(self.button_layout)
        self.setFocusPolicy(Qt.StrongFocus)

        for id, name in SELECTABLE_ICONIC_TAXA.items():
            button = IconicTaxonButton(id, name)
            button.clicked.connect(self.on_click)
            self.button_layout.add_widget(button)

    @property
    def selected_iconic_taxa(self) -> list[int]:
        return [t.taxon_id for t in self.button_layout.widgets if t.isChecked()]

    def reset(self, except_id: str = None):
        """Reset all buttons, or all except one"""
        for button in self.button_layout.widgets:
            if button.taxon_id != except_id:
                button.setChecked(False)

    @Slot()
    def on_click(self):
        """Ctrl-click to select multiple buttons. Otherwise, when pressing a button, uncheck all
        other buttons and display the corresponding taxon.
        """
        if QApplication.keyboardModifiers() != Qt.ControlModifier:
            button_taxon_id = self.sender().taxon_id
            self.reset(except_id=button_taxon_id)
            self.selected_taxon.emit(button_taxon_id)


class IconicTaxonButton(QPushButton):
    """Button used as a filter for iconic taxa"""

    def __init__(self, taxon_id: int, name: str):
        super().__init__()
        self.taxon_id = taxon_id
        self.name = name

        photo = IconPhoto.from_iconic_taxon(name)
        img = PixmapLabel(url=photo.thumbnail_url)
        self.setIcon(QIcon(img.pixmap()))
        self.setIconSize(QSize(45, 45))

        self.setCheckable(True)
        self.setFixedSize(50, 50)
        self.setContentsMargins(0, 0, 0, 0)
        self.setToolTip(name)


class RankList(HorizontalLayout):
    """Taxonomic rank dropdown"""

    def __init__(self, label: str, all_ranks: bool = False):
        super().__init__()
        ranks = RANKS if all_ranks else COMMON_RANKS
        self.addWidget(QLabel(label))
        self.dropdown = QComboBox()
        self.dropdown.addItems([''] + ranks[::-1])
        self.addWidget(self.dropdown)

    def reset(self):
        self.dropdown.setCurrentIndex(0)

    @property
    def text(self) -> Optional[str]:
        return self.dropdown.currentText() or None
