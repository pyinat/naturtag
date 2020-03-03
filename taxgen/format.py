import json


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


def write_tree(tree, output_base_name):
    """
    Write keyword tree to both JSON and simple indented format
    """
    print('Writing output')
    with open(f'{output_base_name}.json', 'w') as f:
        json.dump(tree, f, indent=2)
    print(f'Taxonomy tree written to {output_base_name}.json')

    json_to_indented_tree(tree, output_base_name)
    print(f'Taxonomy tree written to {output_base_name}.txt')
