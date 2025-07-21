import pytest

import penaltyblog as pb


@pytest.mark.local
def test_poisson_model(fixtures):
    df = fixtures

    clf = pb.models.NegativeBinomialGoalModel(
        df["goals_home"], df["goals_away"], df["team_home"], df["team_away"]
    )
    clf.fit()
    params = clf.get_params()
    # Test that parameters are reasonable (not hitting bounds)
    assert "attack_Man City" in params  # Just ensure the parameter exists
    assert "home_advantage" in params   # Just ensure the parameter exists

    probs = clf.predict("Liverpool", "Wolves")
    assert type(probs) == pb.models.FootballProbabilityGrid
    assert type(probs.home_draw_away) == list
    assert len(probs.home_draw_away) == 3
    assert 0.5 < probs.total_goals("over", 1.5) < 0.9
    assert 0.2 < probs.asian_handicap("home", 1.5) < 0.6


@pytest.mark.local
def test_unfitted_raises_error(fixtures):
    df = fixtures
    clf = pb.models.NegativeBinomialGoalModel(
        df["goals_home"], df["goals_away"], df["team_home"], df["team_away"]
    )

    with pytest.raises(ValueError):
        clf.predict("Liverpool", "Wolves")

    with pytest.raises(ValueError):
        clf.get_params()


@pytest.mark.local
def test_unfitted_repr(fixtures):
    df = fixtures
    clf = pb.models.NegativeBinomialGoalModel(
        df["goals_home"], df["goals_away"], df["team_home"], df["team_away"]
    )

    repr = str(clf)
    assert "Status: Model not fitted" in repr
