import json


def json_to_indented_tree(json_data, output_kw_file):
    """
    Convert a JSON-formatted tree into a simplified indented tree format usable as a
    keyword collection
    """
    def write_children(d, f, indent_lvl):
        for k, v in d.items():
            f.write(' ' * indent_lvl + k + '\n')
            write_children(v, f, indent_lvl + 1)

    with open(output_kw_file, 'w') as f:
        write_children(json_data, f, 0)


def write_tree(tree, output_json_file):
    """
    Write keyword tree to both JSON and simple indented format
    """
    print('Writing output')
    with open(output_json_file, 'w') as f:
        json.dump(tree, f, indent=2)
    print(f'Taxonomy tree written to {output_json_file}')

    # TODO: There are safer ways to replace file extensions
    output_kw_file = output_json_file.replace('.json', '.txt')
    json_to_indented_tree(tree, output_kw_file)
    print(f'Taxonomy tree written to {output_kw_file}')


# Alternative version
# import re
# STRIP_JSON_PATTERN = r'\},|: \{|[\{\}"]'
# def json_to_indented_tree(json_file_path, output_kw_file):
#     with open(json_file_path) as src, open(output_kw_file, 'w') as out:
#         for line in src.readlines():
#             line = re.sub(STRIP_JSON_PATTERN, '', line).rstrip()
#             if line.strip():
#                 out.write(line + '\n')


# json_to_indented_tree(
#     'taxonomy_data/ncbi_taxonomy.json',
#     'taxonomy_data/ncbi_taxonomy.txt'
# )
