from logging import getLogger
from typing import Union

import qdarktheme
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication
from qtawesome import icon

from naturtag.constants import QSS_PATH

CustomPalette = dict[QPalette.ColorRole, Union[str, tuple]]

YELLOWGREEN = '#9acd32'
YELLOWGREEN_DARK = '#82c32d'
PALEBLUE = '#80cfee'
PALEBLUE_DARK = '#62bee3'

# GRAYBLUE = (63, 113, 172)
# SILVER = (173, 168, 182)
# PRPL = (200, 0, 200)
# LAVENDER = (180, 180, 255)
# UMBER = (95, 84, 73)
# CERULEAN = (64, 89, 173)
# VIOLET = (42, 30, 92)

logger = getLogger(__name__)


def fa_icon(icon_name, secondary: bool = False, **kwargs):
    """Get a FontAwesome icon, using either a primary or secondary color from the palette"""
    palette = QApplication.instance().palette()
    return icon(
        icon_name,
        color=palette.link().color() if secondary else palette.highlight().color(),
        color_disabled='gray',
        **kwargs,
    )


def set_theme(dark_mode: bool = True):
    app = QApplication.instance()
    theme_str = 'dark' if dark_mode else 'light'
    logger.debug(f'Setting theme: {theme_str}')

    palette = qdarktheme.load_palette(theme_str)
    if dark_mode:
        palette = mod_dark_palette(palette)
    else:
        palette = mod_light_palette(palette)
    app.setPalette(palette)

    base_stylesheet = qdarktheme.load_stylesheet(theme=theme_str)
    with open(QSS_PATH) as f:
        extra_stylesheet = f.read()
    app.setStyleSheet(base_stylesheet + '\n' + extra_stylesheet)


# TODO: Update to use qdarktheme.setup_theme() from version 2
#   Requires strings for both color names and values?
def set_theme_2(dark_mode: bool = True):
    theme_str = 'dark' if dark_mode else 'light'
    logger.debug(f'Setting theme: {theme_str}')

    dark_palette = {
        'highlight': PALEBLUE,
        'link': YELLOWGREEN,  # Secondary highlight
        'link-visited': (46, 70, 94, 85),  # Hover highlight
    }
    light_palette = {
        'highlight': PALEBLUE_DARK,
        'link': YELLOWGREEN,
        'link-visited': (181, 202, 244, 85),
    }

    with open(QSS_PATH) as f:
        extra_stylesheet = f.read()
    qdarktheme.setup_theme(
        theme=theme_str,
        additional_qss=extra_stylesheet,
        custom_colors={'[dark]': dark_palette, '[light]': light_palette},
    )


def mod_dark_palette(palette: QPalette) -> QPalette:
    enabled: CustomPalette = {
        # QPalette.AlternateBase: (66, 66, 66),
        # QPalette.Base: (42, 42, 42),
        # QPalette.BrightText: (180, 180, 180),
        # QPalette.Button: (53, 53, 53),
        # QPalette.ButtonText: (180, 180, 180),
        # QPalette.Dark: (35, 35, 35),
        # QPalette.Highlight: (42, 130, 218),
        QPalette.Highlight: PALEBLUE,
        # QPalette.HighlightedText: (180, 180, 180),
        # QPalette.Light: (180, 180, 180),
        QPalette.Link: YELLOWGREEN,  # Secondary highlight
        QPalette.LinkVisited: (46, 70, 94, 85),  # Hover highlight
        # QPalette.Midlight: (90, 90, 90),
        # QPalette.Shadow: (20, 20, 20),
        # QPalette.Text: (180, 180, 180),
        # QPalette.ToolTipBase: (53, 53, 53),
        # QPalette.ToolTipText: (180, 180, 180),
        # QPalette.Window: (53, 53, 53),
        # QPalette.WindowText: (180, 180, 180),
    }
    disabled: CustomPalette = {}
    return _modify_palette(palette, enabled, disabled)


def mod_light_palette(palette) -> QPalette:
    enabled: CustomPalette = {
        # QPalette.AlternateBase: (245, 245, 245),
        # QPalette.Base: (237, 237, 237),
        # QPalette.BrightText: (0, 0, 0),
        # QPalette.Button: (240, 240, 240),
        # QPalette.ButtonText: (0, 0, 0),
        # QPalette.Dark: (225, 225, 225),
        QPalette.Highlight: PALEBLUE_DARK,
        # QPalette.HighlightedText: (0, 0, 0),
        # QPalette.Light: (180, 180, 180),
        QPalette.Link: YELLOWGREEN,
        QPalette.LinkVisited: (181, 202, 244, 85),
        # QPalette.Midlight: (200, 200, 200),
        # QPalette.Shadow: (20, 20, 20),
        # QPalette.Text: (0, 0, 0),
        # QPalette.ToolTipBase: (240, 240, 240),
        # QPalette.ToolTipText: (0, 0, 0),
        # QPalette.Window: (240, 240, 240),
        # QPalette.WindowText: (0, 0, 0),
    }
    disabled: CustomPalette = {}
    return _modify_palette(palette, enabled, disabled)


def _modify_palette(palette: QPalette, enabled: CustomPalette, disabled: CustomPalette) -> QPalette:
    def _get_qcolor(color):
        return QColor(*color) if isinstance(color, tuple) else QColor(color)

    for role, color in enabled.items():
        palette.setColor(role, _get_qcolor(color))
    for role, color in disabled.items():
        palette.setColor(QPalette.Disabled, role, _get_qcolor(color))
    return palette
