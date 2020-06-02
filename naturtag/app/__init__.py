from kivymd.app import MDApp
from kivymd.uix.snackbar import Snackbar


def alert(text, **kwargs):
    Snackbar(text=text, **kwargs).show()


def get_app():
    """ Wrapper to get the currently running app... in 60% fewer characters! """
    return MDApp.get_running_app()
