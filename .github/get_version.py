#!/usr/bin/env python
import tomlkit

with open('pyproject.toml', 'rb') as f:
    conf = tomlkit.loads(f.read())

print(conf['tool']['poetry']['version'])
