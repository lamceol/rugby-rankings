"""Unit tests for scripts/update_rankings.py (no network needed)."""
import json
import sys
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import update_rankings as ur  # noqa: E402


def entry(name, pos, prev, pts):
    return {"team": {"name": name}, "pos": pos, "previousPos": prev, "pts": pts}


def test_normalise_matches_spelling_variants():
    assert ur.normalise("Côte d'Ivoire") == ur.normalise("Cote D Ivoire")
    assert ur.normalise("Trinidad & Tobago") == ur.normalise("Trinidad and Tobago")
    assert ur.normalise("Saint Vincent and the Grenadines") == ur.normalise("St Vincent & Grenadines")


def test_lookup_handles_aliases():
    lookup = ur.load_lookup()
    assert lookup[ur.normalise("Hong Kong China")][0] == "Hong Kong"
    assert lookup[ur.normalise("Niue Island")][0] == "Niue"  # World Rugby's spelling
    assert lookup[ur.normalise("Australia")][1]["id"] == "036"  # zero-padded like the map


def test_parse_api_reads_entries_and_date():
    payload = {"effective": {"label": "2026-10-19", "millis": 1760832000000},
               "entries": [entry("Ireland", 1, 2, 92.123), entry("England", 2, 1, 90)]}
    as_of, rows = ur.parse_api(payload)
    assert as_of == "2026-10-19"
    assert rows[0] == {"name": "Ireland", "pos": 1, "prevPos": 2, "pts": 92.12}


def test_parse_date_falls_back_to_millis():
    assert ur.parse_date({"millis": 1760832000000}) == "2025-10-19"


def test_parse_api_rejects_unexpected_format():
    with pytest.raises(ValueError):
        ur.parse_api({"rankings": []})
    with pytest.raises(ValueError):
        ur.parse_api({"entries": [{"team": "Ireland"}]})


def test_build_attaches_ids_and_reports_unknown_teams():
    rows = [{"name": "Tonga", "pos": 2, "prevPos": 2, "pts": 60},
            {"name": "Atlantis", "pos": 1, "prevPos": None, "pts": 70}]
    data, unmapped = ur.build("2026-10-19", rows, ur.load_lookup())
    assert [t["name"] for t in data["teams"]] == ["Atlantis", "Tonga"]  # sorted by rank
    assert data["teams"][1]["id"] == "776" and "dot" in data["teams"][1]
    assert data["teams"][0]["id"] is None
    assert unmapped == ["Atlantis"]


def test_validate_rejects_short_or_duplicate_lists():
    few = {"teams": [{"pos": 1}]}
    with pytest.raises(ValueError):
        ur.validate(few)
    dupes = {"teams": [{"pos": 1}] * 60}
    with pytest.raises(ValueError):
        ur.validate(dupes)


def test_write_index_replaces_only_the_data_block(tmp_path):
    page = tmp_path / "index.html"
    page.write_text(f"before\n{ur.BEGIN}\nold\n{ur.END}\nafter\n")
    block = ur.render_block({"asOf": None, "teams": [{"name": "Fiji", "pos": 1}]})
    assert ur.write_index(block, page)
    text = page.read_text()
    assert text.startswith("before\n") and text.endswith("after\n") and "old" not in text
    assert not ur.write_index(block, page)  # second run: no change


class FakeResponse:
    def __init__(self, payload):
        self.body = json.dumps(payload).encode()

    def read(self, *args):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_fetch_falls_back_to_next_source(monkeypatch):
    good = {"entries": [entry("Ireland", 1, 1, 90)]}

    def fake_urlopen(req, timeout):
        if "first" in req.full_url:
            raise urllib.error.URLError("Name or service not known")
        return FakeResponse(good)

    monkeypatch.setattr(ur.urllib.request, "urlopen", fake_urlopen)
    assert ur.fetch(["https://first.example", "https://second.example"]) == good


def test_fetch_skips_responses_in_the_wrong_format(monkeypatch):
    monkeypatch.setattr(ur.urllib.request, "urlopen", lambda req, timeout: FakeResponse({"oops": 1}))
    with pytest.raises(RuntimeError, match="No World Rugby rankings source worked"):
        ur.fetch(["https://a.example", "https://b.example"])
