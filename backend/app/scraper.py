from __future__ import annotations

import ipaddress
import socket
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = "AICheckerBot/0.1 (+educational EU AI Act triage tool; not legal advice)"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
REQUEST_TIMEOUT = (5, 8)  # (connect, read) seconds
MAX_RESPONSE_BYTES = 2_000_000
MAX_REDIRECTS = 5
MAX_PAGES = 5
MAX_TEXT_PER_PAGE = 6000
MAX_COMBINED_TEXT = 12000
MAX_SITEMAP_INDEX_DEPTH = 1


class ScraperError(Exception):
    pass


@dataclass
class PageContent:
    url: str
    title: str
    text: str


@dataclass
class ScrapeResult:
    root_url: str
    source: str  # "sitemap" | "robots_txt_sitemap" | "homepage_links" | "homepage_only" | "none"
    pages: list[PageContent] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def combined_text(self) -> str:
        chunks = [f"### {p.title or p.url}\n{p.text}" for p in self.pages]
        return "\n\n".join(chunks)[:MAX_COMBINED_TEXT]

    def to_dict(self) -> dict:
        return {
            "root_url": self.root_url,
            "source": self.source,
            "pages": [{"url": p.url, "title": p.title, "text": p.text} for p in self.pages],
            "combined_text": self.combined_text,
            "errors": self.errors,
        }


@dataclass
class _FetchResult:
    url: str
    status_code: int
    content: bytes
    content_type: str


def _is_public_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def _validate_public_url(url: str) -> None:
    """Reject non-http(s) schemes and hosts resolving to internal addresses.

    This is called on the original URL and again on every redirect hop, since a
    public hostname can still resolve (or be redirected) to a private/loopback/
    link-local address (e.g. cloud metadata endpoints) — a classic SSRF vector
    for any service that fetches user-submitted URLs server-side.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ScraperError(f"Unsupported URL scheme: {parsed.scheme!r}")
    if not parsed.hostname:
        raise ScraperError("URL has no hostname")

    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise ScraperError(f"Could not resolve host {parsed.hostname!r}: {exc}") from exc

    resolved_ips = {info[4][0] for info in infos}
    if not resolved_ips or not all(_is_public_ip(ip) for ip in resolved_ips):
        raise ScraperError(f"Refusing to fetch {parsed.hostname!r}: resolves to a non-public address")


def _normalize_for_dedup(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"


def _same_site(url_a: str, url_b: str) -> bool:
    def norm(host: str) -> str:
        host = host.lower()
        return host[4:] if host.startswith("www.") else host

    host_a = norm(urlparse(url_a).hostname or "")
    host_b = norm(urlparse(url_b).hostname or "")
    return bool(host_a) and host_a == host_b


def _decode(content: bytes) -> str:
    return content.decode("utf-8", errors="replace")


def _safe_get(url: str) -> _FetchResult:
    """GET with SSRF-validated redirects and a hard cap on response size."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        _validate_public_url(current)
        with requests.get(
            current, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=False, stream=True
        ) as resp:
            if resp.status_code in (301, 302, 303, 307, 308) and resp.headers.get("Location"):
                current = urljoin(current, resp.headers["Location"])
                continue

            raw = resp.raw.read(MAX_RESPONSE_BYTES + 1, decode_content=True)
            return _FetchResult(
                url=current,
                status_code=resp.status_code,
                content=raw[:MAX_RESPONSE_BYTES],
                content_type=resp.headers.get("Content-Type", ""),
            )

    raise ScraperError(f"Too many redirects starting from {url}")


