from kivy.clock import Clock
from kivymd.uix.progressbar import MDProgressBar

FINISHED_COLOR = .1, .8, .1, 1
REMOVED_COLOR = 0, 0, 0, 0


class LoaderProgressBar(MDProgressBar):
    """ A progress bar with some extra features to sync with a BatchLoader """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.start_color = self.color
        self.event = None
        self.loader = None

    def start(self, max=100, loader=None):
        """ (Re)start the progress bar, and bind a BatchLoader's progress update events to it """
        # Cancel any previously scheduled on_complete event
        if self.event:
            self.event.cancel()
            self.event = None

        # Reset progress values
        self.value = 0
        self.max = max
        self.color = self.start_color
        self.loader = loader

        # Bind a BatchLoader's progress update events
        if self.loader:
            self.loader.bind(on_progress=self.update)
            self.loader.bind(on_complete=self.finish)

    def update(self, obj, value):
        self.value = value

    def finish(self, *args):
        """ Finish the progress by changing color, scheduling removal, and unbinding events """
        # TODO: Make this an animation? And cancel if progress is started again before anim finishes
        def remove_progress(*args):
            self.color = REMOVED_COLOR

        self.value = self.max
        self.color = FINISHED_COLOR
        self.event = Clock.schedule_once(remove_progress, 2)

        # Unbind events after completion, in case the loader is reused elsewhere
        if self.loader:
            self.loader.unbind(on_progress=self.update)
            self.loader.unbind(on_complete=self.finish)

