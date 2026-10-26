"""Check every external link in index.html returns a non-error response."""
import pytest
import requests
from html.parser import HTMLParser
from pathlib import Path


class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for attr, value in attrs:
                if attr == "href" and value and value.startswith("http"):
                    self.urls.append(value)


def get_urls():
    html = (Path(__file__).parent.parent / "index.html").read_text()
    parser = LinkExtractor()
    parser.feed(html)
    return sorted(set(parser.urls))


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; link-checker/1.0; "
        "+https://github.com/lamceol/rugby-rankings)"
    )
}


@pytest.mark.parametrize("url", get_urls())
def test_url_reachable(url):
    try:
        resp = requests.head(url, headers=HEADERS, timeout=15, allow_redirects=True)
        if resp.status_code in (405, 403):
            resp = requests.get(
                url, headers=HEADERS, timeout=15, allow_redirects=True, stream=True
            )
    except requests.RequestException as exc:
        pytest.fail(f"Request error for {url}: {exc}")

    assert resp.status_code < 400, f"HTTP {resp.status_code} for {url}"
