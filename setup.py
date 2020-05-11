from setuptools import setup, find_packages

setup(
    name='inat-image-tagger',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'Click>=7.0',
        'click-help-colors',
        # 'pyinaturalist',  # TODO: Submit PR(s) for WIP pyinaturalist changes
        "git+https://github.com/JWCook/pyinaturalist.git@dev",
        'pyexiv2',
        'xmltodict',
    ],
    entry_points={
        'console_scripts': [
            'naturtag=naturtag.cli:main',
            'nt=naturtag.cli:main',
        ],
    }
)
