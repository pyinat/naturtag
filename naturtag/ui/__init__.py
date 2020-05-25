from kivymd.app import MDApp


def get_app_settings():
    """ Get settings controller object from running app, for use by other controllers """
    return MDApp.get_running_app().settings_controller
