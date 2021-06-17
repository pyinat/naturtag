# TODO: This screen is pretty ugly. Ideally this would be a collection of DataTables.
from typing import Any, Dict, List

from kivy.metrics import dp
from kivymd.uix.datatables import MDDataTable

from naturtag.controllers import Controller
from naturtag.models import MetaMetadata


class MetadataViewController(Controller):
    """Controller class to manage image metadata screen"""

    def __init__(self, screen, **kwargs):
        super().__init__(screen)
        self.combined_tab = screen.combined_tab
        self.exif_tab = screen.exif_tab
        self.iptc_tab = screen.iptc_tab
        self.xmp_tab = screen.xmp_tab
        self.keywords_tab = screen.keywords_tab

    # TODO: Display hierarchical keywords (metadata.keyword_meta.hier_keyword_tree_str)
    def select_metadata(self, metadata: MetaMetadata):
        self.combined_tab.clear_widgets()
        self.combined_tab.add_widget(self.get_metadata_table(metadata.filtered_combined))

        self.keywords_tab.clear_widgets()
        self.keywords_tab.add_widget(self.get_keyword_table(metadata.keyword_meta.flat_keywords))

        self.exif_tab.clear_widgets()
        self.exif_tab.add_widget(self.get_metadata_table(metadata.filtered_exif))

        self.iptc_tab.clear_widgets()
        self.iptc_tab.add_widget(self.get_metadata_table(metadata.iptc))

        self.xmp_tab.clear_widgets()
        self.xmp_tab.add_widget(self.get_metadata_table(metadata.xmp))

    @staticmethod
    def get_metadata_table(metadata_dict: Dict[str, Any]) -> MDDataTable:
        return MDDataTable(
            column_data=[("Tag", dp(50)), ("Value", dp(350))],
            use_pagination=True,
            # TODO: Remove this workaround when kivymd 0.104.2 is released
            rows_num=min(25, len(metadata_dict)),
            row_data=[(k, v) for k, v in metadata_dict.items()],
        )

    @staticmethod
    def get_keyword_table(keyword_list: List[str]) -> MDDataTable:
        return MDDataTable(
            column_data=[("Keyword", dp(400))],
            use_pagination=True,
            # TODO: Remove this workaround when kivymd 0.104.2 is released
            rows_num=min(25, len(keyword_list)),
            row_data=[(k,) for k in keyword_list],
        )
