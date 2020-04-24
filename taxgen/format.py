import json
from logging import getLogger
from os import makedirs
from os.path import join

logger = getLogger(__name__)


def json_to_indented_tree(json_data, output_base_name):
    """
    Convert a JSON-formatted tree into a simplified indented tree format usable as a
    keyword collection
    """
    def write_children(d, f, indent_lvl):
        for k, v in d.items():
            f.write(' ' * indent_lvl + k + '\n')
            write_children(v, f, indent_lvl + 1)

    with open(f'{output_base_name}.txt', 'w') as f:
        write_children(json_data, f, 0)


def write_tree(tree, output_dir, base_filename):
    """
    Write keyword tree to both JSON and simple indented format
    """
    logger.info(f'Writing output to  {output_dir}')
    makedirs(output_dir, exist_ok=True)
    output_base_path = join(output_dir, base_filename)

    with open(f'{output_base_path}.json', 'w') as f:
        json.dump(tree, f, indent=2)
    logger.info(f'Taxonomy tree written to {output_base_path}.json')

    json_to_indented_tree(tree, output_base_path)
    logger.info(f'Taxonomy tree written to {output_base_path}.txt')
