from logging import getLogger

from attr import fields
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIntValidator, QValidator
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from naturtag.controllers import BaseController
from naturtag.settings import Settings
from naturtag.widgets import FAIcon, HorizontalLayout, ToggleSwitch, VerticalLayout

logger = getLogger(__name__)


class SettingsMenu(BaseController):
    """Application settings menu, with input widgets connected to values in settings file"""

    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.settings = settings
        self.settings_layout = VerticalLayout(self)

        # iNaturalist settings
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

        # Metadata settings
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

        # User data settings
        user_data = self.add_group('User Data', self.settings_layout)
        use_last_dir = ToggleSetting(
            settings,
            icon_str='mdi.folder-clock-outline',
            setting_attr='use_last_dir',
            setting_title='Use last directory',
        )
        user_data.addLayout(use_last_dir)
        self.default_image_dir = PathSetting(
            settings,
            icon_str='fa5.images',
            setting_attr='default_image_dir',
            setting_title='Default image directory',
            dialog_parent=self,
        )
        user_data.addLayout(self.default_image_dir)

        # Disable default_image_dir option when use_last_dir is enabled
        self.default_image_dir.setEnabled(not settings.use_last_dir)
        use_last_dir.on_click.connect(
            lambda checked: self.default_image_dir.setEnabled(not checked)
        )

        # Display settings
        display = self.add_group('Display', self.settings_layout)
        self.dark_mode = ToggleSetting(
            settings,
            icon_str='mdi.theme-light-dark',
            setting_attr='dark_mode',
        )
        display.addLayout(self.dark_mode)

        # Debug settings
        debug = self.add_group('Debug', self.settings_layout)
        self.show_logs = ToggleSetting(
            settings,
            icon_str='fa.file-text-o',
            setting_attr='show_logs',
        )
        debug.addLayout(self.show_logs)
        self.log_level = ChoiceSetting(
            settings,
            icon_str='fa.thermometer-2',
            setting_attr='log_level',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
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
        self.addWidget(FAIcon(icon_str, size=32))

        title_str = setting_title or setting_attr.replace('_', ' ').title()
        title = QLabel(title_str)
        title.setObjectName('h3')
        self.title_layout = VerticalLayout()
        self.title_layout.addWidget(title)

        attr_meta = getattr(fields(Settings), setting_attr).metadata  # type: ignore  # false positive
        description = attr_meta.get('doc')
        if description:
            self.title_layout.addWidget(QLabel(description))
        self.addLayout(self.title_layout)
        self.addStretch()


class ChoiceSetting(SettingContainer):
    def __init__(
        self,
        settings: Settings,
        icon_str: str,
        setting_attr: str,
        setting_title: str = None,
        choices: list = None,
    ):
        super().__init__(icon_str, setting_attr, setting_title)

        def set_text(text):
            setattr(settings, setting_attr, text)

        widget = QComboBox()
        widget.addItems(choices or [])
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

        text_box = QLineEdit()
        text_box.setFixedWidth(150)
        text_box.setText(str(getattr(settings, setting_attr)))
        text_box.textChanged.connect(set_text)
        if validator:
            text_box.setValidator(validator)
        self.addWidget(text_box)


class PathSetting(SettingContainer):
    def __init__(
        self,
        settings: Settings,
        icon_str: str,
        setting_attr: str,
        setting_title: str = None,
        dialog_parent: QWidget = None,
    ):
        super().__init__(icon_str, setting_attr, setting_title)
        self.settings = settings
        self.setting_attr = setting_attr
        self.dialog_parent = dialog_parent
        path_layout = HorizontalLayout()
        self.title_layout.addLayout(path_layout)

        self.text_box = QLineEdit()
        self.text_box.setFixedWidth(450)
        self.text_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.text_box.setText(str(getattr(settings, setting_attr)))
        self.text_box.textChanged.connect(self.set_text)
        path_layout.addWidget(self.text_box)

        self.browse_button = QPushButton('Browse...')
        self.browse_button.clicked.connect(self.browse)
        path_layout.addWidget(self.browse_button)

    def set_text(self, text):
        setattr(self.settings, self.setting_attr, str(text))

    def setEnabled(self, enabled: bool):
        self.text_box.setEnabled(enabled)
        self.browse_button.setEnabled(enabled)
        super().setEnabled(enabled)

    def browse(self):
        """Browse for a directory"""
        if path := QFileDialog.getExistingDirectory(
            self.dialog_parent,
            'Select directory',
            str(getattr(self.settings, self.setting_attr)),
        ):
            self.text_box.setText(path)


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
