"""Politely crawl HROne's employee help portal into markdown for the knowledge base.

Run this from a network that can reach employee-help.hrone.cloud (e.g. your office or
home machine — cloud sandboxes may be blocked):

    pip install requests beautifulsoup4
    python scripts/crawl_help_portal.py --out knowledge/hrone_howto_crawled.md

Then review the output, curate the useful articles, and merge them into
knowledge/hrone_howto.md.

Behavior:
- Tries sitemap.xml first; if absent, falls back to breadth-first crawling of
  same-domain links from the homepage.
- Throttles to ~1 request/second and honors a page cap.
- Flags articles whose steps appear to live only in screenshots (little text, many
  images) so you know OCR would be needed for them.
"""

import argparse
import re
import time
import xml.etree.ElementTree as ET
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = "https://employee-help.hrone.cloud"
HEADERS = {"User-Agent": "UrbanRoof-HR-KB-builder/1.0 (internal knowledge base; contact: hr@urbanroof.in)"}
DELAY_SECONDS = 1.0


def get(url: str) -> requests.Response | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        time.sleep(DELAY_SECONDS)
        return resp if resp.status_code == 200 else None
    except requests.RequestException:
        return None


def urls_from_sitemap() -> list[str]:
    for path in ("/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"):
        resp = get(BASE + path)
        if resp is None or b"<" not in resp.content[:100]:
            continue
        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError:
            continue
        locs = [el.text.strip() for el in root.iter() if el.tag.endswith("loc") and el.text]
        if locs:
            print(f"Found sitemap at {path} with {len(locs)} URLs")
            return locs
    return []


def crawl_links(max_pages: int) -> list[str]:
    """Fallback: BFS over same-domain links starting at the homepage."""
    seen, order = set(), []
    queue = deque([BASE + "/"])
    while queue and len(order) < max_pages:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        resp = get(url)
        if resp is None or "text/html" not in resp.headers.get("content-type", ""):
            continue
        order.append(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            nxt = urljoin(url, a["href"]).split("#")[0].split("?")[0]
            if urlparse(nxt).netloc == urlparse(BASE).netloc and nxt not in seen:
                queue.append(nxt)
    return order


def page_to_markdown(url: str) -> str | None:
    resp = get(url)
    if resp is None:
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    title = (soup.title.string or url).strip() if soup.title else url
    main = soup.find("main") or soup.find("article") or soup.body
    if main is None:
        return None
    text = re.sub(r"\n{3,}", "\n\n", main.get_text("\n", strip=True))
    n_images = len(main.find_all("img")) if hasattr(main, "find_all") else 0
    screenshot_flag = ""
    if len(text) < 400 and n_images >= 3:
        screenshot_flag = (
            "\n> ⚠️ This article seems to be mostly screenshots "
            f"({n_images} images, little text) — steps may need manual write-up or OCR.\n"
        )
    if len(text) < 80:
        return None  # empty shell / nav page
    return f"## {title}\n\nSource: {url}\n{screenshot_flag}\n{text}\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="knowledge/hrone_howto_crawled.md")
    parser.add_argument("--max-pages", type=int, default=200)
    args = parser.parse_args()

    urls = urls_from_sitemap() or crawl_links(args.max_pages)
    if not urls:
        print("Could not reach the portal or find any pages. Are you on a network that can open " + BASE + " ?")
        return

    sections = []
    for i, url in enumerate(urls[: args.max_pages], 1):
        print(f"[{i}/{min(len(urls), args.max_pages)}] {url}")
        md = page_to_markdown(url)
        if md:
            sections.append(md)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("# HROne Help Portal — crawled articles (review before use)\n\n")
        f.write("\n\n---\n\n".join(sections))
    print(f"\nWrote {len(sections)} articles to {args.out}")
    print("Review + curate them, then merge the good ones into knowledge/hrone_howto.md")


if __name__ == "__main__":
    main()
