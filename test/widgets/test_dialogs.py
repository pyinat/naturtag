"""Tests for WelcomeDialog and ResetDbDialog."""

from unittest.mock import MagicMock, patch

import pytest

from naturtag.storage import Settings
from naturtag.widgets.dialogs import ResetDbDialog, WelcomeDialog

LOCALES = {'en': 'English (en)', 'fr': 'French (fr)'}


# WelcomeDialog
# ----------------------------------------


@pytest.fixture
def dialog(qtbot, mock_app):
    mock_app.settings.username = ''  # mock_app fixture defaults to 'testuser'

    with patch('naturtag.widgets.dialogs.read_display_locales', return_value=LOCALES):
        dlg = WelcomeDialog(None, mock_app, MagicMock())
    qtbot.addWidget(dlg)
    return dlg


def test_skip(dialog, mock_app):
    """Clicking Skip sets disable_obs_sync, writes settings, and rejects the dialog."""
    with patch.object(Settings, 'write') as mock_write:
        dialog._on_cancel()

    assert mock_app.settings.disable_obs_sync is True
    mock_write.assert_called_once()


def test_ok(dialog, mock_app):
    """OK with a username schedules a background observation count fetch."""
    dialog.username_input.setText('naturalist')
    dialog._on_ok()
    mock_app.threadpool.schedule.assert_called_once()


def test_ok__empty_username(dialog, mock_app):
    dialog.username_input.setText('')
    dialog._on_ok()
    mock_app.threadpool.schedule.assert_not_called()


def test_on_count_received(dialog, mock_app):
    """A successful count saves username, locale, and writes settings."""
    dialog.username_input.setText('naturalist')
    dialog.locale_combo.setCurrentText('French (fr)')

    with patch.object(Settings, 'write') as mock_write:
        dialog._on_count_received(42)

    assert mock_app.settings.username == 'naturalist'
    assert mock_app.settings.locale == 'fr'
    mock_write.assert_called_once()


def test_on_count_error(dialog):
    """A failed count shows the error label and returns to the input step."""
    dialog.username_input.setText('baduser')
    # Simulate being mid-count (step advanced by _on_ok, but don't need threadpool side effects)
    dialog._step = 'counting'

    dialog._on_count_error(Exception('not found'))

    assert dialog._step == 'input'
    assert not dialog.error_label.isHidden()
    assert 'baduser' in dialog.error_label.text()


# ResetDbDialog
# ----------------------------------------


@pytest.fixture
def reset_dialog(qtbot):
    dlg = ResetDbDialog(None)
    qtbot.addWidget(dlg)
    return dlg


def test_reset_dialog__initial_state(reset_dialog):
    """Dialog starts with spinner visible and OK button hidden."""
    assert not reset_dialog.progress_bar.isHidden()
    assert reset_dialog.button_box.isHidden()


def test_reset_dialog__on_result(reset_dialog):
    """on_result hides the spinner, shows OK, and updates the status text."""
    reset_dialog.on_result(None)

    assert reset_dialog.progress_bar.isHidden()
    assert not reset_dialog.button_box.isHidden()
    assert 'complete' in reset_dialog.status_label.text().lower()


def test_reset_dialog__on_error(reset_dialog):
    """on_error hides the spinner, shows OK, and includes the error message."""
    reset_dialog.on_error(Exception('disk full'))

    assert reset_dialog.progress_bar.isHidden()
    assert not reset_dialog.button_box.isHidden()
    assert 'disk full' in reset_dialog.status_label.text()
