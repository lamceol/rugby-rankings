"""Check the rankings data embedded in index.html is complete and drawable on the map."""
import json
import re
from pathlib import Path

import pytest

HTML = (Path(__file__).parent.parent / "index.html").read_text(encoding="utf-8")
UK_IDS = {"ENG", "SCO", "WAL"}


def load_rankings():
    m = re.search(r"const RANKINGS = (\{.*?\n\});", HTML, re.S)
    assert m, "RANKINGS block not found in index.html"
    return json.loads(m.group(1))


RANKINGS = load_rankings()
TEAMS = RANKINGS["teams"]
MAP_IDS = set(re.findall(r'"id":"([^"]+)","properties"', HTML))


def test_has_teams():
    assert len(TEAMS) >= 50


def test_sorted_by_unique_rank():
    positions = [t["pos"] for t in TEAMS]
    assert positions == sorted(positions)
    assert len(set(positions)) == len(positions)


def test_fields_are_valid():
    for t in TEAMS:
        assert t["name"].strip()
        assert isinstance(t["pts"], (int, float)) and t["pts"] > 0
        assert t["prevPos"] is None or t["prevPos"] >= 1


def test_points_decrease_with_rank():
    pts = [t["pts"] for t in TEAMS]
    assert pts == sorted(pts, reverse=True)


def test_as_of_is_a_date_or_unknown():
    assert RANKINGS["asOf"] is None or re.fullmatch(r"\d{4}-\d{2}-\d{2}", RANKINGS["asOf"])


def test_map_ids_found():
    assert len(MAP_IDS) > 150, "couldn't read country ids from the map data"


@pytest.mark.parametrize("team", TEAMS, ids=lambda t: t["name"])
def test_every_team_is_on_the_map(team):
    """Each ranked nation needs a country shape, a UK nation shape, or a dot."""
    assert team["id"], f"{team['name']} has no map id - add it to data/teams.json"
    if "dot" in team:
        lon, lat = team["dot"]
        assert -180 <= lon <= 180 and -90 <= lat <= 90
    else:
        assert team["id"] in MAP_IDS | UK_IDS, (
            f"{team['name']} (id {team['id']}) has no shape on the map - "
            "add a 'dot' for it in data/teams.json"
        )
