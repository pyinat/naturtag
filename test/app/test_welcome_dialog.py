"""Tests for WelcomeDialog."""

from unittest.mock import MagicMock, patch

import pytest

from naturtag.app.welcome_dialog import WelcomeDialog
from naturtag.storage import Settings

LOCALES = {'en': 'English (en)', 'fr': 'French (fr)'}


@pytest.fixture
def dialog(qtbot, mock_app):
    mock_app.settings.username = ''  # mock_app fixture defaults to 'testuser'

    with patch('naturtag.app.welcome_dialog.read_display_locales', return_value=LOCALES):
        dlg = WelcomeDialog(None, mock_app, MagicMock())
    qtbot.addWidget(dlg)
    return dlg


def test_skip__sets_disable_and_writes(dialog, mock_app):
    """Clicking Skip sets disable_obs_sync, writes settings, and rejects the dialog."""
    with patch.object(Settings, 'write') as mock_write:
        dialog._on_cancel()

    assert mock_app.settings.disable_obs_sync is True
    mock_write.assert_called_once()


def test_ok__empty_username_does_nothing(dialog, mock_app):
    """OK with no username entered does not schedule any work."""
    dialog.username_input.setText('')
    dialog._on_ok()

    mock_app.threadpool.schedule.assert_not_called()


def test_ok__valid_username_schedules_count(dialog, mock_app):
    """OK with a username schedules a background observation count fetch."""
    dialog.username_input.setText('naturalist')
    dialog._on_ok()

    mock_app.threadpool.schedule.assert_called_once()


def test_on_count_received(dialog, mock_app):
    """A successful count saves username, locale, and writes settings."""
    dialog.username_input.setText('naturalist')
    dialog.locale_combo.setCurrentText('French (fr)')

    with patch.object(Settings, 'write') as mock_write:
        dialog._on_count_received(42)

    assert mock_app.settings.username == 'naturalist'
    assert mock_app.settings.locale == 'fr'
    mock_write.assert_called_once()


def test_on_count_error__shows_error_and_resets_step(dialog):
    """A failed count shows the error label and returns to the input step."""
    dialog.username_input.setText('baduser')
    # Simulate being mid-count (step advanced by _on_ok, but don't need threadpool side effects)
    dialog._step = 'counting'

    dialog._on_count_error(Exception('not found'))

    assert dialog._step == 'input'
    assert not dialog.error_label.isHidden()
    assert 'baduser' in dialog.error_label.text()
