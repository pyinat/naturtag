"""First-run dialog that collects the username and shows live observation download progress"""

from logging import getLogger
from time import monotonic

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

logger = getLogger(__name__)

# Phases used to track which UI state the dialog is in
_PHASE_INPUT = 'input'
_PHASE_SYNCING = 'syncing'


class WelcomeDialog(QDialog):
    """Dialog shown on first startup when no username is configured.

    * Input: user enters their iNaturalist username.
    * Count: spinner while the API returns the total observation count.
    * Download: show progress bar tracking the background sync.

    Closing during phase 1 cancels everything. Closing during phases 2/3 just
    dismisses the dialog; the download continues in the background.
    """

    def __init__(self, parent, app, observation_controller):
        super().__init__(parent)
        self.app = app
        self.observation_controller = observation_controller
        self._phase = _PHASE_INPUT

        self.setWindowTitle('Download iNaturalist Observations')
        self.setMinimumWidth(420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Part 1: username input
        self.intro_label = QLabel('Enter your iNaturalist username to download your observations.')
        self.intro_label.setWordWrap(True)
        layout.addWidget(self.intro_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('iNaturalist username')
        self.username_input.returnPressed.connect(self._on_ok)
        layout.addWidget(self.username_input)

        # Part 2: status label and progress bar (hidden initially)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.hide()
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)  # indeterminate until we know the total
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.background_note = QLabel('You can use the app while downloading continues.')
        self.background_note.setWordWrap(True)
        self.background_note.hide()
        layout.addWidget(self.background_note)

        # Error label (hidden until needed)
        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet('color: red;')
        self.error_label.hide()
        layout.addWidget(self.error_label)

        # Button box: OK/Cancel in part 1; "Run in background" in part 2
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._on_ok)
        self.button_box.rejected.connect(self._on_cancel)
        layout.addWidget(self.button_box)

        self.background_button = QPushButton('Run in background')
        self.background_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.background_button.clicked.connect(self.accept)
        self.background_button.hide()
        layout.addWidget(self.background_button)

    # Transitions
    # ----------------------------------------

    def _start_count(self, username: str):
        """Switch to the indeterminate spinner while we fetch the total count."""
        self._phase = 'counting'

        self.intro_label.hide()
        self.username_input.hide()
        self.button_box.hide()
        self.error_label.hide()

        self.status_label.setText(f'Checking observations for <b>{username}</b>…')
        self.status_label.show()
        self.progress_bar.setMaximum(0)  # indeterminate
        self.progress_bar.show()

    def _start_download(self, total: int):
        """Switch to the determinate progress bar now that we know the total."""
        self._phase = _PHASE_SYNCING
        self._sync_start_time = monotonic()

        self.progress_bar.setMaximum(total if total > 0 else 1)
        self.progress_bar.setValue(0)
        self._update_dl_label(0, total)
        self.background_note.show()
        self.background_button.show()

    def _update_dl_label(self, loaded: int, total: int):
        text = f'{loaded} / {total} observations downloaded'
        if loaded > 0 and total > loaded:
            elapsed = monotonic() - self._sync_start_time
            remaining_secs = elapsed / loaded * (total - loaded)
            text += f' — about {_format_duration(remaining_secs)} remaining'
        self.status_label.setText(text)

    # Button handlers
    # ----------------------------------------

    def _on_ok(self):
        """Handle OK / Enter in the username input phase."""
        if self._phase != _PHASE_INPUT:
            return

        username = self.username_input.text().strip()
        if not username:
            self.username_input.setFocus()
            return

        # Save the username immediately
        self.app.settings.username = username
        self.app.settings.write()

        self._start_count(username)

        # Fetch total count from API in a background thread
        signals = self.app.threadpool.schedule(lambda: self.app.client.observations.count(username))
        signals.on_result.connect(self._on_count_received)
        signals.on_error.connect(self._on_count_error)

    def _on_cancel(self):
        """Cancel during part 1 — do not start a download."""
        if self._phase == _PHASE_INPUT:
            self.reject()
        else:
            # Shouldn't normally be reachable (button is hidden), but be safe
            self.accept()

    # Slots for threadpool/controller signals
    # ----------------------------------------

    @Slot(object)
    def _on_count_received(self, total: int):
        """API returned the total observation count; start downloading."""
        logger.info(f'Total observations for user: {total}')
        self._start_download(total)

        # Connect to live download progress
        self.observation_controller.on_sync_progress.connect(self._on_sync_progress)
        self.observation_controller.on_sync_finished.connect(self._on_sync_finished)

        # Set total results so on_sync_progress emits meaningful values from the first page.
        self.observation_controller.total_results = total

        # DB is empty on first run; set this flag so the observations tab populates when 1st page arrives
        self.observation_controller._is_cold_start = True

        # Kick off the actual download
        self.observation_controller.start_background_sync()

    @Slot(Exception)
    def _on_count_error(self, exc: Exception):
        """Show an error and let the user correct the username."""
        logger.warning('Could not fetch observation count:', exc_info=exc)
        self._phase = _PHASE_INPUT

        self.progress_bar.hide()
        self.status_label.hide()
        self.intro_label.show()
        self.username_input.show()
        self.button_box.show()

        self.error_label.setText(
            f'Could not fetch observations for <b>{self.app.settings.username}</b>. '
            'Please check the username and your internet connection.'
        )
        self.error_label.show()
        self.username_input.setFocus()

    @Slot(int, int)
    def _on_sync_progress(self, loaded: int, total: int):
        """Update the progress bar as sync pages arrive."""
        if self._phase != _PHASE_SYNCING:
            return
        if total > 0 and self.progress_bar.maximum() != total:
            self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(loaded)
        self._update_dl_label(loaded, total)

    @Slot()
    def _on_sync_finished(self):
        """Auto-close when the download completes."""
        logger.info('Download finished; closing sync dialog')
        self.accept()


def _format_duration(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f'{minutes}:{secs}'
