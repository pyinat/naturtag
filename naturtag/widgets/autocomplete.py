from logging import getLogger

from pyinaturalist_convert import TaxonAutocompleter
from PySide6.QtCore import QEvent, QStringListModel, Qt, Signal, Slot
from PySide6.QtWidgets import QCompleter, QLineEdit, QToolButton

from naturtag.app.style import fa_icon
from naturtag.constants import DB_PATH

logger = getLogger(__name__)


class TaxonAutocomplete(QLineEdit):
    """Autocomplete search that gets results from a local SQLite database. Allows cycling through
    autocomplete results with tab key.
    """

    on_select = Signal(int)  #: An autocomplete result was selected
    on_tab = Signal()  #: Tab key was pressed

    def __init__(self):
        super().__init__()
        self.setClearButtonEnabled(True)
        self.findChild(QToolButton).setIcon(fa_icon('mdi.backspace'))
        self.taxa: dict[str, int] = {}

        completer = QCompleter()
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.setCompleter(completer)
        self.on_tab.connect(self.next_result)

        # Results are fetched from FTS5, and passed to the completer via an intermediate model
        self.taxon_completer = TaxonAutocompleter(DB_PATH)
        self.textChanged.connect(self.search)
        self.model = QStringListModel()
        completer.activated.connect(self.select_taxon)
        completer.setModel(self.model)

    def event(self, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Tab:
            self.on_tab.emit()
            return True
        return super().event(event)

    def next_result(self):
        completer = self.completer()
        completer.popup().setCurrentIndex(completer.currentIndex())
        if not completer.setCurrentRow(completer.currentRow() + 1):
            completer.setCurrentRow(0)

    # TODO: Input delay
    def search(self, q: str):
        if len(q) > 1 and q not in self.taxa:
            self.taxa = {t.name: t.id for t in self.taxon_completer.search(q)}
            self.model.setStringList(self.taxa.keys())

    @Slot(str)
    def select_taxon(self, name: str):
        """Triggered by selecting a taxon name from the autocomplete list"""
        taxon_id = self.taxa.get(name)
        if taxon_id:
            self.on_select.emit(taxon_id)
