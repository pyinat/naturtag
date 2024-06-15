#!/usr/bin/env python
"""Get app version from poetry config"""

from pathlib import Path

import tomlkit

PROJECT_DIR = Path(__file__).parent.parent.absolute()

with open(PROJECT_DIR / 'pyproject.toml', 'rb') as f:
    conf = tomlkit.loads(f.read())

print(conf['tool']['poetry']['version'])
