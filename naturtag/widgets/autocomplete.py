from logging import getLogger

from pyinaturalist_convert import DATA_DIR, TaxonAutocompleter
from PySide6.QtCore import QEvent, QStringListModel, Qt, Signal
from PySide6.QtWidgets import QCompleter, QLineEdit, QToolButton

from naturtag.app.style import fa_icon
from naturtag.widgets import VerticalLayout

logger = getLogger(__name__)
DB_FILE = DATA_DIR / 'taxa.db'


class TaxonAutocomplete(VerticalLayout):
    on_select = Signal(int)

    def __init__(self):
        super().__init__()

        self.search_input = TabCompleteLineEdit()
        self.search_input.setClearButtonEnabled(True)
        self.search_input.findChild(QToolButton).setIcon(fa_icon('mdi.backspace'))
        self.addWidget(self.search_input)
        self.taxa: dict[str, int] = {}

        completer = QCompleter()
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.search_input.setCompleter(completer)

        self.taxon_completer = TaxonAutocompleter()
        self.search_input.textChanged.connect(self.search)
        completer.activated.connect(self.select_taxon)

        self.model = QStringListModel()
        completer.setModel(self.model)

    # TODO: Input delay
    def search(self, q: str):
        if len(q) > 1 and q not in self.taxa:
            self.taxa = {t.name: t.id for t in self.taxon_completer.search(q)}
            self.model.setStringList(self.taxa.keys())

    def select_taxon(self, name: str):
        """Triggered by selecting a taxon name from the autocomplete list"""
        taxon_id = self.taxa.get(name)
        if taxon_id:
            self.on_select.emit(taxon_id)


class TabCompleteLineEdit(QLineEdit):
    """LineEdit that allows cycling through autocomplete results with tab key.
    Source: https://stackoverflow.com/a/28976373/15592055
    """

    on_tab = Signal()

    def __init__(self):
        super().__init__()
        self.on_tab.connect(self.next_completion)

    def next_completion(self):
        completer = self.completer()
        completer.popup().setCurrentIndex(completer.currentIndex())
        if not completer.setCurrentRow(completer.currentRow() + 1):
            completer.setCurrentRow(0)

    def event(self, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Tab:
            self.on_tab.emit()
            return True
        return super().event(event)
