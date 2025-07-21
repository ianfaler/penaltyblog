import pickle
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

import numpy as np

from penaltyblog.models.custom_types import (
    GoalInput,
    TeamInput,
    WeightInput,
)

logger = logging.getLogger(__name__)


class ModelNotFittedError(ValueError):
    """Raised when attempting to use an unfitted model."""

    pass


class BaseGoalsModel(ABC):
    """
    Base class for football prediction models.

    Provides common functionality for football prediction models, including:
      - Input validation
      - Team setup (unique team list and mapping)
      - Model persistence (save/load)
      - Abstract methods for fit and predict
    """

    def __init__(
        self,
        goals_home: GoalInput,
        goals_away: GoalInput,
        teams_home: TeamInput,
        teams_away: TeamInput,
        weights: WeightInput = None,
    ):
        # Initialize fitted status
        self.fitted = False
        self._params = None

        # Validate and convert inputs to numpy arrays
        self._validate_inputs(goals_home, goals_away, teams_home, teams_away, weights)

        # Convert inputs to numpy arrays
        self.goals_home = np.asarray(goals_home, dtype=np.int64, order="C")
        self.goals_away = np.asarray(goals_away, dtype=np.int64, order="C")
        self.teams_home = np.asarray(teams_home, dtype=str, order="C")
        self.teams_away = np.asarray(teams_away, dtype=str, order="C")

        n_matches = len(self.goals_home)

        # Process weights: if None, create an array of 1s; else, validate its length
        if weights is None:
            self.weights = np.ones(n_matches, dtype=np.double, order="C")
        else:
            self.weights = np.asarray(weights, dtype=np.double, order="C")
            if len(self.weights) != n_matches:
                raise ValueError(
                    f"Weights array must have the same length as the number of matches. "
                    f"Expected {n_matches}, got {len(self.weights)}."
                )

        # Validate that arrays have consistent lengths
        arrays = [
            self.goals_home,
            self.goals_away,
            self.teams_home,
            self.teams_away,
            self.weights,
        ]
        lengths = [len(arr) for arr in arrays]
        if not all(length == n_matches for length in lengths):
            raise ValueError(
                f"All input arrays must have the same length. "
                f"Got lengths: goals_home={len(self.goals_home)}, goals_away={len(self.goals_away)}, "
                f"teams_home={len(self.teams_home)}, teams_away={len(self.teams_away)}, "
                f"weights={len(self.weights)}"
            )

        if self.teams_home.size == 0 or self.teams_away.size == 0:
            raise ValueError("Team arrays must not be empty.")

        # Set up teams after validation
        self._setup_teams()

        logger.info(
            f"Initialized {self.__class__.__name__} with {n_matches} matches and {self.n_teams} teams"
        )

    def _validate_inputs(self, goals_home, goals_away, teams_home, teams_away, weights):
        """Validate input data types and basic constraints."""

        # Check that inputs are not None
        if any(x is None for x in [goals_home, goals_away, teams_home, teams_away]):
            raise ValueError(
                "goals_home, goals_away, teams_home, and teams_away cannot be None"
            )

        # Check that inputs are not empty
        if any(len(x) == 0 for x in [goals_home, goals_away, teams_home, teams_away]):
            raise ValueError("Input arrays cannot be empty")

        # Validate goal values are non-negative integers
        try:
            goals_home_arr = np.asarray(goals_home, dtype=np.int64)
            goals_away_arr = np.asarray(goals_away, dtype=np.int64)

            if np.any(goals_home_arr < 0):
                raise ValueError("Home goals must be non-negative integers")
            if np.any(goals_away_arr < 0):
                raise ValueError("Away goals must be non-negative integers")

        except (ValueError, TypeError) as e:
            raise ValueError(f"Goals must be convertible to non-negative integers: {e}")

        # Validate team names are not empty strings
        try:
            teams_home_arr = np.asarray(teams_home, dtype=str)
            teams_away_arr = np.asarray(teams_away, dtype=str)

            if np.any(teams_home_arr == "") or np.any(teams_away_arr == ""):
                raise ValueError("Team names cannot be empty strings")

        except (ValueError, TypeError) as e:
            raise ValueError(f"Team names must be convertible to strings: {e}")

        # Validate weights if provided
        if weights is not None:
            try:
                weights_arr = np.asarray(weights, dtype=np.double)
                if np.any(weights_arr < 0):
                    raise ValueError("Weights must be non-negative")
                if np.any(~np.isfinite(weights_arr)):
                    raise ValueError("Weights must be finite values")
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Weights must be convertible to non-negative finite numbers: {e}"
                )

    def _setup_teams(self):
        """Set up unique teams and mappings for fast lookup."""
        self.teams = np.sort(
            np.unique(np.concatenate([self.teams_home, self.teams_away]))
        )
        self.n_teams = len(self.teams)

        if self.n_teams < 2:
            raise ValueError(f"Must have at least 2 unique teams, got {self.n_teams}")

        self.team_to_idx = {team: i for i, team in enumerate(self.teams)}
        self.home_idx = np.array(
            [self.team_to_idx[t] for t in self.teams_home], dtype=np.int64, order="C"
        )
        self.away_idx = np.array(
            [self.team_to_idx[t] for t in self.teams_away], dtype=np.int64, order="C"
        )

    def _check_fitted(self):
        """Check if model has been fitted, raise standardized error if not."""
        if not self.fitted:
            raise ModelNotFittedError(
                f"{self.__class__.__name__} has not been fitted yet. "
                "Call the .fit() method before using .predict() or .get_params()."
            )

    def _validate_prediction_teams(self, home_team: str, away_team: str):
        """Validate that teams exist in the training data."""
        if home_team not in self.team_to_idx:
            available_teams = ", ".join(sorted(self.teams[:10]))  # Show first 10 teams
            more_text = (
                f" and {len(self.teams) - 10} more" if len(self.teams) > 10 else ""
            )
            raise ValueError(
                f"Home team '{home_team}' not found in training data. "
                f"Available teams: {available_teams}{more_text}"
            )

        if away_team not in self.team_to_idx:
            available_teams = ", ".join(sorted(self.teams[:10]))  # Show first 10 teams
            more_text = (
                f" and {len(self.teams) - 10} more" if len(self.teams) > 10 else ""
            )
            raise ValueError(
                f"Away team '{away_team}' not found in training data. "
                f"Available teams: {available_teams}{more_text}"
            )

    def save(self, filepath: str):
        """
        Saves the model to a file using pickle.

        Parameters
        ----------
        filepath : str
            The path to the file where the model will be saved.
        """
        try:
            with open(filepath, "wb") as f:
                pickle.dump(self, f)
            logger.info(f"Model saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving model to {filepath}: {e}")
            raise

    @classmethod
    def load(cls, filepath: str) -> Any:
        """
        Loads a model from a file.

        Parameters
        ----------
        filepath : str
            The path to the file from which the model will be loaded.

        Returns
        -------
        Any
            An instance of the model.
        """
        try:
            with open(filepath, "rb") as f:
                model = pickle.load(f)
            logger.info(f"Model loaded from {filepath}")
            return model
        except Exception as e:
            logger.error(f"Error loading model from {filepath}: {e}")
            raise

    @abstractmethod
    def fit(self):
        """
        Fits the model to the data.

        Must be implemented by the subclass.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def predict(self, home_team: str, away_team: str, max_goals: int = 15):
        """
        Predicts the probability of each scoreline for a given match.

        Must be implemented by the subclass.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_params(self) -> Dict[str, Any]:
        """
        Returns the fitted parameters of the model.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    @property
    def params(self) -> Dict[str, Any]:
        """
        Property to retrieve the fitted model parameters.
        Same as `get_params()`, but allows attribute-like access.

        Returns
        -------
        dict
            A dictionary containing attack, defense, home advantage, and correlation parameters.

        Raises
        ------
        ModelNotFittedError
            If the model has not been fitted yet.
        """
        return self.get_params()

    def __repr__(self):
        """String representation of the model."""
        lines = [
            "Module: Penaltyblog",
            "",
            f"Model: {self.__class__.__name__}",
            "",
        ]

        if not self.fitted:
            lines.append("Status: Model not fitted")
        else:
            lines.extend(
                [
                    f"Teams: {self.n_teams}",
                    f"Matches: {len(self.goals_home)}",
                    "Status: Model fitted and ready for predictions",
                ]
            )

        return "\n".join(lines)
