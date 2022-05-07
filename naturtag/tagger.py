""" Combined entry point for both CLI and GUI """
from naturtag.constants import Coordinates
from naturtag.inat_metadata import (
    get_keywords,
    get_observation_coordinates,
    get_observation_dwc_terms,
    get_taxon_dwc_terms,
)
from naturtag.models.meta_metadata import MetaMetadata


def tag_images(
    observation_id: int,
    taxon_id: int,
    common_names: bool = False,
    darwin_core: bool = False,
    hierarchical: bool = False,
    create_xmp_sidecar: bool = False,
    images: list[str] = None,
):
    """
    Get taxonomy tags from an iNaturalist observation or taxon, and write them to local image
    metadata. See :py:func:`~naturtag.cli.tag` for details.
    """
    keywords = get_keywords(
        observation_id=observation_id,
        taxon_id=taxon_id,
        common=common_names,
        hierarchical=hierarchical,
    )

    all_metadata = []
    dwc_metadata = {}
    coordinates = get_observation_coordinates(observation_id) if observation_id else None
    if observation_id and darwin_core:
        dwc_metadata = get_observation_dwc_terms(observation_id)
    elif taxon_id and darwin_core:
        dwc_metadata = get_taxon_dwc_terms(taxon_id)
    for image_path in images:
        all_metadata.append(
            tag_image(image_path, keywords, dwc_metadata, coordinates, create_xmp_sidecar)
        )

    return all_metadata, keywords, dwc_metadata


def tag_image(
    image_path: str,
    keywords: list[str],
    dwc_metadata: dict,
    coordinates: Coordinates,
    create_xmp_sidecar: bool,
) -> MetaMetadata:
    metadata = MetaMetadata(image_path)
    metadata.update(dwc_metadata)
    metadata.update_coordinates(coordinates)
    metadata.update_keywords(keywords)
    metadata.write(create_xmp_sidecar=create_xmp_sidecar)
    return metadata
