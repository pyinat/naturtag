from setuptools import setup, find_packages

setup(
    name='taxon-keyword-gen',
    version='0.0.1',
    packages=find_packages(),
    install_requires=[
        'Click>=7.0',
        'pandas',
        'progress',
        'pyinaturalist',
        # "https://github.com/JWCook/pyinaturalist.git",
        'pyexiv2',
        'requests',
        'requests-ftp',
        'xmltodict',
    ],
    entry_points={
        'console_scripts': [
            'taxgen=taxgen.cli:main',
        ],
    }
)
