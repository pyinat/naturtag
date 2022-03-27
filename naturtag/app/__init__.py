from typing import TYPE_CHECKING

from kivymd.app import MDApp
from kivy.logger import Logger
from kivymd.uix.snackbar import Snackbar

from pyinaturalist import enable_logging

enable_logging('DEBUG')
Logger.setLevel('DEBUG')


if TYPE_CHECKING:
    from naturtag.app.app import NaturtagApp


def alert(text, **kwargs):
    """Show a popup 'snackbar' message"""
    Snackbar(text=text, **kwargs).open()


def get_app() -> 'NaturtagApp':
    """Wrapper to get the currently running app"""
    return MDApp.get_running_app()
