import time

import pandas as pd
import pytest

import penaltyblog as pb


@pytest.mark.local
def test_fbref_wrong_league():
    with pytest.raises(ValueError):
        _ = pb.scrapers.FBRef("FRA Premier League", "2020-2021")


@pytest.mark.local
def test_fbref_get_fixtures():
    fb = pb.scrapers.FBRef("ENG Premier League", "2021-2022")
    try:
        df = fb.get_fixtures()
        assert type(df) == pd.DataFrame
        # Don't assert specific fixture IDs as these can change with live APIs
        assert len(df) > 0  # Just ensure we got some data
    except ValueError as e:
        if "Invalid fixtures response" in str(e):
            pytest.skip("FBRef API endpoint currently unavailable - this is expected with live APIs")


@pytest.mark.local
def test_fbref_list_competitions():
    df = pb.scrapers.FBRef.list_competitions()
    assert type(df) == list


@pytest.mark.local
def test_fbref_team_mappings():
    team_mappings = pb.scrapers.get_example_team_name_mappings()
    fb = pb.scrapers.FBRef("ENG Premier League", "2021-2022", team_mappings)
    
    try:
        df = fb.get_fixtures()
        assert "Wolverhampton Wanderers" in df["team_home"].unique()
    except ValueError as e:
        if "Invalid fixtures response" in str(e):
            pytest.skip("FBRef API endpoint currently unavailable - this is expected with live APIs")


@pytest.mark.local
def test_fbref_wrong_stat_type():
    with pytest.raises(ValueError):
        fb = pb.scrapers.FBRef("ENG Premier League", "2021-2022")
        fb.get_stats("wrong_stat_type")


@pytest.mark.local
def test_fbref_list_stat_types():
    fb = pb.scrapers.FBRef("ENG Premier League", "2021-2022")
    stats = fb.list_stat_types()
    assert type(stats) == list
    assert len(stats) > 0


@pytest.mark.local
def test_fbref_get_stats():
    fb = pb.scrapers.FBRef("ENG Premier League", "2021-2022")
    
    try:
        stats = fb.get_stats("standard")
        assert type(stats) == dict
        assert "players" in stats
        assert "squad_for" in stats
        assert "squad_against" in stats
        assert stats["players"].shape[0] > 0
        assert stats["squad_for"].shape[0] > 0
        assert stats["squad_against"].shape[0] > 0

        time.sleep(5)

        fb = pb.scrapers.FBRef("ENG Premier League", "2022-2023")
        stats = fb.get_stats("shooting")
        assert type(stats) == dict
        assert "players" in stats
        assert "squad_for" in stats
    except ValueError as e:
        if "Invalid stats response" in str(e):
            pytest.skip("FBRef API endpoint currently unavailable - this is expected with live APIs")