def _fetch_sitemap_urls(sitemap_url: str, depth: int = 0) -> list[str]:
    if depth > MAX_SITEMAP_INDEX_DEPTH:
        return []
    try:
        fetch = _safe_get(sitemap_url)
    except ScraperError:
        return []
    if fetch.status_code != 200:
        return []

    try:
        root = ET.fromstring(fetch.content)
    except ET.ParseError:
        return []

    if root.tag.endswith("}sitemapindex"):
        nested = [loc.text.strip() for loc in root.iter() if loc.tag.endswith("}loc") and loc.text]
        urls: list[str] = []
        for nested_sitemap in nested[:MAX_PAGES]:
            urls.extend(_fetch_sitemap_urls(nested_sitemap, depth=depth + 1))
        return urls

    if root.tag.endswith("}urlset"):
        return [loc.text.strip() for loc in root.iter() if loc.tag.endswith("}loc") and loc.text]

    return []


def _discover_sitemap_urls(root_url: str) -> tuple[list[str], str]:
    parsed = urlparse(root_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    page_urls = _fetch_sitemap_urls(f"{origin}/sitemap.xml")
    if page_urls:
        return page_urls, "sitemap"

    try:
        robots = _safe_get(f"{origin}/robots.txt")
    except ScraperError:
        return [], "none"

    if robots.status_code != 200:
        return [], "none"

    sitemap_lines = [
        line.split(":", 1)[1].strip()
        for line in _decode(robots.content).splitlines()
        if line.lower().startswith("sitemap:") and ":" in line
    ]
    for sitemap_url in sitemap_lines:
        page_urls = _fetch_sitemap_urls(sitemap_url)
        if page_urls:
            return page_urls, "robots_txt_sitemap"

    return [], "none"


def _extract_homepage_links(root_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        absolute = urljoin(root_url, a["href"].split("#")[0].strip())
        if not absolute.startswith(("http://", "https://")):
            continue
        if not _same_site(root_url, absolute) or absolute in seen:
            continue
        seen.add(absolute)
        links.append(absolute)
    return links


def _extract_visible_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "svg", "iframe"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return title, text[:MAX_TEXT_PER_PAGE]


def _fetch_page_content(url: str) -> PageContent | None:
    try:
        fetch = _safe_get(url)
    except ScraperError:
        return None
    if fetch.status_code != 200 or "html" not in fetch.content_type.lower():
        return None
    title, text = _extract_visible_text(_decode(fetch.content))
    if not text:
        return None
    return PageContent(url=fetch.url, title=title, text=text)


def scrape_url(url: str) -> ScrapeResult:
    """Fetch a small, same-site set of pages for a user-submitted URL.

    Discovery order: sitemap.xml -> robots.txt-declared sitemaps -> homepage
    links. The homepage itself is always included when reachable.
    """
    url = url.strip()
    if not urlparse(url).scheme:
        url = f"https://{url}"

    try:
        _validate_public_url(url)
    except ScraperError as exc:
        return ScrapeResult(root_url=url, source="none", errors=[str(exc)])

    result = ScrapeResult(root_url=url, source="none")

    try:
        homepage_fetch = _safe_get(url)
    except ScraperError as exc:
        result.errors.append(f"Homepage fetch failed: {exc}")
        return result

    if homepage_fetch.status_code != 200:
        result.errors.append(f"Homepage returned HTTP {homepage_fetch.status_code}")
        return result

    homepage_html = _decode(homepage_fetch.content)
    title, text = _extract_visible_text(homepage_html)
    if text:
        result.pages.append(PageContent(url=homepage_fetch.url, title=title, text=text))

    candidate_urls, source = _discover_sitemap_urls(url)
    if not candidate_urls:
        candidate_urls = _extract_homepage_links(url, homepage_html)
        source = "homepage_links" if candidate_urls else "homepage_only"
    result.source = source

    already = {_normalize_for_dedup(p.url) for p in result.pages}
    seen: set[str] = set()
    ordered_candidates = []
    for candidate in candidate_urls:
        key = _normalize_for_dedup(candidate)
        if key in already or key in seen or not _same_site(url, candidate):
            continue
        seen.add(key)
        ordered_candidates.append(candidate)

    for candidate in ordered_candidates:
        if len(result.pages) >= MAX_PAGES:
            break
        page = _fetch_page_content(candidate)
        if page is not None:
            result.pages.append(page)

    if not result.pages:
        result.errors.append("No page content could be extracted")

    return result
