""" Data classes with utilities for managing specific resources """
# flake8: noqa: F401

from pyinaturalist.models import Observation

from naturtag.metadata.image_metadata import ImageMetadata
from naturtag.metadata.inat_metadata import get_inat_metadata, tag_image, tag_images
from naturtag.metadata.keyword_metadata import HIER_KEYWORD_TAGS, KEYWORD_TAGS, KeywordMetadata
from naturtag.metadata.meta_metadata import MetaMetadata
