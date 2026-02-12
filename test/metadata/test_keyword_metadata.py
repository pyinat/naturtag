import pytest

from naturtag.metadata.keyword_metadata import KeywordMetadata, sort_taxonomy_keywords


def test_kv_keywords():
    kw = KeywordMetadata(
        keywords=[
            'taxonomy:kingdom=Animalia',
            'taxonomy:family=Rhagionidae',
            'inat:taxon_id=202860',
            'Animals',
        ]
    )
    assert kw.kv_keywords == {
        'taxonomy:kingdom': 'Animalia',
        'taxonomy:family': 'Rhagionidae',
        'inat:taxon_id': '202860',
    }


def test_kv_keywords__ignores_empty_value():
    """Keywords like 'key=' (empty value) should not be treated as key-value pairs"""
    kw = KeywordMetadata(keywords=['empty_key=', 'valid=value'])
    assert 'empty_key' not in kw.kv_keywords
    assert kw.kv_keywords == {'valid': 'value'}


def test_hier_keywords():
    kw = KeywordMetadata(
        keywords=[
            'Animalia|Arthropoda|Insecta',
            'Animalia|Arthropoda',
            'Animals',
        ]
    )
    # Should include hierarchical keywords plus the inferred root node
    assert 'Animalia|Arthropoda|Insecta' in kw.hier_keywords
    assert 'Animalia|Arthropoda' in kw.hier_keywords
    assert 'Animalia' in kw.hier_keywords  # root node


def test_normal_keywords():
    kw = KeywordMetadata(
        keywords=[
            'taxonomy:kingdom=Animalia',
            'Animalia|Arthropoda',
            'Animals',
            'Insects',
        ]
    )
    assert kw.normal_keywords == ['Animals', 'Insects']


def test_from_metadata():
    kw = KeywordMetadata(
        metadata={
            'Xmp.dc.subject': ['Animals', 'taxonomy:kingdom=Animalia'],
            'Xmp.lr.hierarchicalSubject': ['Animalia|Arthropoda'],
        }
    )
    assert 'Animals' in kw.keywords
    assert kw.kv_keywords == {'taxonomy:kingdom': 'Animalia'}
    assert 'Animalia|Arthropoda' in kw.hier_keywords


def test_from_metadata__strips_quotes():
    """Quoted keywords in metadata should have quotes removed"""
    kw = KeywordMetadata(
        metadata={
            'Xmp.dc.subject': ['"Ornate Snipe Fly"', '"taxonomy:species=Chrysopilus ornatus"'],
        }
    )
    assert 'Ornate Snipe Fly' in kw.keywords
    assert kw.kv_keywords.get('taxonomy:species') == 'Chrysopilus ornatus'


def test_kv_keyword_list():
    kw = KeywordMetadata(keywords=['taxonomy:kingdom=Animalia', 'inat:taxon_id=123'])
    kv_list = kw.kv_keyword_list
    assert 'taxonomy:kingdom=Animalia' in kv_list
    assert 'inat:taxon_id=123' in kv_list


def test_flickr_tags():
    kw = KeywordMetadata(
        keywords=[
            'taxonomy:kingdom=Animalia',
            'Ornate Snipe Fly',
        ]
    )
    flickr = kw.flickr_tags
    # Keywords with spaces should be quoted
    assert '"Ornate Snipe Fly"' in flickr
    assert 'taxonomy:kingdom=Animalia' in flickr


def test_hier_keyword_tree():
    kw = KeywordMetadata(keywords=['A|B|C', 'A|B', 'A|D'])
    tree = kw.hier_keyword_tree
    assert 'A' in tree
    assert 'B' in tree['A']
    assert 'C' in tree['A']['B']
    assert 'D' in tree['A']


def test_hier_keyword_tree_str():
    kw = KeywordMetadata(keywords=['A|B|C', 'A|B', 'A|D'])
    tree_str = kw.hier_keyword_tree_str
    assert 'A\n' in tree_str
    assert ' B\n' in tree_str
    assert '  C\n' in tree_str
    assert ' D\n' in tree_str


def test_tags():
    """tags property should map keywords to all appropriate metadata tag names"""
    kw = KeywordMetadata(
        keywords=[
            'taxonomy:kingdom=Animalia',
            'Animals',
            'Animalia|Arthropoda',
        ]
    )
    tags = kw.tags
    # Normal + kv keywords go to KEYWORD_TAGS
    assert 'Animals' in tags['Xmp.dc.subject']
    assert 'taxonomy:kingdom=Animalia' in tags['Xmp.dc.subject']
    assert 'Animals' in tags['Iptc.Application2.Subject']
    # Hierarchical keywords go to HIER_KEYWORD_TAGS
    assert 'Animalia|Arthropoda' in tags['Xmp.lr.hierarchicalSubject']
    assert 'Animalia|Arthropoda' in tags['Iptc.Application2.Keywords']


@pytest.mark.parametrize(
    'keywords, expected_order',
    [
        (
            ['taxonomy:family=X', 'taxonomy:species=Y', 'taxonomy:kingdom=Z'],
            ['taxonomy:kingdom=Z', 'taxonomy:family=X', 'taxonomy:species=Y'],
        ),
        (
            ['taxonomy:species=A', 'taxonomy:species=B'],
            ['taxonomy:species=A', 'taxonomy:species=B'],
        ),
        (
            ['inat:taxon_id=123', 'taxonomy:order=Diptera'],
            ['taxonomy:order=Diptera', 'inat:taxon_id=123'],
        ),
    ],
)
def test_sort_taxonomy_keywords(keywords, expected_order):
    assert sort_taxonomy_keywords(keywords) == expected_order
