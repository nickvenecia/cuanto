"""Safe HTTPS for the update check: certificate checks always on (certifi's list when bundled)."""

from __future__ import annotations

import os
import ssl


def ssl_context() -> ssl.SSLContext:
    if os.environ.get("SSL_CERT_FILE"):  # respect a custom CA (company proxies)
        return ssl.create_default_context()
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()
