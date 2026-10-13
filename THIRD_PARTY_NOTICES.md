# Third-party software in Cuánto

The packaged app includes these open-source components. Thank you to their authors.

| Component | License | Source |
|---|---|---|
| Qt 6 / PySide6 | LGPL-3.0 | https://www.qt.io/download-open-source · https://code.qt.io/cgit/pyside/pyside-setup.git |
| Python | PSF License | https://www.python.org |
| certifi | MPL-2.0 | https://github.com/certifi/python-certifi |
| openpyxl (Excel export) | MIT | https://foss.heptapod.net/openpyxl/openpyxl |
| defusedxml | PSF License | https://github.com/tiran/defusedxml |
| keyring (the system keychain) | MIT | https://github.com/jaraco/keyring |
| Inter typeface (the app and the paper) | SIL Open Font License 1.1 | https://github.com/rsms/inter |
| IBM Plex Mono (account codes; unmodified) | SIL Open Font License 1.1 | https://github.com/IBM/plex |
| Icons (redrawn line icons) | ISC (Lucide) | https://lucide.dev |

The fonts' license files are in `cuanto/assets/fonts` (OFL-*.txt). Inter's fixed weights are included as
published; IBM Plex Mono is included exactly as published.
Qt libraries are shipped as separate shared libraries in the app folder and can be replaced.
