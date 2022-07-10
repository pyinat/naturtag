from logging import getLogger

from attr import fields
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIntValidator, QValidator
from PySide6.QtWidgets import QComboBox, QLabel, QLineEdit, QSizePolicy

from naturtag.settings import Settings
from naturtag.widgets import IconLabel, StylableWidget, ToggleSwitch
from naturtag.widgets.layouts import HorizontalLayout, VerticalLayout

logger = getLogger(__name__)


class SettingsMenu(StylableWidget):
    """Application settings menu, with input widgets connected to values in settings file"""

    on_message = Signal(str)  #: Forward a message to status bar

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.settings_layout = VerticalLayout(self)

        inat = self.add_group('iNaturalist', self.settings_layout)
        inat.addLayout(TextSetting(settings, icon_str='fa.user', setting_attr='username'))
        inat.addLayout(TextSetting(settings, icon_str='fa.globe', setting_attr='locale'))
        inat.addLayout(
            IntSetting(
                settings, icon_str='mdi.home-city-outline', setting_attr='preferred_place_id'
            )
        )
        inat.addLayout(
            ToggleSetting(settings, icon_str='mdi6.cat', setting_attr='casual_observations')
        )
        self.all_ranks = ToggleSetting(
            settings, icon_str='fa.chevron-circle-up', setting_attr='all_ranks'
        )
        inat.addLayout(self.all_ranks)

        metadata = self.add_group('Metadata', self.settings_layout)
        metadata.addLayout(
            ToggleSetting(settings, icon_str='fa.language', setting_attr='common_names')
        )
        metadata.addLayout(
            ToggleSetting(settings, icon_str='mdi.file-tree', setting_attr='hierarchical')
        )
        metadata.addLayout(
            ToggleSetting(settings, icon_str='fa5s.file-code', setting_attr='sidecar')
        )
        metadata.addLayout(
            ToggleSetting(
                settings, icon_str='fa5s.file-alt', setting_attr='exif', setting_title='EXIF'
            )
        )
        metadata.addLayout(
            ToggleSetting(
                settings, icon_str='fa5s.file-alt', setting_attr='iptc', setting_title='IPTC'
            )
        )
        metadata.addLayout(
            ToggleSetting(
                settings, icon_str='fa5s.file-alt', setting_attr='xmp', setting_title='XMP'
            )
        )

        display = self.add_group('Display', self.settings_layout)
        self.dark_mode = ToggleSetting(
            settings,
            icon_str='mdi.theme-light-dark',
            setting_attr='dark_mode',
        )
        display.addLayout(self.dark_mode)

        debug = self.add_group('Debug', self.settings_layout)
        self.show_logs = ToggleSetting(
            settings,
            icon_str='fa.file-text-o',
            setting_attr='show_logs',
        )
        debug.addLayout(self.show_logs)
        self.log_level = ChoiceSetting(
            settings, icon_str='fa.thermometer-2', setting_attr='log_level'
        )
        debug.addLayout(self.log_level)

        # Press escape to save and close window
        self.add_shortcut(Qt.Key_Escape, self.close)

    def add_group(self, *args, **kwargs):
        group = super().add_group(*args, **kwargs)
        group.box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        return group

    def closeEvent(self, event):
        """Save settings when closing the window"""
        self.settings.write()
        self.on_message.emit('Settings saved')
        event.accept()


class SettingContainer(HorizontalLayout):
    """Layout for an icon, description, and input widget for a single setting"""

    def __init__(self, icon_str: str, setting_attr: str, setting_title: str = None):
        super().__init__()
        self.setAlignment(Qt.AlignLeft)
        self.addWidget(IconLabel(icon_str, size=32))

        title_str = setting_title or setting_attr.replace('_', ' ').title()
        title = QLabel(title_str)
        title.setObjectName('h3')
        title_layout = VerticalLayout()
        title_layout.addWidget(title)

        attr_meta = getattr(fields(Settings), setting_attr).metadata
        description = attr_meta.get('doc')
        if description:
            title_layout.addWidget(QLabel(description))
        self.addLayout(title_layout)
        self.addStretch()


class ChoiceSetting(SettingContainer):
    def __init__(
        self,
        settings: Settings,
        icon_str: str,
        setting_attr: str,
        setting_title: str = None,
    ):
        super().__init__(icon_str, setting_attr, setting_title)

        def set_text(text):
            setattr(settings, setting_attr, text)

        widget = QComboBox()
        widget.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR'])
        widget.setCurrentText(str(getattr(settings, setting_attr)))
        widget.currentTextChanged.connect(set_text)
        self.addWidget(widget)


class TextSetting(SettingContainer):
    """Text input setting"""

    def __init__(
        self,
        settings: Settings,
        icon_str: str,
        setting_attr: str,
        setting_title: str = None,
        validator: QValidator = None,
    ):
        super().__init__(icon_str, setting_attr, setting_title)

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


class ToggleSetting(SettingContainer):
    """Boolean setting with toggle switch"""

    on_click = Signal(bool)

    def __init__(
        self,
        settings: Settings,
        icon_str: str,
        setting_attr: str,
        setting_title: str = None,
    ):
        super().__init__(icon_str, setting_attr, setting_title)

        def set_state(checked: bool):
            setattr(settings, setting_attr, checked)

        self.switch = ToggleSwitch()
        setting_value = getattr(settings, setting_attr)
        self.switch.setChecked(setting_value)
        self.switch.clicked.connect(set_state)
        self.switch.clicked.connect(lambda checked: self.on_click.emit(checked))
        self.addWidget(self.switch)
