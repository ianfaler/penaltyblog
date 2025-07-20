import io
import logging

import pandas as pd

from .base_scrapers import RequestsScraper
from .common import (
    COMPETITION_MAPPINGS,
    create_game_id,
    move_column_inplace,
    sanitize_columns,
)

logger = logging.getLogger(__name__)


class FBRef(RequestsScraper):
    """
    Scrapes data from FBRef and returns as a pandas dataframes

    Parameters
    ----------
    league : str
        Name of the league of interest,
        see the `FBRef.list_competitions()` output for available choices

    season : str
        Name of the season of interest in format 2020-2021

    team_mappings : dict or None
        dict (or None) of team name mappings in format
        `{
            "Manchester United: ["Man Utd", "Man United],
        }`
    """

    source = "fbref"

    def __init__(self, competition, season, team_mappings=None):
        self._check_competition(competition)

        self.base_url = "https://fbref.com/en/comps/"
        self.competition = competition
        self.season = season
        self.mapped_season = self._map_season(self.season)
        self.mapped_competition = COMPETITION_MAPPINGS[self.competition]["fbref"][
            "slug"
        ]

        super().__init__(team_mappings=team_mappings)

    def _map_season(self, season) -> str:
        """
        Internal function to map the season name

        Parameters
        ----------
        season : str
            Name of the season
        """
        try:
            # Validate season format
            if not season or '-' not in season:
                raise ValueError(f"Invalid season format: {season}")
            
            years = season.split('-')
            if len(years) != 2:
                raise ValueError(f"Season must be in format YYYY-YYYY, got: {season}")
            
            # Basic validation of years
            start_year, end_year = map(int, years)
            if end_year != start_year + 1:
                logger.warning(f"Unusual season span: {season}")
            
            return season
        except Exception as e:
            logger.error(f"Error mapping season {season}: {e}")
            raise ValueError(f"Invalid season format: {season}") from e

    def _convert_date(self, df):
        """Convert date columns with improved error handling."""
        if df.empty:
            logger.warning("Empty dataframe provided to _convert_date")
            return df
        
        try:
            if 'date' in df.columns and 'time' in df.columns:
                # Combine date and time columns
                datetime_strs = df["date"].astype(str) + " " + df["time"].astype(str)
                df["datetime"] = pd.to_datetime(datetime_strs, errors="coerce")
                
                # Count conversion failures
                failed_conversions = df["datetime"].isna() & df["date"].notna()
                if failed_conversions.any():
                    logger.warning(f"Failed to convert {failed_conversions.sum()} datetime values")
            
            if 'date' in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                
                # Remove rows with invalid dates
                invalid_dates = df["date"].isna()
                if invalid_dates.any():
                    logger.warning(f"Removing {invalid_dates.sum()} rows with invalid dates")
                    df = df[~invalid_dates]
        
        except Exception as e:
            logger.error(f"Error in date conversion: {e}")
            # Continue without date conversion if it fails
        
        return df

    def _rename_fixture_columns(self, df) -> pd.DataFrame:
        """
        Internal function to rename columns to make consistent with other data sources
        """
        cols = {
            "Wk": "week",
            "Home": "team_home",
            "Away": "team_away",
            "xG": "xg_home",
            "xG.1": "xg_away",
        }
        
        # Only rename columns that exist
        existing_cols = {k: v for k, v in cols.items() if k in df.columns}
        if not existing_cols:
            logger.warning("No expected columns found for renaming")
        
        df = df.rename(columns=existing_cols)
        return df

    def _drop_fixture_spacer_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Internal function to drop the spacer rows from the fixtures df
        """
        if 'week' not in df.columns:
            logger.warning("No 'week' column found for filtering spacer rows")
            return df
        
        initial_count = len(df)
        df = df[~df["week"].isna()]
        removed_count = initial_count - len(df)
        
        if removed_count > 0:
            logger.info(f"Removed {removed_count} spacer rows")
        
        return df

    def _drop_unplayed_fixtures(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Internal function to drop unplayed fixtures from the fixtures df
        """
        if 'xg_home' not in df.columns:
            logger.warning("No 'xg_home' column found for filtering unplayed fixtures")
            return df
        
        initial_count = len(df)
        df = df[~df["xg_home"].isna()]
        removed_count = initial_count - len(df)
        
        if removed_count > 0:
            logger.info(f"Removed {removed_count} unplayed fixtures")
        
        return df

    def _split_score(self, df) -> pd.DataFrame:
        """
        Internal function to split the score column into goals_home and goals_away
        """
        if 'score' not in df.columns:
            logger.warning("No 'score' column found for splitting")
            return df
        
        try:
            # Handle different score formats
            score_parts = df["score"].str.split("–", expand=True)
            
            if score_parts.shape[1] < 2:
                # Try alternative separators
                score_parts = df["score"].str.split("-", expand=True)
            
            if score_parts.shape[1] >= 2:
                df["goals_home"] = pd.to_numeric(score_parts[0], errors="coerce")
                df["goals_away"] = pd.to_numeric(score_parts[1], errors="coerce")
                
                # Validate goal values
                invalid_goals = (df["goals_home"].isna() | df["goals_away"].isna()) & df["score"].notna()
                if invalid_goals.any():
                    logger.warning(f"Failed to parse {invalid_goals.sum()} score values")
            else:
                logger.warning("Could not split score column - unexpected format")
        
        except Exception as e:
            logger.error(f"Error splitting score column: {e}")
        
        return df

    def _validate_fixtures_response(self, content: str, url: str) -> bool:
        """Validate that the fixtures response contains expected data."""
        if not self.validate_response_data(content, url):
            return False
        
        # Check for FBRef-specific content
        required_indicators = ["fixtures", "scores", "table"]
        found_indicators = sum(1 for indicator in required_indicators if indicator.lower() in content.lower())
        
        if found_indicators == 0:
            logger.warning(f"Response from {url} doesn't appear to contain fixtures data")
            return False
        
        return True

    def get_fixtures(self) -> pd.DataFrame:
        """Get fixtures data with comprehensive error handling."""
        url = (
            self.base_url
            + self.mapped_competition
            + "/"
            + self.mapped_season
            + "/schedule/"
        )

        try:
            logger.info(f"Fetching fixtures for {self.competition} {self.season}")
            content = self.get(url)
            
            if not self._validate_fixtures_response(content, url):
                raise ValueError(f"Invalid fixtures response from {url}")

            # Remove HTML comments that interfere with parsing
            content = content.replace("<!--", "").replace("-->", "")

            # Parse HTML tables
            try:
                dfs = pd.read_html(io.StringIO(content))
            except ValueError as e:
                logger.error(f"No tables found in response from {url}")
                raise ValueError(f"No fixtures data found for {self.competition} {self.season}") from e
            
            if not dfs:
                raise ValueError(f"No tables found in fixtures page for {self.competition} {self.season}")
            
            # Use the first table (fixtures table)
            raw_df = dfs[0]
            logger.info(f"Raw fixtures data shape: {raw_df.shape}")
            
            if raw_df.empty:
                logger.warning(f"Empty fixtures table for {self.competition} {self.season}")
                return pd.DataFrame()

            # Process the data pipeline
            df = (
                raw_df
                .pipe(self._rename_fixture_columns)
                .pipe(self._drop_fixture_spacer_rows)
                .pipe(self._drop_unplayed_fixtures)
                .pipe(self._convert_date)
                .pipe(self._split_score)
                .pipe(sanitize_columns)
                .assign(season=self.season)
                .assign(competition=self.competition)
                .pipe(self._map_teams, columns=["team_home", "team_away"])
                .dropna(subset=["goals_home", "goals_away"])  # Remove unparsed matches
                .pipe(create_game_id)
                .set_index(["id"])
                .sort_index()
            )

            # Move important columns to front
            important_cols = ["competition", "season", "datetime", "date"]
            for i, col in enumerate(important_cols):
                if col in df.columns:
                    move_column_inplace(df, col, i)

            logger.info(f"Successfully processed {len(df)} fixtures")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching fixtures for {self.competition} {self.season}: {e}")
            raise

    def _flatten_stats_col_names(self, df):
        """Flatten multi-level column names."""
        if isinstance(df.columns, pd.MultiIndex):
            # Flatten multi-level columns
            df.columns = ['_'.join(col).strip() for col in df.columns.values]
            # Clean up column names
            df.columns = [col.replace('__', '_').strip('_') for col in df.columns]
        
        return df

    def _set_stat_col_types(self, df):
        """Set appropriate data types for statistical columns."""
        try:
            # Numeric columns that should be converted
            numeric_patterns = ['goals', 'assists', 'shots', 'passes', 'tackles', 'cards', 'minutes', 'xg', 'xa']
            
            for col in df.columns:
                col_lower = col.lower()
                if any(pattern in col_lower for pattern in numeric_patterns):
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
        except Exception as e:
            logger.warning(f"Error setting column types: {e}")
        
        return df

    def _player_ages(self, df):
        """Process player age information."""
        if 'age' in df.columns:
            try:
                # Extract numeric age from age column (might be in format "23-123")
                df['age_years'] = df['age'].str.split('-').str[0]
                df['age_years'] = pd.to_numeric(df['age_years'], errors='coerce')
            except Exception as e:
                logger.warning(f"Error processing player ages: {e}")
        
        return df

    def list_stat_types(self) -> list:
        """
        Returns the stat types available to the .get_stats() function
        """
        competition_info = COMPETITION_MAPPINGS.get(self.competition, {}).get("fbref", {})
        stats = competition_info.get("stats", [])
        
        if not stats:
            logger.warning(f"No stat types found for {self.competition}")
        
        return stats

    def get_stats(self, stat_type: str) -> dict:
        """
        Downloads the stats data and returns a dictionary containing the stats for
        `squad_for`, `squad_against` and `players` stats
        """
        available_stats = self.list_stat_types()
        if stat_type not in available_stats:
            raise ValueError(
                f"Stat type '{stat_type}' not available for {self.competition}. "
                f"Available types: {available_stats}"
            )

        # Map stat type to URL path
        stat_page_mapping = {
            "standard": "stats",
            "goalkeeping": "keepers",
            "advanced_goalkeeping": "keepersadv",
            "goal_shot_creation": "gca",
            "defensive_actions": "defense",
            "playing_time": "playingtime",
        }
        
        page = stat_page_mapping.get(stat_type, stat_type)

        url = (
            self.base_url
            + self.mapped_competition
            + "/"
            + self.mapped_season
            + "/"
            + page
            + "/"
        )

        try:
            logger.info(f"Fetching {stat_type} stats for {self.competition} {self.season}")
            content = self.get(url)
            
            if not self.validate_response_data(content, url):
                raise ValueError(f"Invalid stats response from {url}")
            
            # Remove HTML comments
            content = content.replace("<!--", "").replace("-->", "")

            try:
                dfs = pd.read_html(io.StringIO(content))
            except ValueError as e:
                logger.error(f"No tables found in stats response from {url}")
                raise ValueError(f"No {stat_type} stats found for {self.competition} {self.season}") from e
            
            if len(dfs) < 3:
                raise ValueError(f"Expected 3 tables for {stat_type} stats, found {len(dfs)}")

            output = dict()

            # Process squad stats (for)
            output["squad_for"] = (
                dfs[0]
                .pipe(self._flatten_stats_col_names)
                .pipe(sanitize_columns)
                .assign(season=self.season)
                .assign(competition=self.competition)
                .pipe(self._set_stat_col_types)
                .set_index("squad")
                .sort_index()
            )

            # Process squad stats (against)
            output["squad_against"] = (
                dfs[1]
                .pipe(self._flatten_stats_col_names)
                .pipe(sanitize_columns)
                .assign(season=self.season)
                .assign(competition=self.competition)
                .pipe(self._set_stat_col_types)
                .set_index("squad")
                .sort_index()
            )

            # Process player stats
            player_df = dfs[2].copy()
            
            # Remove header rows that sometimes appear in player data
            if 'rk' in player_df.columns:
                player_df = player_df.query("rk != 'Rk'").copy()
                
            # Drop unnecessary columns
            cols_to_drop = ['rk', 'matches']
            cols_to_drop = [col for col in cols_to_drop if col in player_df.columns]
            if cols_to_drop:
                player_df = player_df.drop(cols_to_drop, axis=1)

            output["players"] = (
                player_df
                .pipe(self._flatten_stats_col_names)
                .pipe(sanitize_columns)
                .assign(season=self.season)
                .assign(competition=self.competition)
                .pipe(self._set_stat_col_types)
                .pipe(self._player_ages)
                .set_index("player")
                .sort_index()
            )

            # Validate output
            for key, df in output.items():
                if df.empty:
                    logger.warning(f"Empty {key} dataframe for {stat_type} stats")
                else:
                    logger.info(f"Successfully processed {len(df)} {key} records")

            return output
            
        except Exception as e:
            logger.error(f"Error fetching {stat_type} stats for {self.competition} {self.season}: {e}")
            raise
