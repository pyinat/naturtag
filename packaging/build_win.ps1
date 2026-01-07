# Build pyinstaller package prior to creating Windows installer

# Create virtualenv (if needed)
# python3.12 -m venv  $env:USERPROFILE\.virtualenvs\naturtag

# Install uv (if needed)
# Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression

# Sync dependencies and build with pyinstaller
uv sync --no-dev
uv run pyinstaller -y packaging\naturtag.spec

# Launch Actual Installer, then:
#  1. Run 'Build Project' (F9)
#  2. Run installer
#  3. Open Naturtag and test basic features
Invoke-Item packaging\naturtag.aip
