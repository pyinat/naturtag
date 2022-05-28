from logging import getLogger

from attr import fields
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIntValidator, QKeySequence, QShortcut, QValidator
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout

from naturtag.settings import Settings
from naturtag.widgets import IconLabel, StylableWidget, ToggleSwitch

logger = getLogger(__name__)


class SettingsMenu(StylableWidget):
    """Application settings menu, with input widgets connected to values in settings file"""

    message = Signal(str)

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.settings_layout = QVBoxLayout(self)

        inat = self.add_group('iNaturalist', self.settings_layout)
        inat.addLayout(TextSetting(settings, icon_str='fa.user', setting_attr='username'))
        inat.addLayout(TextSetting(settings, icon_str='fa.globe', setting_attr='locale'))
        inat.addLayout(
            IntSetting(settings, icon_str='mdi.home-city-outline', setting_attr='preferred_place_id')
        )
        inat.addLayout(ToggleSetting(settings, icon_str='mdi6.cat', setting_attr='casual_observations'))
        self.all_ranks = ToggleSetting(
            settings, icon_str='fa.chevron-circle-up', setting_attr='all_ranks'
        )
        inat.addLayout(self.all_ranks)

        metadata = self.add_group('Metadata', self.settings_layout)
        metadata.addLayout(ToggleSetting(settings, icon_str='fa.language', setting_attr='common_names'))
        metadata.addLayout(
            ToggleSetting(settings, icon_str='ph.files-fill', setting_attr='create_sidecar')
        )
        metadata.addLayout(
            ToggleSetting(settings, icon_str='mdi.file-tree', setting_attr='hierarchical_keywords')
        )

        display = self.add_group('Display', self.settings_layout)
        self.dark_mode = ToggleSetting(
            settings,
            icon_str='mdi.theme-light-dark',
            setting_attr='dark_mode',
        )
        display.addLayout(self.dark_mode)

        # Press escape to save and close window
        shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        shortcut.activated.connect(self.close)

    def closeEvent(self, event):
        """Save settings when closing the window"""
        self.settings.write()
        self.message.emit('Settings saved')
        event.accept()


class SettingLayout(QHBoxLayout):
    """Layout for an icon, description, and input widget for a single setting"""

    def __init__(self, icon_str: str, setting_attr: str):
        super().__init__()
        self.setAlignment(Qt.AlignLeft)
        self.addWidget(IconLabel(icon_str, size=32))

        label_layout = QVBoxLayout()
        label = QLabel(setting_attr.replace('_', ' ').title())
        # TODO: Style with QSS
        font = QFont()
        font.setPixelSize(16)
        font.setBold(True)
        label.setFont(font)
        label_layout.addWidget(label)

        attr_meta = getattr(fields(Settings), setting_attr).metadata
        description = attr_meta.get('doc')
        if description:
            label_layout.addWidget(QLabel(description))
        self.addLayout(label_layout)
        self.addStretch()


class TextSetting(SettingLayout):
    """Text input setting"""

    def __init__(
        self,
        settings: Settings,
        icon_str: str,
        setting_attr: str,
        validator: QValidator = None,
    ):
        super().__init__(icon_str, setting_attr)

        def set_text(text):
            setattr(settings, setting_attr, text)

        widget = QLineEdit()
        widget.setFixedWidth(150)
        widget.setText(str(getattr(settings, setting_attr)))
        widget.textChanged.connect(set_text)
        if validator:
            widget.setValidator(validator)
        self.addWidget(widget)


class IntSetting(TextSetting):
    """Text input setting, integer values only"""

    def __init__(self, settings: Settings, icon_str: str, setting_attr: str):
        super().__init__(settings, icon_str, setting_attr, validator=QIntValidator())


class ToggleSetting(SettingLayout):
    """Boolean setting with toggle switch"""

    clicked = Signal(bool)

    def __init__(self, settings: Settings, icon_str: str, setting_attr: str):
        super().__init__(icon_str, setting_attr)

        def set_state(checked: bool):
            setattr(settings, setting_attr, checked)

        self.switch = ToggleSwitch()
        setting_value = getattr(settings, setting_attr)
        self.switch.setChecked(setting_value)
        self.switch.clicked.connect(set_state)
        self.switch.clicked.connect(lambda checked: self.clicked.emit(checked))
        self.addWidget(self.switch)
