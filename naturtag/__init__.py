from os import getenv

# Set the pre-release version number, if set by CI job
__version__ = '0.6.1'
__version__ += getenv('PRE_RELEASE_SUFFIX', '')
