"""Reaching the web safely: the one way anything in Cuánto follows a link (a vendor's site, live exchange rates).

A link can come from a shared file or another tool's export, so it's treated as untrusted:
- only https (http is upgraded); never file://, smb://, ftp:// or anything else
- only public internet addresses: never this computer, your home network or the router (checked again on
  every redirect, so a page can't bounce us somewhere private), and the connection goes to the checked address
- a size cap on what's downloaded and on what it unpacks to, and a timeout
Every failure is an OSError with a plain message.
"""

from __future__ import annotations

import http.client
import ipaddress
import json
import socket
import urllib.request
import zlib
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from cuanto import __version__
from cuanto.core.log import get_logger
from cuanto.core.net import ssl_context

log = get_logger(__name__)

TIMEOUT_S = 15
MAX_BYTES = 6_000_000  # downloaded, and again after unpacking
MAX_REDIRECTS = 5
HEADERS = {
    "User-Agent": f"Cuanto/{__version__}",  # says what it is: Cuánto never passes itself off as a browser
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}


class Blocked(OSError):
    """A link Cuánto won't open or download."""


class Refused(OSError):
    """A site that turned Cuánto away."""


def site_name(url: str) -> str:
    """What to call a site in a message: its address without www."""
    return (urlparse(url if "://" in url else "https://" + url).hostname or "").lower().removeprefix("www.")


# ---------------------------------------------------------------- links
def web_link(text: str) -> str:
    """A link as typed or imported -> "https://…", or "" if it isn't a plain web link.
    "example.com/rates" gets https://; "file://…", "javascript:…", "smb://…", a link with a
    name@ in front of its address, or a malformed one give ""."""
    s = (text or "").strip()
    if not s or any(c.isspace() for c in s) or len(s) > 2048:
        return ""
    if "://" not in s:
        if ":" in s.split("/", 1)[0] and not s.split("/", 1)[0].rsplit(":", 1)[-1].isdigit():
            return ""  # mailto:, javascript:, …
        s = "https://" + s
    try:
        u = urlparse(s)
        host, _port = u.hostname, u.port  # .port raises for ":abc" or ":99999"
    except ValueError:
        return ""
    if u.scheme.lower() not in ("http", "https") or not host or "." not in host:
        return ""
    if "@" in u.netloc or "%" in u.netloc:  # "https://example.com@elsewhere.net" really goes to elsewhere.net
        return ""
    return s


def is_web_link(text: str) -> bool:
    return bool(web_link(text))


_NAT64 = ipaddress.ip_network("64:ff9b::/96")
_V4_COMPAT = ipaddress.ip_network("::/96")


def _private(ip) -> bool:
    """True for anything that isn't a plain public address, including IPv6 forms that carry a private
    IPv4 address inside them."""
    if not ip.is_global or ip.is_multicast:
        return True
    if ip.version == 6:
        inner = ip.ipv4_mapped or ip.sixtofour or (ip.teredo[1] if ip.teredo else None)
        if ip in _NAT64 or ip in _V4_COMPAT:
            inner = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
        if inner is not None and _private(inner):
            return True
    return False


def check_public(host: str) -> str:
    """The public address to connect to for `host`. Raises Blocked if any address it resolves to isn't
    on the public internet (so a name can't point at this computer or your network)."""
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError) as e:
        raise OSError(f"Couldn't find {host}.") from e
    addresses = [ipaddress.ip_address(info[4][0].split("%", 1)[0]) for info in infos]
    if not addresses or any(_private(ip) for ip in addresses):
        raise Blocked(f"{host} isn't on the public internet, so Cuánto won't open it.")
    return str(addresses[0])


def _https(url: str) -> str:
    link = web_link(url)
    if not link:
        raise Blocked("That isn't a web link.")
    if urlparse(link).scheme.lower() == "http":
        link = "https://" + link.split("://", 1)[1]
    return link


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # redirects are never followed with an API key on board


_opener = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=ssl_context()))
_direct = urllib.request.build_opener(  # for this computer: never through a proxy
    _NoRedirect(), urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ssl_context())
)


def open_no_redirect(req: urllib.request.Request, timeout: float, direct: bool = False):
    """Open `req` without following redirects (an API key in its headers must never be sent on to
    wherever a redirect points). A redirect comes back as an HTTPError. `direct`: skip any proxy (a model
    on this computer: its key must not travel through a proxy in plain http)."""
    return (_direct if direct else _opener).open(req, timeout=timeout)


