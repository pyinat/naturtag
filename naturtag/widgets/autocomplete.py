from logging import getLogger

from pyinaturalist_convert import DATA_DIR, TaxonAutocompleter
from PySide6.QtCore import QStringListModel, Qt, Signal
from PySide6.QtWidgets import QCompleter, QLineEdit, QToolButton

from naturtag.app.style import fa_icon
from naturtag.widgets import VerticalLayout

logger = getLogger(__name__)
DB_FILE = DATA_DIR / 'taxa.db'


class TaxonAutocomplete(VerticalLayout):
    selection = Signal(int)

    def __init__(self):
        super().__init__()

        self.search_input = QLineEdit()
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
            self.selection.emit(taxon_id)
