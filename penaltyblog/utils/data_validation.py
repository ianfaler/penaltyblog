"""
Data validation utilities for penaltyblog package.

This module provides comprehensive data quality checks for football data
including validation of fixtures, stats, and historical data accuracy.
"""

import logging
import warnings
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class DataValidationError(ValueError):
    """Raised when data validation fails."""

    pass


class DataValidationWarning(UserWarning):
    """Warning for data quality issues that don't prevent operation."""

    pass


class DataQualityValidator:
    """
    Comprehensive data quality validator for football data.
    """

    def __init__(self, strict_mode: bool = False):
        """
        Initialize the validator.

        Parameters
        ----------
        strict_mode : bool
            If True, raise exceptions for warnings. If False, issue warnings.
        """
        self.strict_mode = strict_mode
        self.validation_report: dict[str, list[str]] = {"errors": [], "warnings": [], "info": []}

    def reset_report(self):
        """Reset the validation report."""
        self.validation_report: dict[str, list[str]] = {"errors": [], "warnings": [], "info": []}

    def _add_error(self, message: str):
        """Add an error to the report."""
        self.validation_report["errors"].append(message)
        logger.error(message)
        if self.strict_mode:
            raise DataValidationError(message)

    def _add_warning(self, message: str):
        """Add a warning to the report."""
        self.validation_report["warnings"].append(message)
        logger.warning(message)
        if self.strict_mode:
            raise DataValidationError(f"Warning in strict mode: {message}")
        else:
            warnings.warn(message, DataValidationWarning)

    def _add_info(self, message: str):
        """Add info to the report."""
        self.validation_report["info"].append(message)
        logger.info(message)

    def validate_fixtures_data(
        self, df: pd.DataFrame, competition: str = "", season: str = ""
    ) -> Dict[str, Any]:
        """
        Validate fixtures/results data for completeness and consistency.

        Parameters
        ----------
        df : pd.DataFrame
            Fixtures dataframe to validate
        competition : str
            Competition name for context
        season : str
            Season for context

        Returns
        -------
        Dict[str, Any]
            Validation report with errors, warnings, and statistics
        """
        self.reset_report()
        context = f"{competition} {season}".strip()

        if df.empty:
            self._add_error(f"Empty fixtures dataframe for {context}")
            return self.validation_report

        self._add_info(f"Validating {len(df)} fixtures for {context}")

        # Check required columns
        required_cols = ["team_home", "team_away", "goals_home", "goals_away"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            self._add_error(f"Missing required columns: {missing_cols}")
            return self.validation_report

        # Validate team names
        self._validate_team_names(df)

        # Validate goals
        self._validate_goals(df)

        # Validate dates if present
        if "date" in df.columns:
            self._validate_dates(df, season)

        # Check for duplicates
        self._check_duplicates(df, context)

        # Validate data consistency
        self._validate_data_consistency(df, context)

        # Check season completeness
        if season:
            self._check_season_completeness(df, season, context)

        return self.validation_report

    def _validate_team_names(self, df: pd.DataFrame):
        """Validate team names in the dataframe."""
        for col in ["team_home", "team_away"]:
            if col not in df.columns:
                continue

            # Check for empty team names
            empty_teams = df[col].isna() | (df[col] == "") | (df[col].str.strip() == "")
            if empty_teams.any():
                count = empty_teams.sum()
                self._add_error(f"Found {count} empty team names in {col}")

            # Check for suspicious team names
            suspicious_patterns = ["test", "unknown", "tbd", "null", "nan"]
            for pattern in suspicious_patterns:
                suspicious = df[col].str.lower().str.contains(pattern, na=False)
                if suspicious.any():
                    teams = df.loc[suspicious, col].unique()
                    self._add_warning(f"Suspicious team names in {col}: {teams}")

        # Check for team name consistency
        home_teams = set(df["team_home"].dropna().unique())
        away_teams = set(df["team_away"].dropna().unique())

        home_only = home_teams - away_teams
        away_only = away_teams - home_teams

        if home_only:
            self._add_warning(f"Teams that only appear as home: {home_only}")
        if away_only:
            self._add_warning(f"Teams that only appear as away: {away_only}")

        total_teams = len(home_teams | away_teams)
        self._add_info(f"Found {total_teams} unique teams")

    def _validate_goals(self, df: pd.DataFrame):
        """Validate goal data."""
        for col in ["goals_home", "goals_away"]:
            if col not in df.columns:
                continue

            # Convert to numeric and check for conversion issues
            len(df)
            numeric_goals = pd.to_numeric(df[col], errors="coerce")
            conversion_failures = numeric_goals.isna() & df[col].notna()

            if conversion_failures.any():
                count = conversion_failures.sum()
                self._add_error(f"Found {count} non-numeric values in {col}")

            # Check for negative goals
            negative_goals = numeric_goals < 0
            if negative_goals.any():
                count = negative_goals.sum()
                self._add_error(f"Found {count} negative values in {col}")

            # Check for unusually high scores
            high_scores = numeric_goals > 10
            if high_scores.any():
                count = high_scores.sum()
                max_score = numeric_goals.max()
                self._add_warning(
                    f"Found {count} unusually high scores in {col} (max: {max_score})"
                )

            # Statistical checks
            if not numeric_goals.empty:
                mean_goals = numeric_goals.mean()
                if mean_goals < 0.5 or mean_goals > 5.0:
                    self._add_warning(
                        f"Unusual average for {col}: {mean_goals:.2f} goals per game"
                    )

    def _validate_dates(self, df: pd.DataFrame, season: str = ""):
        """Validate date information."""
        date_col = "date" if "date" in df.columns else None
        if not date_col:
            return

        # Check for missing dates
        missing_dates = df[date_col].isna()
        if missing_dates.any():
            count = missing_dates.sum()
            self._add_warning(f"Found {count} missing dates")

        valid_dates = df[date_col].dropna()
        if valid_dates.empty:
            return

        # Check date range
        min_date = valid_dates.min()
        max_date = valid_dates.max()
        date_range = max_date - min_date

        self._add_info(
            f"Date range: {min_date.date()} to {max_date.date()} ({date_range.days} days)"
        )

        # Check for future dates
        future_dates = valid_dates > datetime.now()
        if future_dates.any():
            count = future_dates.sum()
            self._add_warning(f"Found {count} future dates")

        # Check for very old dates
        old_threshold = datetime.now() - timedelta(days=365 * 20)  # 20 years
        old_dates = valid_dates < old_threshold
        if old_dates.any():
            count = old_dates.sum()
            self._add_warning(f"Found {count} dates older than 20 years")

        # Season-specific validation
        if season and "-" in season:
            try:
                start_year, end_year = map(int, season.split("-"))
                expected_start = datetime(
                    start_year, 7, 1
                )  # Assume season starts in July
                expected_end = datetime(end_year, 6, 30)  # Ends in June

                outside_season = (valid_dates < expected_start) | (
                    valid_dates > expected_end
                )
                if outside_season.any():
                    count = outside_season.sum()
                    self._add_warning(
                        f"Found {count} dates outside expected season range"
                    )
            except ValueError:
                pass  # Invalid season format

    def _check_duplicates(self, df: pd.DataFrame, context: str = ""):
        """Check for duplicate fixtures."""
        if not all(col in df.columns for col in ["team_home", "team_away"]):
            return

        # Check for exact duplicates
        duplicate_rows = df.duplicated()
        if duplicate_rows.any():
            count = duplicate_rows.sum()
            self._add_warning(f"Found {count} completely duplicate rows in {context}")

        # Check for duplicate fixtures (same teams, same date if available)
        if "date" in df.columns:
            fixture_cols = ["team_home", "team_away", "date"]
        else:
            fixture_cols = ["team_home", "team_away"]

        duplicate_fixtures = df.duplicated(subset=fixture_cols)
        if duplicate_fixtures.any():
            count = duplicate_fixtures.sum()
            self._add_warning(f"Found {count} duplicate fixtures in {context}")

        # Check for reverse fixtures on same date
        if "date" in df.columns:
            df_reversed = df.copy()
            df_reversed["team_home"], df_reversed["team_away"] = (
                df["team_away"],
                df["team_home"],
            )

            # Find matches where teams play each other twice on same date
            merged = df.merge(
                df_reversed, on=["team_home", "team_away", "date"], how="inner"
            )
            if not merged.empty:
                count = len(merged)
                self._add_warning(f"Found {count} potential reverse fixture conflicts")

    def _validate_data_consistency(self, df: pd.DataFrame, context: str = ""):
        """Check for data consistency issues."""
        if not all(
            col in df.columns
            for col in ["team_home", "team_away", "goals_home", "goals_away"]
        ):
            return

        # Check for teams playing themselves
        self_matches = df["team_home"] == df["team_away"]
        if self_matches.any():
            count = self_matches.sum()
            self._add_error(f"Found {count} matches where teams play themselves")

        # Check goals consistency with result patterns
        goals_home = pd.to_numeric(df["goals_home"], errors="coerce")
        goals_away = pd.to_numeric(df["goals_away"], errors="coerce")

        if not goals_home.empty and not goals_away.empty:
            # Check for suspicious patterns
            always_home_wins = (goals_home > goals_away).all() and len(df) > 10
            always_away_wins = (goals_away > goals_home).all() and len(df) > 10
            always_draws = (goals_home == goals_away).all() and len(df) > 10

            if always_home_wins:
                self._add_warning(
                    "All matches result in home wins - suspicious pattern"
                )
            if always_away_wins:
                self._add_warning(
                    "All matches result in away wins - suspicious pattern"
                )
            if always_draws:
                self._add_warning("All matches result in draws - suspicious pattern")

    def _check_season_completeness(
        self, df: pd.DataFrame, season: str, context: str = ""
    ):
        """Check if season data appears complete."""
        if not all(col in df.columns for col in ["team_home", "team_away"]):
            return

        teams = set(df["team_home"].unique()) | set(df["team_away"].unique())
        n_teams = len(teams)
        n_matches = len(df)

        # Estimate expected matches for common league formats
        expected_matches_per_team = {
            20: 38,  # Premier League, La Liga, etc.
            18: 34,  # Bundesliga, Ligue 1
            16: 30,  # Some smaller leagues
            14: 26,
            12: 22,
            10: 18,
        }

        expected = expected_matches_per_team.get(
            n_teams, n_teams * 2 - 2
        )  # Default: round robin home/away
        expected_total = (n_teams * expected) // 2  # Each match involves 2 teams

        completeness = n_matches / expected_total if expected_total > 0 else 0

        self._add_info(
            f"Season completeness: {n_matches}/{expected_total} matches ({completeness:.1%})"
        )

        if completeness < 0.8:
            self._add_warning(
                f"Season appears incomplete: only {completeness:.1%} of expected matches"
            )
        elif completeness > 1.2:
            self._add_warning(
                f"More matches than expected: {completeness:.1%} of typical season"
            )

    def validate_historical_coverage(
        self, data_sources: Dict[str, pd.DataFrame], required_seasons: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate historical data coverage across multiple sources.

        Parameters
        ----------
        data_sources : Dict[str, pd.DataFrame]
            Dictionary mapping source names to their data
        required_seasons : List[str], optional
            List of seasons that should be covered

        Returns
        -------
        Dict[str, Any]
            Coverage analysis report
        """
        self.reset_report()

        if not data_sources:
            self._add_error("No data sources provided for coverage validation")
            return self.validation_report

        coverage_report: Dict[str, Any] = {
            "sources": {},
            "season_coverage": {},
            "competition_coverage": {},
            "data_gaps": [],
            "overlaps": [],
        }

        # Analyze each source
        for source_name, df in data_sources.items():
            if df.empty:
                self._add_warning(f"Empty data from source: {source_name}")
                continue

            source_info = {
                "matches": len(df),
                "date_range": None,
                "seasons": set(),
                "competitions": set(),
            }

            if "date" in df.columns and not df["date"].empty:
                valid_dates = pd.to_datetime(df["date"], errors="coerce").dropna()
                if not valid_dates.empty:
                    source_info["date_range"] = (valid_dates.min(), valid_dates.max())

            if "season" in df.columns:
                source_info["seasons"] = set(df["season"].dropna().unique())

            if "competition" in df.columns:
                source_info["competitions"] = set(df["competition"].dropna().unique())

            coverage_report["sources"][source_name] = source_info

        # Check required seasons coverage
        if required_seasons:
            all_seasons = set()
            for info in coverage_report["sources"].values():
                all_seasons.update(info["seasons"])

            missing_seasons = set(required_seasons) - all_seasons
            if missing_seasons:
                self._add_warning(f"Missing required seasons: {missing_seasons}")

            coverage_report["season_coverage"] = {
                "required": set(required_seasons),
                "available": all_seasons,
                "missing": missing_seasons,
                "coverage_rate": len(all_seasons & set(required_seasons))
                / len(required_seasons),
            }

        self.validation_report["coverage_analysis"] = coverage_report
        return self.validation_report

    def cross_validate_sources(
        self,
        source1: pd.DataFrame,
        source2: pd.DataFrame,
        source1_name: str = "Source1",
        source2_name: str = "Source2",
    ) -> Dict[str, Any]:
        """
        Cross-validate data between two sources to identify discrepancies.

        Parameters
        ----------
        source1, source2 : pd.DataFrame
            DataFrames to compare
        source1_name, source2_name : str
            Names for the sources

        Returns
        -------
        Dict[str, Any]
            Cross-validation report
        """
        self.reset_report()

        if source1.empty or source2.empty:
            self._add_error("Cannot cross-validate empty sources")
            return self.validation_report

        # Common columns for comparison
        common_cols = ["team_home", "team_away", "goals_home", "goals_away"]

        if not all(
            col in source1.columns and col in source2.columns for col in common_cols
        ):
            self._add_error("Sources missing required columns for cross-validation")
            return self.validation_report

        # Try to merge on team names and date if available
        merge_cols = ["team_home", "team_away"]
        if "date" in source1.columns and "date" in source2.columns:
            merge_cols.append("date")

        try:
            merged = source1.merge(
                source2, on=merge_cols, how="inner", suffixes=("_s1", "_s2")
            )

            if merged.empty:
                self._add_warning(
                    f"No common matches found between {source1_name} and {source2_name}"
                )
                return self.validation_report

            self._add_info(f"Found {len(merged)} common matches for comparison")

            # Compare goals
            goal_mismatches = (merged["goals_home_s1"] != merged["goals_home_s2"]) | (
                merged["goals_away_s1"] != merged["goals_away_s2"]
            )

            if goal_mismatches.any():
                count = goal_mismatches.sum()
                mismatch_rate = count / len(merged)
                self._add_warning(
                    f"Goal mismatches between sources: {count}/{len(merged)} "
                    f"({mismatch_rate:.1%})"
                )

            self.validation_report["cross_validation"] = {
                "common_matches": len(merged),
                "goal_mismatches": goal_mismatches.sum(),
                "mismatch_rate": (
                    goal_mismatches.sum() / len(merged) if len(merged) > 0 else 0
                ),
            }

        except Exception as e:
            self._add_error(f"Error during cross-validation: {e}")

        return self.validation_report

    def generate_summary_report(self) -> str:
        """Generate a human-readable summary of the validation report."""
        report_lines = []

        if self.validation_report["errors"]:
            report_lines.append("🚨 ERRORS FOUND:")
            for error in self.validation_report["errors"]:
                report_lines.append(f"  ❌ {error}")
            report_lines.append("")

        if self.validation_report["warnings"]:
            report_lines.append("⚠️  WARNINGS:")
            for warning in self.validation_report["warnings"]:
                report_lines.append(f"  ⚠️  {warning}")
            report_lines.append("")

        if self.validation_report["info"]:
            report_lines.append("ℹ️  INFORMATION:")
            for info in self.validation_report["info"]:
                report_lines.append(f"  ℹ️  {info}")
            report_lines.append("")

        # Summary
        error_count = len(self.validation_report["errors"])
        warning_count = len(self.validation_report["warnings"])

        if error_count == 0 and warning_count == 0:
            report_lines.append("✅ DATA VALIDATION PASSED - No issues found")
        elif error_count == 0:
            report_lines.append(f"✅ DATA VALIDATION PASSED - {warning_count} warnings")
        else:
            report_lines.append(
                f"❌ DATA VALIDATION FAILED - {error_count} errors, {warning_count} warnings"
            )

        return "\n".join(report_lines)


# Convenience functions
def validate_fixtures(
    df: pd.DataFrame, competition: str = "", season: str = "", strict_mode: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to validate fixtures data.

    Parameters
    ----------
    df : pd.DataFrame
        Fixtures dataframe to validate
    competition : str
        Competition name for context
    season : str
        Season for context
    strict_mode : bool
        If True, raise exceptions for warnings

    Returns
    -------
    Dict[str, Any]
        Validation report
    """
    validator = DataQualityValidator(strict_mode=strict_mode)
    return validator.validate_fixtures_data(df, competition, season)


def cross_validate_sources(
    source1: pd.DataFrame,
    source2: pd.DataFrame,
    source1_name: str = "Source1",
    source2_name: str = "Source2",
    strict_mode: bool = False,
) -> Dict[str, Any]:
    """
    Convenience function to cross-validate data sources.

    Parameters
    ----------
    source1, source2 : pd.DataFrame
        DataFrames to compare
    source1_name, source2_name : str
        Names for the sources
    strict_mode : bool
        If True, raise exceptions for warnings

    Returns
    -------
    Dict[str, Any]
        Cross-validation report
    """
    validator = DataQualityValidator(strict_mode=strict_mode)
    return validator.cross_validate_sources(
        source1, source2, source1_name, source2_name
    )
