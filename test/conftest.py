from pathlib import Path

import prettyprinter

prettyprinter.install_extras(exclude=['django'])

DEMO_IMAGES_DIR = Path(__file__).parent.parent / 'assets' / 'demo_images'
SAMPLE_DATA_DIR = Path(__file__).parent / 'sample_data'
