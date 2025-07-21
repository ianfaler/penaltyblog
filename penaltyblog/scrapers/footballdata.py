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


class FootballData(RequestsScraper):
    """
    Scrapes data from football-data.co.uk as pandas dataframes

    Parameters
    ----------
    competition : str
        Name of the league of interest. See the
        `FootballData.list_competitions()` function
        for available competitions

    season : str
        Name of the season of interest in format 2020-2021

    team_mappings : dict or None
        dict (or None) of team name mappings in format
        `{
            "Manchester United: ["Man Utd", "Man United],
        }`

    """

    source = "footballdata"

    def __init__(self, competition, season, team_mappings=None):

        self._check_competition(competition)

        self.base_url = (
            "https://www.football-data.co.uk/mmz4281/{season}/{competition}.csv"
        )
        self.competition = competition
        self.season = season
        self.mapped_season = self._season_mapping(self.season)
        self.mapped_competition = COMPETITION_MAPPINGS[self.competition][
            "footballdata"
        ]["slug"]

        super().__init__(team_mappings=team_mappings)

    def _season_mapping(self, season):
        """
        Internal function to map season to football-data's format
        """
        try:
            years = season.split("-")
            if len(years) != 2:
                raise ValueError(f"Season format should be YYYY-YYYY, got: {season}")

            part1 = years[0][-2:]
            part2 = years[1][-2:]
            mapped = part1 + part2
            return mapped
        except Exception as e:
            logger.error(f"Error mapping season {season}: {e}")
            raise ValueError(f"Invalid season format: {season}") from e

    def _convert_date(self, df):
        """
        Convert date columns with robust error handling for NaT prevention
        """
        if df.empty:
            logger.warning("Empty dataframe provided to _convert_date")
            return df

        # Remove any completely empty rows
        df = df.dropna(how="all")

        if df.empty or "Date" not in df.columns:
            logger.warning("No Date column found or dataframe is empty after cleaning")
            return df

        # Filter out rows with null/empty dates
        date_mask = df["Date"].notna() & (df["Date"] != "") & (df["Date"] != "Date")
        df = df[date_mask]

        if df.empty:
            logger.warning("No valid dates found in dataframe")
            return df

        try:
            # Check for date format - could be either %d/%m/%Y or %d/%m/%y
            sample_date = str(df["Date"].iloc[0]).strip()

            if not sample_date or sample_date.lower() == "nan":
                logger.warning("First date value is empty or NaN")
                return df

            # Determine date format based on sample
            date_format = "%d/%m/%y" if len(sample_date) <= 8 else "%d/%m/%Y"
            logger.info(
                f"Using date format: {date_format} for sample date: {sample_date}"
            )

            # Convert datetime column if Time exists
            if "Time" in df.columns:
                time_mask = df["Time"].notna() & (df["Time"] != "")
                valid_time_df = df[time_mask].copy()

                if not valid_time_df.empty:
                    time_format = date_format + " %H:%M"
                    valid_time_df["datetime"] = pd.to_datetime(
                        valid_time_df["Date"].astype(str)
                        + " "
                        + valid_time_df["Time"].astype(str),
                        format=time_format,
                        errors="coerce",
                    )
                    # Merge back the datetime column
                    df = df.merge(
                        valid_time_df[["datetime"]],
                        left_index=True,
                        right_index=True,
                        how="left",
                    )

            # Convert Date column with robust error handling
            df["Date"] = pd.to_datetime(
                df["Date"].astype(str), format=date_format, errors="coerce"
            )

            # Remove rows where date conversion failed
            df = df.dropna(subset=["Date"])

            if df.empty:
                logger.warning("No valid dates remain after conversion")
            else:
                logger.info(f"Successfully converted {len(df)} rows with valid dates")

        except Exception as e:
            logger.error(f"Error in date conversion: {e}")
            # Return dataframe with original date column if conversion fails
            logger.warning(
                "Falling back to original date column due to conversion error"
            )

        return df

    def _validate_fixtures_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate fixtures data for completeness and consistency
        """
        if df.empty:
            logger.warning("Empty fixtures dataframe")
            return df

        required_columns = ["team_home", "team_away", "fthg", "ftag"]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            raise ValueError(
                f"Missing required columns in fixtures data: {missing_columns}"
            )

        # Check for invalid scores (negative values, non-numeric)
        for col in ["fthg", "ftag"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            invalid_scores = df[col].isna() | (df[col] < 0)
            if invalid_scores.any():
                logger.warning(f"Found {invalid_scores.sum()} invalid scores in {col}")
                df = df[~invalid_scores]

        # Check for missing team names
        team_cols = ["team_home", "team_away"]
        for col in team_cols:
            empty_teams = df[col].isna() | (df[col] == "")
            if empty_teams.any():
                logger.warning(f"Found {empty_teams.sum()} empty team names in {col}")
                df = df[~empty_teams]

        logger.info(f"Validated fixtures data: {len(df)} valid rows remaining")
        return df

    def get_fixtures(self) -> pd.DataFrame:
        """
        Downloads the fixtures and returns them as a pandas data frame with robust error handling
        """
        url = self.base_url.format(
            season=self.mapped_season, competition=self.mapped_competition
        )

        col_renames = {
            "HomeTeam": "team_home",
            "AwayTeam": "team_away",
        }

        try:
            logger.info(f"Fetching fixtures for {self.competition} {self.season}")
            content = self.get(url)

            if not self.validate_response_data(content, url):
                raise ValueError(f"Invalid response data from {url}")

            # Read CSV with error handling for malformed data
            try:
                raw_df = pd.read_csv(io.StringIO(content))
            except pd.errors.EmptyDataError:
                logger.error(f"Empty CSV data from {url}")
                raise ValueError(
                    f"No data available for {self.competition} {self.season}"
                )
            except pd.errors.ParserError as e:
                logger.error(f"CSV parsing error from {url}: {e}")
                raise ValueError(f"Malformed CSV data from {url}") from e

            if raw_df.empty:
                logger.warning(f"Empty dataframe from {url}")
                return pd.DataFrame()

            logger.info(f"Raw data shape: {raw_df.shape}")

            # Process data with validation at each step
            df = (
                raw_df.pipe(self._convert_date)
                .rename(columns=col_renames)
                .pipe(self._validate_fixtures_data)
                .pipe(sanitize_columns)
                .assign(season=self.season)
                .assign(competition=self.competition)
                .assign(goals_home=lambda x: x["fthg"])
                .assign(goals_away=lambda x: x["ftag"])
                .pipe(self._map_teams, columns=["team_home", "team_away"])
                .dropna(subset=["date"])  # Final cleanup of any remaining NaT dates
                .pipe(create_game_id)
                .set_index(["id"])
                .sort_index()
            )

            # Reorder columns
            cols = ["competition", "season", "datetime", "date"]
            i = 0
            for c in cols:
                if c in df.columns:
                    move_column_inplace(df, c, i)
                    i += 1  # Fixed increment bug

            logger.info(f"Successfully processed {len(df)} fixtures")
            return df

        except Exception as e:
            logger.error(
                f"Error fetching fixtures for {self.competition} {self.season}: {e}"
            )
            raise
