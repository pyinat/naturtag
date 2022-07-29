# {fa}`download` Installation
Package downloads can be found on [GitHub Releases](https://github.com/pyinat/naturtag/releases).
Platform-specific installation instructions are below:

<!-- TODO: portable (.tar.gz) download links & instructions -->

```{warning}
These packages and installers are brand new, and not yet throughly tested on all platforms.
Please [create a bug report](https://github.com/pyinat/naturtag/issues/new) if you find any issues!
```

::::{tab-set}

:::{tab-item} Debian
A DEB package is available for Debian, Ubuntu, and derivatives. Download
{{
    '[naturtag.deb](https://github.com/pyinat/naturtag/releases/download/{}/naturtag.deb)'.format(version)
}}
and run:
```
sudo dpkg -i naturtag.deb
```
:::

:::{tab-item} Fedora
An RPM package is available for Fedora, RHEL, and derivatives. Download
{{
    '[naturtag.rpm](https://github.com/pyinat/naturtag/releases/download/{}/naturtag.rpm)'.format(version)
}}
and run:
```
sudo rpm -i naturtag.rpm
```
:::

:::{tab-item} Linux (Other)
For other Linux distributions, a [Snap](https://snapcraft.io/docs/installing-snapd)
package is available. Download
{{
    '[naturtag.snap](https://github.com/pyinat/naturtag/releases/download/{}/naturtag.snap)'.format(version)
}}
and run:
```
sudo snap install naturtag.snap
```
:::

:::{tab-item} macOS
Download
{{
    '[naturtag.dmg](https://github.com/pyinat/naturtag/releases/download/{}/naturtag.dmg),'.format(version)
}}
double-click the file, and drag to Applications to install.
:::

:::{tab-item} Windows
A Windows installer is available here:
{{
    '[naturtag-installer.exe](https://github.com/pyinat/naturtag/releases/download/{}/naturtag-installer.exe)'.format(version)
}}
:::

::::


## Python package
You can also install naturtag as a regular python package, if you prefer:
* First, [install python 3.10](https://www.python.org/downloads/) if you don't have it yet.
* It's recommended to install into a [virtual environment](https://docs.python.org/3/library/venv.html).
* Install with `pip`:
```
pip install naturtag
```
