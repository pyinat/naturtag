"""Tests for MainWindow."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from naturtag.app.app import MainWindow, install_excepthook
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


@pytest.mark.parametrize(
    'username, disable_obs_sync',
    [
        ('testuser', False),
        ('', True),
    ],
    ids=['username_set', 'disable_obs_sync'],
)
def test_check_first_run__skipped(window, mock_app, username, disable_obs_sync):
    """No dialog shown when username is set or obs sync is disabled."""
    mock_app.settings.username = username
    mock_app.settings.disable_obs_sync = disable_obs_sync

    with patch('naturtag.app.app.WelcomeDialog') as mock_dialog_cls:
        window.check_first_run()

    mock_dialog_cls.assert_not_called()


def test_check_first_run__shows_dialog(window, mock_app):
    """WelcomeDialog is shown when username is empty and obs sync is not disabled."""
    mock_app.settings.username = ''
    mock_app.settings.disable_obs_sync = False

    with patch('naturtag.app.app.WelcomeDialog') as mock_dialog_cls:
        window.check_first_run()

    mock_dialog_cls.assert_called_once()
    mock_dialog_cls.return_value.exec.assert_called_once()


def test_close_event(window, mock_app):
    """closeEvent saves settings and state."""
    with patch.object(Settings, 'write') as mock_write:
        window.closeEvent(None)

    mock_write.assert_called_once()
    mock_app.state.write.assert_called_once()


def test_post_init__installs_excepthook(mock_app):
    """post_init() replaces sys.excepthook with a custom handler."""
    assert sys.excepthook is not sys.__excepthook__


def test_excepthook__logs_and_shows_dialog():
    """Custom excepthook logs critical and shows a QMessageBox for unhandled exceptions."""
    install_excepthook()
    hook = sys.excepthook

    with (
        patch('naturtag.app.app.logger') as mock_logger,
        patch('naturtag.app.app.QMessageBox') as mock_msgbox,
    ):
        try:
            raise RuntimeError('boom')
        except RuntimeError:
            hook(*sys.exc_info())

    args, kwargs = mock_logger.critical.call_args
    assert args == ('Unhandled exception',)
    assert kwargs['exc_info'][0] is RuntimeError
    mock_msgbox.return_value.exec.assert_called_once()
    assert 'boom' in mock_msgbox.return_value.setText.call_args[0][0]


def test_excepthook__passthrough_for_keyboard_interrupt():
    """KeyboardInterrupt is forwarded to the default hook, not shown as a dialog."""
    mock_default = MagicMock()
    with patch.object(sys, 'excepthook', mock_default):
        install_excepthook()
        hook = sys.excepthook

    exc = KeyboardInterrupt()
    hook(KeyboardInterrupt, exc, None)

    mock_default.assert_called_once_with(KeyboardInterrupt, exc, None)
