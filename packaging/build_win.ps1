# Build pyinstaller package prior to creating Windows installer

# Create virtualenv (if needed)
# python3.11 -m venv  $env:USERPROFILE\.virtualenvs\naturtag

# Install poetry (if needed)
# Invoke-WebRequest -Uri https://install.python-poetry.org -OutFile install-poetry.py
# python install-poetry.py --preview
# ~\AppData\Roaming\Python\Scripts\poetry.exe config virtualenvs.create false

# Install dependencies
. ~\.virtualenvs\naturtag\Scripts\activate.ps1
poetry self update
poetry install -v --only main
pip install -U setuptools pyinstaller
pyinstaller -y packaging\naturtag.spec

# Launch Actual Installer, then:
#  1. Run 'Build Project' (F9)
#  2. Run installer
#  3. Open Naturtag and test basic features
Invoke-Item packaging\naturtag.aip
