from pathlib import Path

import prettyprinter

prettyprinter.install_extras(exclude=['django'])

SAMPLE_DATA_DIR = Path(__file__).parent.parent / 'assets' / 'demo_images'
