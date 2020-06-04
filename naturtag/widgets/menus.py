from kivy.properties import ObjectProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy_garden.contextmenu import AbstractMenuItemHoverable, ContextMenu, ContextMenuText


class PhotoContextMenu(ContextMenu):
    """ Context menu with a reference to an image, which can be set by an event handler on the parent
    controller
    """
    selected_image = ObjectProperty()


class PhotoContextMenuItem(ButtonBehavior, ContextMenuText, AbstractMenuItemHoverable):
    """ Menu item that has a reference to an image, and hides its parent menu after selecting """
    @property
    def selected_image(self):
        return self.parent.selected_image

    @property
    def metadata(self):
        return self.parent.selected_image.metadata

    def on_release(self, *args):
        super().on_release()
        self.parent.hide()
