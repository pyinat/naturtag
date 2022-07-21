# Build pyinstaller package prior to creating Windows installer

# Create virtualenv
# python -m venv  $env:USERPROFILE\.virtualenvs\naturtag

# Install poetry
# Invoke-WebRequest -Uri https://install.python-poetry.org -OutFile install-poetry.py
# python install-poetry.py --preview
# ~\AppData\Roaming\Python\Scripts\poetry.exe config virtualenvs.create false

# Install dependencies
. ~\.virtualenvs\naturtag\Scripts\activate.ps1
poetry install -v --no-dev
pip install -U setuptools pyinstaller
pyinstaller -y packaging\naturtag.spec

# Launch Actual Installer, then:
#  1. Run 'Build Project' (F9)
#  2. Run installer
#  3. Open Naturtag and test basic features
Invoke-Item packaging\naturtag.aip

# Launch InstallForge
# Invoke-Item packaging\naturtag.ifp
