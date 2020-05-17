""" Combined entry point for both CLI and GUI """
from naturtag.image_metadata import get_keyword_metadata, write_metadata
from naturtag.inat_darwincore import get_observation_dwc_terms
from naturtag.inat_keywords import get_keywords


# TODO: Option to include Darwin Core metadata or not
def tag_images(observation_id, taxon_id, common_names, hierarchical, create_xmp, images):
    keywords = get_keywords(
        observation_id=observation_id,
        taxon_id=taxon_id,
        common=common_names,
        hierarchical=hierarchical,
    )
    metadata = get_keyword_metadata(keywords)

    if observation_id and images:
        metadata.update(get_observation_dwc_terms(observation_id))
    for image in images:
        write_metadata(image, metadata, create_xmp=create_xmp)

    return keywords, metadata
