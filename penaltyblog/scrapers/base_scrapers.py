import logging
import time
from typing import Iterable

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError, HTTPError, RequestException, Timeout
from urllib3.util.retry import Retry

from .common import COMPETITION_MAPPINGS

# Set up logging
logger = logging.getLogger(__name__)


class BaseScraper:
    """
    Base scraper that all scrapers inherit from

    Parameters
    ----------
    team_mappings : dict or None
        dict (or None) of team name mappings in format
        `{
            "Manchester United: ["Man Utd", "Man United],
        }`
    """

    src: str = ""

    def __init__(self, team_mappings=None):
        if team_mappings is not None:
            self.team_mappings = dict()
            for team, options in team_mappings.items():
                for option in options:
                    self.team_mappings[option] = team
        else:
            self.team_mappings = None

    def _check_competition(self, competition):
        available = self.list_competitions()
        if competition not in available:
            raise ValueError(
                f"{competition} not available for this data source. Available: {available}"
            )

    @classmethod
    def list_competitions(cls) -> list:
        if not hasattr(cls, "source"):
            raise AttributeError(f"{cls.__name__} has no attribute 'source'")
        competitions = list()
        for k, v in COMPETITION_MAPPINGS.items():
            if cls.source in v.keys():
                competitions.append(k)
        return competitions

    def _map_teams(self, df: pd.DataFrame, columns: Iterable) -> pd.DataFrame:
        """
        Internal function to apply team mappings if they've been provided

        Parameters
        ----------
        df : pd.DataFrame
            dataframe of scraped data

        columns : Iterable
            iterable of columns to map
        """
        if self.team_mappings is not None:
            for c in columns:
                if c in df.columns:
                    df[c] = df[c].replace(self.team_mappings)
                else:
                    logger.warning(
                        f"Column {c} not found in dataframe for team mapping"
                    )
        return df


class RequestsScraper(BaseScraper):
    """
    Base scraper that all request-based scrapers inherit from with robust error handling
    """

    def __init__(self, team_mappings=None, timeout=30, max_retries=3):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/102.0.0.0 Safari/537.36"
            )
        }

        self.cookies = None
        self.timeout = timeout
        self.max_retries = max_retries

        # Set up session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        super().__init__(team_mappings=team_mappings)

    def get(self, url: str, delay: float = 1.0) -> str:
        """
        Perform HTTP GET request with robust error handling

        Parameters
        ----------
        url : str
            URL to fetch
        delay : float
            Delay in seconds before making request (for rate limiting)

        Returns
        -------
        str
            Response text

        Raises
        ------
        RequestException
            If request fails after all retries
        """
        if delay > 0:
            time.sleep(delay)

        try:
            logger.info(f"Fetching data from: {url}")

            if self.cookies is not None:
                response = self.session.get(
                    url,
                    headers=self.headers,
                    cookies=self.cookies,
                    timeout=self.timeout,
                )
            else:
                response = self.session.get(
                    url, headers=self.headers, timeout=self.timeout
                )

            response.raise_for_status()  # Raises HTTPError for bad responses

            logger.info(f"Successfully fetched data from: {url}")
            return response.text

        except Timeout as e:
            logger.error(f"Timeout error for {url}: {e}")
            raise RequestException(
                f"Request timed out after {self.timeout}s: {url}"
            ) from e

        except ConnectionError as e:
            logger.error(f"Connection error for {url}: {e}")
            raise RequestException(f"Connection failed: {url}") from e

        except HTTPError as e:
            logger.error(f"HTTP error for {url}: {e}")
            raise RequestException(f"HTTP error {e.response.status_code}: {url}") from e

        except RequestException as e:
            logger.error(f"Request exception for {url}: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error for {url}: {e}")
            raise RequestException(f"Unexpected error: {url}") from e

    def validate_response_data(self, data: str, url: str) -> bool:
        """
        Validate that response data is not empty or malformed

        Parameters
        ----------
        data : str
            Response data to validate
        url : str
            URL that was fetched (for logging)

        Returns
        -------
        bool
            True if data appears valid
        """
        if not data or len(data.strip()) == 0:
            logger.warning(f"Empty response from {url}")
            return False

        if "404" in data or "Not Found" in data:
            logger.warning(f"404 error content detected from {url}")
            return False

        if "Access Denied" in data or "Forbidden" in data:
            logger.warning(f"Access denied content detected from {url}")
            return False

        return True
