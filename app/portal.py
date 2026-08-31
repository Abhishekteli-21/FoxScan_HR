"""TEMPORARY: server-side reader for the HROne employee help portal.

The portal is unreachable from the sandbox this project is developed in, but a
deployed instance can reach it, so this endpoint lets the knowledge base be built
from the running app. It is deliberately locked to one host, read-only, and sends
no credentials — and it should be deleted once knowledge/hrone_howto.md is filled.
"""

from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

ALLOWED_HOST = "employee-help.hrone.cloud"
BASE = f"https://{ALLOWED_HOST}"
SKIP_TAGS = {"script", "style", "noscript", "svg"}


class Reader(HTMLParser):
    """Collect visible text, same-host links, and image alt/src for a page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []
        self.links: list[str] = []
        self.images = 0
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in SKIP_TAGS:
            self._skip += 1
        elif tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        elif tag == "img":
            self.images += 1
            if attrs.get("alt"):
                self.chunks.append(f"[image: {attrs['alt']}]")
        elif tag in ("br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4"):
            self.chunks.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.chunks.append(data.strip())

    def text(self) -> str:
        out = " ".join(self.chunks)
        while "\n " in out or "  " in out or "\n\n\n" in out:
            out = out.replace("\n ", "\n").replace("  ", " ").replace("\n\n\n", "\n\n")
        return out.strip()


def read(path: str) -> dict:
    """Fetch one page of the help portal and return its text plus its links."""
    url = urljoin(BASE, path)
    if urlparse(url).hostname != ALLOWED_HOST:
        return {"error": f"only {ALLOWED_HOST} may be read", "url": url}
    try:
        with httpx.Client(timeout=25, follow_redirects=True) as client:
            resp = client.get(
                url, headers={"User-Agent": "UrbanRoof-HR-KB-builder/1.0"}
            )
    except Exception as exc:  # network/DNS/TLS problems shouldn't 500 the app
        return {"error": str(exc), "url": url}

    body = resp.text
    if "xml" in resp.headers.get("content-type", "") or body.lstrip().startswith(
        "<?xml"
    ):
        return {"url": url, "status": resp.status_code, "xml": body[:60000]}

    reader = Reader()
    reader.feed(body)
    links = []
    for href in reader.links:
        full = urljoin(url, href)
        if urlparse(full).hostname == ALLOWED_HOST and full not in links:
            links.append(full.split("#")[0])
    return {
        "url": url,
        "status": resp.status_code,
        "images": reader.images,
        "text": reader.text()[:60000],
        "links": links[:200],
    }
