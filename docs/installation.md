# Installation
Package downloads can be found on [GitHub Releases](https://github.com/pyinat/naturtag/releases).
Platform-specific installation instructions are below:

<!-- TODO: portable (.tar.gz) download links & instructions -->

```{warning}
These packages and installers are brand new, and not yet throughly tested on all platforms.
Please [create a bug report](https://github.com/pyinat/naturtag/issues/new) if you find any issues.
```

::::{tab-set}

:::{tab-item} Windows
A windows installer is coming soon. Meanwhile, you can download
{{
    '[naturtag-windows.tar.gz](https://github.com/pyinat/naturtag/releases/download/{}/naturtag-windows.tar.gz),'.format(version)
}}
extract it, and run `naturtag.exe`.
:::

:::{tab-item} macOS
Download
{{
    '[naturtag.dmg](https://github.com/pyinat/naturtag/releases/download/{}/naturtag.dmg),'.format(version)
}}
double-click the file, and drag to Applications to install.
:::

::::


## Linux
::::{tab-set}

:::{tab-item} DEB (Debian/Ubuntu and derivatives)
Download
{{
    '[naturtag.deb](https://github.com/pyinat/naturtag/releases/download/{}/naturtag.deb)'.format(version)
}}
and run:
```
sudo dpkg -i naturtag.deb
```
:::

:::{tab-item} RPM (Fedora and derivatives)
Download
{{
    '[naturtag.rpm](https://github.com/pyinat/naturtag/releases/download/{}/naturtag.rpm)'.format(version)
}}
and run:
```
sudo rpm -i naturtag.rpm
```
:::

:::{tab-item} Other linux distros
For other Linux distributions, you can install with [Snap](https://snapcraft.io/docs/installing-snapd).
Download
{{
    '[naturtag.snap](https://github.com/pyinat/naturtag/releases/download/{}/naturtag.snap)'.format(version)
}}
and run:
```
sudo snap install naturtag.snap
```
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
