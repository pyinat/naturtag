# Build pyinstaller package prior to creating Windows installer

# Setup virtualenv
# python -m venv  $env:USERPROFILE\.virtualenvs\naturtag

. ~\.virtualenvs\naturtag\Scripts\activate.ps1
pip install -U poetry
poetry install -v --no-dev
pip install -U setuptools
pip install -U pyinstaller
pyinstaller -y packaging\naturtag.spec

# Launch Actual Installer, then:
#  1. Run 'Build Project' (F9)
#  2. Run installer
#  3. Open Naturtag and test basic features
Invoke-Item packaging\naturtag.aip

# Launch InstallForge
# Invoke-Item packaging\naturtag.ifp
