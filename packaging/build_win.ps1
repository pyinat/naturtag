# Build pyinstaller package and Windows installer
# (for local builds; not used by CI)

# Install uv (if needed)
# Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression

# Sync dependencies and build with pyinstaller
uv sync --no-dev
uv run pyinstaller -y packaging\naturtag.spec

# Build installer with Inno Setup
$version = uv run python packaging\get_version.py
iscc /DAppVersion=$version packaging\naturtag.iss
