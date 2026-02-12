"""Tests for MainWindow."""

from unittest.mock import patch

import pytest

from naturtag.app.app import MainWindow
from naturtag.storage import Settings


@pytest.fixture
def window(qtbot, mock_app):
    win = MainWindow(mock_app)
    qtbot.addWidget(win)
    return win


def test_init__tabs(window):
    tab_labels = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert 'Photos' in tab_labels
    assert 'Taxonomy' in tab_labels
    assert 'Observations' in tab_labels


def test_init__log_tab_visible(qtbot, mock_app):
    """Log tab is visible when show_logs is True in settings."""
    mock_app.settings.show_logs = True
    win = MainWindow(mock_app)
    qtbot.addWidget(win)

    assert win.tabs.isTabVisible(win.log_tab_idx)


def test_toggle_log_tab(window):
    """toggle_log_tab shows and hides the log tab."""
    assert not window.tabs.isTabVisible(window.log_tab_idx)

    window.toggle_log_tab(True)
    assert window.tabs.isTabVisible(window.log_tab_idx)

    window.toggle_log_tab(False)
    assert not window.tabs.isTabVisible(window.log_tab_idx)


def test_info(window):
    """info() shows message in the status bar."""
    window.info('Test message', timeout=1000)
    assert window.statusbar.currentMessage() == 'Test message'


@pytest.mark.parametrize(
    'method, controller_attr',
    [
        ('switch_tab_observations', 'observation_controller'),
        ('switch_tab_taxa', 'taxon_controller'),
        ('switch_tab_photos', 'image_controller'),
    ],
    ids=['observations', 'taxa', 'photos'],
)
def test_switch_tab(window, method, controller_attr):
    getattr(window, method)()
    assert window.tabs.currentWidget() is getattr(window, controller_attr)


def test_toggle_fullscreen(window):
    """toggle_fullscreen saves window flags and attempts to enter fullscreen.

    Note: isFullScreen() always returns False on the offscreen QPA platform,
    so we verify the method runs and saves the original window flags.
    """
    assert not window.isFullScreen()
    assert not hasattr(window, '_flags')
    window.toggle_fullscreen()
    assert hasattr(window, '_flags')


def test_close_event(window, mock_app):
    """closeEvent saves settings and state."""
    with patch.object(Settings, 'write') as mock_write:
        window.closeEvent(None)

    mock_write.assert_called_once()
    mock_app.state.write.assert_called_once()


def test_check_username__already_set(window, mock_app):
    """No dialog shown when username is already configured."""
    mock_app.settings.username = 'testuser'

    with patch('naturtag.app.app.QInputDialog.getText') as mock_dialog:
        window.check_username()

    mock_dialog.assert_not_called()


@pytest.mark.parametrize(
    'dialog_return, expected_username, write_called',
    [
        (('newuser', True), 'newuser', True),
        (('', False), '', False),
    ],
    ids=['confirmed', 'cancelled'],
)
def test_check_username__empty(window, mock_app, dialog_return, expected_username, write_called):
    """Dialog is shown when username is empty; result depends on user action."""
    mock_app.settings.username = ''

    with (
        patch('naturtag.app.app.QInputDialog.getText', return_value=dialog_return) as mock_dialog,
        patch.object(Settings, 'write') as mock_write,
    ):
        window.check_username()

    mock_dialog.assert_called_once()
    assert mock_app.settings.username == expected_username
    assert mock_write.called == write_called
