"""
I don't love this design, but the individual controllers need to talk to each other sometimes.
These functions get the controller objects from the currently running kivy App.
TODO: Maybe this could be managed by controllers calling methods on the App instead?
"""
from kivymd.app import MDApp


def get_settings_controller():
    """ Get settings controller object from running app, for use by other controllers """
    return MDApp.get_running_app().settings_controller


def get_taxon_selection_controller():
    return MDApp.get_running_app().taxon_selection_controller


def get_taxon_view_controller():
    return MDApp.get_running_app().taxon_view_controller
