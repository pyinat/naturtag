from setuptools import setup, find_packages
from naturtag import __version__

setup(
    name='inat-image-tagger',
    version=__version__,
    packages=find_packages(),
    install_requires=[
        'Click>=7.0',
        'click-help-colors',
        # 'pyinaturalist',  # TODO: Submit PR(s) for WIP pyinaturalist changes
        # "git+https://github.com/JWCook/pyinaturalist.git@dev",
        'pyexiv2',
        'xmltodict',
    ],
    extras_require={
        'ui': ['docutils', 'kivy>=1.11', 'kivymd~=0.104.1', 'pygments'],
        'ui-win': ['pypiwin32', 'kivy_deps.sdl2', 'kivy_deps.gstreamer', 'kivy_deps.angle'],
        'dev': ['black', 'kivy_examples', 'pytest']
    },
    # pip install
    entry_points={
        'console_scripts': [
            'naturtag=naturtag.cli:main',
            'nt=naturtag.cli:main',
        ],
    }
)
