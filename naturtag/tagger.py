"""Main entry point for tagging images for both CLI and GUI"""
from naturtag.inat_metadata import get_inat_metadata
from naturtag.models.meta_metadata import MetaMetadata


def tag_images(
    observation_id: int,
    taxon_id: int,
    common_names: bool = False,
    darwin_core: bool = False,
    hierarchical: bool = False,
    create_sidecar: bool = False,
    images: list[str] = None,
) -> list[MetaMetadata]:
    """
    Get taxonomy tags from an iNaturalist observation or taxon, and write them to local image
    metadata. See :py:func:`~naturtag.cli.tag` for details.
    """
    inat_metadata = get_inat_metadata(
        observation_id=observation_id,
        taxon_id=taxon_id,
        common_names=common_names,
        darwin_core=darwin_core,
        hierarchical=hierarchical,
    )

    if not images:
        return [inat_metadata]
    return [tag_image(image_path, inat_metadata, create_sidecar) for image_path in images]


def tag_image(
    image_path: str, inat_metadata: MetaMetadata, create_sidecar: bool = False
) -> MetaMetadata:
    img_metadata = MetaMetadata(image_path).merge(inat_metadata)
    img_metadata.write(create_sidecar=create_sidecar)
    return img_metadata
