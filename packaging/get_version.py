#!/usr/bin/env python
"""Get app version from pyproject.toml"""

import tomllib
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.absolute()

with open(PROJECT_DIR / 'pyproject.toml', 'rb') as f:
    conf = tomllib.load(f)

print(conf['project']['version'])
