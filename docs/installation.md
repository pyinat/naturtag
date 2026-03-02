# {fa}`download` Installation
Downloads can be found on [GitHub Releases](https://github.com/pyinat/naturtag/releases).
Platform-specific installation instructions are below:

<!-- TODO: portable (.tar.gz) download links & instructions -->

```{warning}
These packages and installers have not yet been thoroughly tested on all platforms.
Please [create a bug report](https://github.com/pyinat/naturtag/issues/new) if you encounter any installation issues!
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

:::{tab-item} Arch
A pacman package is available for Arch Linux and derivatives. Download
{{
    '[naturtag.pkg.tar.zst](https://github.com/pyinat/naturtag/releases/download/{}/naturtag.pkg.tar.zst)'.format(version)
}}
and run:
```
sudo pacman -U naturtag.pkg.tar.zst
```
:::

:::{tab-item} Linux (Other)
For other Linux distributions, a portable AppImage is available. Download
{{
    '[naturtag.AppImage](https://github.com/pyinat/naturtag/releases/download/{}/naturtag.AppImage)'.format(version)
}}
and run:
```
chmod +x naturtag.AppImage
./naturtag.AppImage
```
:::

:::{tab-item} macOS
Download
{{
    '[naturtag.dmg](https://github.com/pyinat/naturtag/releases/download/{}/naturtag.dmg),'.format(version)
}}
double-click the file, and drag to Applications to install.

If you see a Gatekeeper message _"naturtag is damaged and can't be opened"_, run the following command to remove the quarantine flag:
```sh
xattr -dr com.apple.quarantine /Applications/naturtag.app
```
This is required because the app is not signed with a ($100/yr) Apple Developer ID certificate.
:::

:::{tab-item} Windows
A Windows installer is available here:
{{
    '[naturtag-installer.exe](https://github.com/pyinat/naturtag/releases/download/{}/naturtag-installer.exe)'.format(version)
}}

If you see a Microsoft Defender message _"SmartScreen prevented an unrecognized app from starting..."_,
click **More info > Run anyway**. This is required because the app is not signed with a (paid) code signing certificate.
:::

::::


## Python package
You can also use naturtag as a {ref}`plain python library <library>`, if you prefer:
* First, [install python 3.13](https://www.python.org/downloads/) if you don't have it yet.
* It's recommended to install into a [virtual environment](https://docs.python.org/3/library/venv.html).
* Install with `pip`:
    ```
    pip install naturtag
    ```
* Or use [`uv`](https://docs.astral.sh/uv/) to install as a user-level CLI tool (no manual virtualenv required):
    ```
    uv tool install naturtag
    ```

```{warning}
The PyPI package is suitable for using the library and CLI; for the desktop application, it is highly
recommended to use one of the platform-specific builds above.
```
