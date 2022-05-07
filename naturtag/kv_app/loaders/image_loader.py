from typing import Any

from kivy.uix.widget import Widget

from naturtag.kv_app import get_app
from naturtag.loaders import WidgetBatchLoader
from naturtag.widgets import ImageMetaTile


class ImageBatchLoader(WidgetBatchLoader):
    """Loads batches of ImageMetaTiles"""

    def __init__(self, **kwargs):
        super().__init__(widget_cls=ImageMetaTile, **kwargs)

    async def load_widget(self, item: Any, parent: Widget = None, **kwargs) -> Widget:
        """Add an ImageMetaTile to its parent view and bind its click event"""
        widget = await super().load_widget(item, parent, **kwargs)
        widget.bind(on_touch_down=get_app().image_selection_controller.on_image_click)
        return widget
