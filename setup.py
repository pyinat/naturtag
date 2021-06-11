from itertools import chain
from setuptools import find_packages, setup

from naturtag import __version__

extras_require = {  # noqa
    'app': ['kivy>=2.0.0', 'kivymd~=0.104.1', 'kivy-garden.contextmenu'],
    'build': ['coveralls', 'twine', 'wheel'],
    'dev': [
        'black==21.4b0',
        'flake8',
        'isort',
        'mypy',
        'pre-commit',
        'pytest>=5.0',
        'pytest-cov',
        'kivy_examples',
        'memory_profiler',
        'prettyprinter',
        'Sphinx~=3.2.1',
        'sphinx-rtd-theme',
        'sphinxcontrib-apidoc',
    ],
}
extras_require['all'] = list(chain.from_iterable(extras_require.values()))


setup(
    name='naturtag',
    version=__version__,
    packages=find_packages(),
    install_requires=[
        'appdirs',
        'attrs',
        'Click>=7.0',
        'click-help-colors',
        'pillow>=7.0',
        'pyexiv2>=2.4.0',
        'python-dateutil',
        'pyinaturalist==0.14.0dev374',
        'pyyaml',
        'requests',
        'requests-cache~=0.6.2',
        'rich',
        'xmltodict',
    ],
    extras_require=extras_require,
    entry_points={
        'console_scripts': [
            'naturtag=naturtag.cli:main',
            'nt=naturtag.cli:main',
        ],
        'gui_scripts': [
            'naturtag-app=naturtag.app.app:main',
        ],
    },
)
