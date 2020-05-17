""" Combined entry point for both CLI and GUI """
from naturtag.metadata_writer import get_keyword_metadata, write_metadata
from naturtag.inat_darwincore import get_observation_dwc_terms
from naturtag.inat_keywords import get_keywords


def tag_images(observation_id, taxon_id, common_names, darwin_core, hierarchical, create_xmp, images):
    keywords = get_keywords(
        observation_id=observation_id,
        taxon_id=taxon_id,
        common=common_names,
        hierarchical=hierarchical,
    )
    metadata = get_keyword_metadata(keywords)

    # TODO: Write minimal DwC taxonomy metadata if only a taxon ID is provided
    if observation_id and images and darwin_core:
        metadata.update(get_observation_dwc_terms(observation_id))
    for image in images:
        write_metadata(image, metadata, create_xmp=create_xmp)

    return keywords, metadata
