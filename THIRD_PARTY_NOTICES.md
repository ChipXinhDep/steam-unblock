# Third-party notices

The released `SteamUnblock.exe` bundles the following components.

| Component | License | Source |
|-----------|---------|--------|
| Python runtime | PSF License | https://www.python.org/ |
| pystray | LGPL-3.0 | https://github.com/moses-palmer/pystray |
| Pillow | MIT-CMU (HPND) | https://github.com/python-pillow/Pillow |
| six (pystray dependency) | MIT | https://github.com/benjaminp/six |
| PyInstaller bootloader | GPL-2.0 with bootloader exception | https://github.com/pyinstaller/pyinstaller |

## pystray (LGPL-3.0)

pystray is used unmodified as a separate library. Under the LGPL you may replace it with
your own modified version: the full source of this app is in this repository, so you can
rebuild the executable against any pystray version with the build command in the README.
The LGPL-3.0 text: https://www.gnu.org/licenses/lgpl-3.0.txt

## PyInstaller

The PyInstaller bootloader is GPL-2.0 with an exception that allows distributing
executables built with it under any license. https://pyinstaller.org/en/stable/license.html