@dataclass
class Page:
    url: str  # where it ended up
    html: str
    content_type: str = ""


def _unpack(raw: bytes, encoding: str, limit: int) -> bytes:
    if encoding not in ("gzip", "deflate", "x-gzip"):
        return raw
    for wbits in (47, -15):  # gzip or zlib (auto), then raw deflate
        try:
            d = zlib.decompressobj(wbits=wbits)
            out = d.decompress(raw, limit)  # never more than `limit`, however well it packs
            return out
        except zlib.error:
            continue
    raise OSError("The page came back garbled.")


class _PinnedHTTPS(http.client.HTTPSConnection):
    """HTTPS to the exact address that was checked (asking DNS again could give a different, private
    one), with the certificate still checked against the name."""

    def __init__(self, host: str, ip: str, port: int, timeout: float):
        super().__init__(host, port, timeout=timeout, context=ssl_context())
        self._ip = ip

    def connect(self):
        sock = socket.create_connection((self._ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


@dataclass
class _Reply:
    status: int
    headers: object  # an http.client.HTTPMessage
    body: bytes


def _get(url: str, ip: str, timeout: float, max_bytes: int) -> _Reply:
    """One GET to the checked address (no redirects followed)."""
    u = urlparse(url)
    path = (u.path or "/") + (f"?{u.query}" if u.query else "")
    conn = _PinnedHTTPS(u.hostname or "", ip, u.port or 443, timeout)
    try:
        conn.request("GET", path, headers=HEADERS)
        resp = conn.getresponse()
        return _Reply(resp.status, resp.headers, resp.read(max_bytes))
    finally:
        conn.close()


def _fetch(url: str, max_bytes: int, timeout: float) -> tuple[str, _Reply, bytes]:
    """GET a public https link, following redirects (each one checked). (where it ended up, reply, body)."""
    url = _https(url)
    for _hop in range(MAX_REDIRECTS + 1):
        host = urlparse(url).hostname or ""
        site = site_name(url)
        ip = check_public(host)
        try:
            r = _get(url, ip, timeout, max_bytes)
        except OSError as e:
            log.info("fetch failed for %s: %s", host, type(e).__name__)
            raise OSError(f"Couldn't reach {site}.") from e
        except Exception as e:  # http.client raises a few kinds of its own
            log.info("fetch failed for %s: %s", host, type(e).__name__)
            raise OSError(f"Couldn't reach {site}.") from e
        if r.status in (301, 302, 303, 307, 308) and r.headers.get("Location"):
            try:
                url = _https(urljoin(url, r.headers["Location"]))
            except ValueError as e:
                raise Blocked("That page redirects to a broken link.") from e
            continue
        if r.status >= 400:
            log.info("fetch failed for %s: HTTP %s", host, r.status)
            if r.status in (401, 403):
                raise Refused(f"{site} turned Cuánto away.")
            if r.status in (429, 503):
                raise Refused(f"{site} didn't let Cuánto read it.")
            raise OSError(f"{site} said no (error {r.status}).")
        body = _unpack(r.body, (r.headers.get("Content-Encoding") or "").lower(), max_bytes)
        return url, r, body
    raise OSError("That link redirects too many times.")


def fetch(url: str, max_bytes: int = MAX_BYTES, timeout: float = TIMEOUT_S) -> Page:
    """Download a public web page over https. Raises OSError (Blocked for links it won't follow)."""
    url, r, body = _fetch(url, max_bytes, timeout)
    charset = r.headers.get_content_charset() or "utf-8"
    try:
        text = body.decode(charset, errors="replace")
    except (LookupError, ValueError):  # a charset Python doesn't know, or can't use here
        text = body.decode("utf-8", errors="replace")
    return Page(url, text, r.headers.get_content_type() or "")


def fetch_json(url: str, max_bytes: int = 1_000_000, timeout: float = TIMEOUT_S):
    """A public https link's JSON (an exchange-rate service, say). Raises OSError if it isn't JSON."""
    page = fetch(url, max_bytes, timeout)
    try:
        return json.loads(page.html)
    except (ValueError, RecursionError) as e:
        raise OSError(f"{site_name(url)} didn't send what Cuánto expected.") from e
