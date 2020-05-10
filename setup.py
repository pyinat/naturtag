from setuptools import setup, find_packages

setup(
    name='inat-image-tagger',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'Click>=7.0',
        'pyinaturalist',
        # "https://github.com/JWCook/pyinaturalist.git",
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
