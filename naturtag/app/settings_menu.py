from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator, QKeySequence, QShortcut, QValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from naturtag.settings import Settings


# TODO: Make this less ugly
# TODO: Put setting descriptions in attrs metadata in Settings class
class SettingsMenu(QWidget):
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.layout = QVBoxLayout(self)

        self.add_section(
            'iNaturalist',
            self.get_text_setting('username', 'Your iNaturalist username'),
            self.get_text_setting('locale', 'Locale preference for species common names'),
            self.get_int_setting(
                'preferred_place_id', 'Place preference for regional species common names'
            ),
            self.get_bool_setting('casual_observations', 'Include casual observations'),
        )

        self.add_section(
            'Metadata',
            self.get_bool_setting('common_names', 'Include common names in taxonomy keywords'),
            self.get_bool_setting(
                'create_sidecar', "Create XMP sidecar files if they don't already exist"
            ),
            self.get_bool_setting(
                'darwin_core', 'Convert species/observation metadata into XMP Darwin Core metadata'
            ),
            self.get_bool_setting(
                'hierarchical_keywords', 'Generate pipe-delimited hierarchical keywords'
            ),
        )

        # Press escape to close window
        shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        shortcut.activated.connect(self.close)

    def closeEvent(self, event):
        """Save settings when closing the window"""
        self.settings.write()
        event.accept()

    def add_section(self, name: str, *items: list[QLayout]):
        """Add a section containing a group of related settings"""
        section_layout = QVBoxLayout()
        group_box = QGroupBox(name)
        group_box.setLayout(section_layout)
        self.layout.addWidget(group_box)

        for item in items:
            section_layout.addLayout(item)
        return section_layout

    def get_int_setting(self, setting_attr: str, description: str):
        """Get a widget and label for an integer setting"""
        return self.get_text_setting(setting_attr, description, QIntValidator())

    def get_text_setting(
        self, setting_attr: str, description: str, validator: QValidator = None
    ) -> QLayout:
        """Get a widget and label for a text setting"""
        item_layout = QHBoxLayout()
        item_layout.addWidget(QLabel(description))
        item_layout.addWidget(self._get_line_edit(setting_attr, validator))
        item_layout.setAlignment(Qt.AlignLeft)
        return item_layout

    def get_bool_setting(self, setting_attr: str, description: str) -> QLayout:
        """Get a widget and label for a boolean setting"""
        item_layout = QHBoxLayout()
        item_layout.addWidget(self._get_checkbox(setting_attr))
        item_layout.addWidget(QLabel(description))
        item_layout.setAlignment(Qt.AlignLeft)
        return item_layout

    def _get_line_edit(self, setting_attr: str, validator: QValidator = None) -> QLineEdit:
        widget = QLineEdit()
        widget.setText(str(getattr(self.settings, setting_attr)))
        if validator:
            widget.setValidator(validator)

        def set_text(text):
            setattr(self.settings, setting_attr, text)

        widget.textChanged.connect(set_text)
        return widget

    def _get_checkbox(self, setting_attr: str) -> QCheckBox:
        widget = QCheckBox()
        setting_value = getattr(self.settings, setting_attr)
        widget.setCheckState(Qt.Checked if setting_value else Qt.Unchecked)

        def set_state(state):
            setattr(self.settings, setting_attr, state == Qt.Checked)

        widget.stateChanged.connect(set_state)
        return widget
