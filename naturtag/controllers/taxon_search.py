"""Components for searching for taxa"""
from logging import getLogger
from typing import Optional

from pyinaturalist import IconPhoto, Taxon
from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QPushButton, QWidget

from naturtag.app.style import fa_icon
from naturtag.client import INAT_CLIENT
from naturtag.constants import COMMON_RANKS, RANKS, SELECTABLE_ICONIC_TAXA
from naturtag.settings import Settings
from naturtag.widgets import (
    GridLayout,
    HorizontalLayout,
    PixmapLabel,
    TaxonAutocomplete,
    ToggleSwitch,
    VerticalLayout,
)
from naturtag.widgets.images import FAIcon

logger = getLogger(__name__)


class TaxonSearch(VerticalLayout):
    on_results = Signal(list)  #: New search results were loaded
    on_reset = Signal()  #: Input fields were reset

    def __init__(self, settings: Settings):
        super().__init__()
        self.selected_taxon: Taxon = None
        self.settings = settings
        self.setAlignment(Qt.AlignTop)

        # Taxon name autocomplete
        self.autocomplete = TaxonAutocomplete()
        search_group = self.add_group('Search', self, width=400)
        search_group.addWidget(self.autocomplete)
        self.autocomplete.returnPressed.connect(self.search)

        # Category inputs
        self.iconic_taxon_filters = IconicTaxonFilters()
        categories = self.add_group('Categories', self, width=400)
        categories.addWidget(self.iconic_taxon_filters)

        # Rank inputs
        self.ranks = self.add_group('Rank', self, width=400)
        self.reset_ranks()

        # Clear exact rank after selecting min or max, and vice versa
        self.min_rank.dropdown.activated.connect(self.exact_rank.reset)
        self.max_rank.dropdown.activated.connect(self.exact_rank.reset)
        self.exact_rank.dropdown.activated.connect(self.min_rank.reset)
        self.exact_rank.dropdown.activated.connect(self.max_rank.reset)

        # Button to search for children of selected taxon
        # TODO: If more than one toggle filter is added, consolidate with settings_menu.ToggleSetting
        group_box = self.add_group('Parent', self, width=400)
        button_layout = HorizontalLayout()
        button_layout.setAlignment(Qt.AlignLeft)
        button_layout.addWidget(FAIcon('mdi.file-tree', size=20))
        group_box.addLayout(button_layout)
        self.search_children_desc = QLabel('Search within children of selected taxon')
        self.search_children_desc.setTextFormat(Qt.RichText)
        button_layout.addWidget(self.search_children_desc)
        button_layout.addStretch()
        self.search_children_switch = ToggleSwitch()
        button_layout.addWidget(self.search_children_switch)

        # Search/reset buttons
        button_layout = HorizontalLayout()
        search_button = QPushButton('Search')
        search_button.setMaximumWidth(200)
        search_button.setIcon(fa_icon('fa.search'))
        search_button.clicked.connect(self.search)
        button_layout.addWidget(search_button)

        reset_button = QPushButton('Reset')
        reset_button.setMaximumWidth(200)
        reset_button.setIcon(fa_icon('mdi.backspace'))
        reset_button.clicked.connect(self.reset)
        button_layout.addWidget(reset_button)
        self.addLayout(button_layout)

    def search(self):
        """Search for taxa with the currently selected filters"""
        taxon_ids = self.iconic_taxon_filters.selected_iconic_taxa
        if self.search_children_switch.isChecked():
            taxon_ids.append(self.selected_taxon.id)

        taxa = INAT_CLIENT.taxa.search(
            q=self.autocomplete.text(),
            taxon_id=taxon_ids,
            rank=self.exact_rank.text,
            min_rank=self.min_rank.text,
            max_rank=self.max_rank.text,
            preferred_place_id=self.settings.preferred_place_id,
            locale=self.settings.locale,
            limit=30,
        ).all()

        logger.debug('\n'.join([str(t) for t in taxa[:10]]))
        self.on_results.emit(taxa)

    def reset(self):
        """Reset all search filters"""
        self.autocomplete.setText('')
        self.iconic_taxon_filters.reset()
        self.reset_ranks()
        self.search_children_switch.setChecked(False)
        self.on_reset.emit()

    def reset_ranks(self):
        self.exact_rank = RankList('Exact', 'fa5s.equals', all_ranks=self.settings.all_ranks)
        self.min_rank = RankList(
            'Minimum', 'fa5s.greater-than-equal', all_ranks=self.settings.all_ranks
        )
        self.max_rank = RankList(
            'Maximum', 'fa5s.less-than-equal', all_ranks=self.settings.all_ranks
        )
        self.ranks.clear()
        self.ranks.addLayout(self.exact_rank)
        self.ranks.addLayout(self.min_rank)
        self.ranks.addLayout(self.max_rank)

    @Slot(Taxon)
    def set_taxon(self, taxon: Taxon):
        self.selected_taxon = taxon
        self.search_children_desc.setText(f'Search within children of <b><i>{taxon.name}</i></b>')


class IconicTaxonFilters(QWidget):
    """Filters for iconic taxa"""

    on_select = Signal(int)  # A filter was selected

    def __init__(self):
        super().__init__()
        self.button_layout = GridLayout(self, n_columns=6)
        self.setFocusPolicy(Qt.StrongFocus)

        for id, name in SELECTABLE_ICONIC_TAXA.items():
            button = IconicTaxonButton(id, name)
            button.clicked.connect(self.on_click)
            self.button_layout.addWidget(button)

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
            self.on_select.emit(button_taxon_id)


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

    def __init__(self, label: str, icon_str: str, all_ranks: bool = False):
        super().__init__()
        self.setAlignment(Qt.AlignLeft)
        self.addWidget(FAIcon(icon_str, size=20))
        self.addWidget(QLabel(label))
        self.addStretch()

        ranks = RANKS if all_ranks else COMMON_RANKS
        self.dropdown = QComboBox()
        self.dropdown.addItems([''] + ranks[::-1])
        self.addWidget(self.dropdown)

    def reset(self):
        self.dropdown.setCurrentIndex(0)

    @property
    def text(self) -> Optional[str]:
        return self.dropdown.currentText() or None
