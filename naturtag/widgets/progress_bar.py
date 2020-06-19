from kivy.clock import Clock
from kivymd.uix.progressbar import MDProgressBar

FINISHED_COLOR = .1, .8, .1, 1
REMOVED_COLOR = 0, 0, 0, 0


class LoaderProgressBar(MDProgressBar):
    """ A progress bar with some convenience wrappers to bind to a BatchLoader """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.start_color = self.color

    def start(self, max=100):
        self.value = 0
        self.max = max
        self.color = self.start_color

    def update(self, obj, value):
        self.value = value

    def finish(self, *args):
        # TODO: Make this an animation? And cancel if progress is started again before anim finishes
        def remove_progress(*args):
            self.color = REMOVED_COLOR

        self.value = self.max
        self.color = FINISHED_COLOR
        Clock.schedule_once(remove_progress, 2)
