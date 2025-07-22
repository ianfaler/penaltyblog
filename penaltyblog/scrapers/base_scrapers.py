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
        Perform HTTP GET request with robust error handling and real connection validation

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
            If request fails after all retries or if response indicates fake data
        """
        if delay > 0:
            time.sleep(delay)

        last_exception = None
        
        # Retry mechanism with exponential backoff
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying request to {url} (attempt {attempt + 1}/{self.max_retries + 1}) after {wait_time}s")
                    time.sleep(wait_time)
                
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

                # Additional validation for empty responses
                if not response.text or len(response.text.strip()) == 0:
                    raise RequestException(f"Empty response received from {url}")

                # Validate that we got real data, not a placeholder/error page
                if not self.validate_response_data(response.text, url):
                    raise RequestException(f"Response validation failed for {url}")

                logger.info(f"Successfully fetched data from: {url}")
                return response.text

            except Timeout as e:
                last_exception = RequestException(f"Request timed out after {self.timeout}s: {url}")
                logger.error(f"Timeout error for {url} (attempt {attempt + 1}): {e}")

            except ConnectionError as e:
                last_exception = RequestException(f"Connection failed: {url}")
                logger.error(f"Connection error for {url} (attempt {attempt + 1}): {e}")

            except HTTPError as e:
                # Don't retry certain HTTP errors
                if e.response.status_code in [400, 401, 403, 404, 410]:
                    if e.response.status_code == 404:
                        raise RequestException(f"Data not found (404): {url}") from e
                    elif e.response.status_code == 403:
                        raise RequestException(f"Access denied (403): {url}") from e
                    else:
                        raise RequestException(f"HTTP error {e.response.status_code}: {url}") from e
                else:
                    # Retry for server errors (5xx) and rate limiting (429)
                    last_exception = RequestException(f"HTTP error {e.response.status_code}: {url}")
                    logger.error(f"HTTP error for {url} (attempt {attempt + 1}): {e}")

            except RequestException as e:
                last_exception = e
                logger.error(f"Request exception for {url} (attempt {attempt + 1}): {e}")

            except Exception as e:
                last_exception = RequestException(f"Unexpected error: {url}")
                logger.error(f"Unexpected error for {url} (attempt {attempt + 1}): {e}")

        # If we get here, all retries failed
        logger.error(f"All {self.max_retries + 1} attempts failed for {url}")
        raise last_exception or RequestException(f"Request failed after {self.max_retries + 1} attempts: {url}")

    def validate_response_data(self, data: str, url: str) -> bool:
        """
        Validate that response data is not empty or malformed and appears to be real data

        Parameters
        ----------
        data : str
            Response data to validate
        url : str
            URL that was fetched (for logging)

        Returns
        -------
        bool
            True if data appears valid and real
        """
        if not data or len(data.strip()) == 0:
            logger.warning(f"Empty response from {url}")
            return False

        # Check for common error indicators
        error_indicators = [
            "404", "not found", "page not found",
            "access denied", "forbidden", "403 forbidden",
            "500 internal server error", "502 bad gateway",
            "503 service unavailable", "504 gateway timeout",
            "error", "exception", "invalid",
            "maintenance", "temporarily unavailable",
            "rate limit", "too many requests",
            "captcha", "blocked", "bot detection"
        ]
        
        data_lower = data.lower()
        for indicator in error_indicators:
            if indicator in data_lower:
                logger.warning(f"Error indicator '{indicator}' detected in response from {url}")
                return False

        # Check for minimum data size (real data should be substantial)
        if len(data) < 50:
            logger.warning(f"Response too small ({len(data)} chars) from {url}")
            return False

        # For HTML responses, check for actual content
        if "<html" in data_lower or "<!doctype html" in data_lower:
            # Should contain actual data tables or content, not just error pages
            content_indicators = [
                "<table", "<tbody", "<tr", "<td", 
                "fixtures", "results", "matches", "schedule",
                "data-", "json", "api", "calendar"
            ]
            has_content = any(indicator in data_lower for indicator in content_indicators)
            if not has_content:
                logger.warning(f"HTML response from {url} appears to lack actual data content")
                return False
            
            # Check for common "no data" messages
            no_data_indicators = [
                "no fixtures", "no matches", "no results",
                "no data available", "coming soon",
                "check back later", "no games scheduled"
            ]
            for indicator in no_data_indicators:
                if indicator in data_lower:
                    logger.warning(f"'No data' indicator '{indicator}' found in response from {url}")
                    return False

        # For CSV responses, check for data rows
        elif "," in data and ("\n" in data or "\r" in data):
            lines = data.strip().split('\n')
            if len(lines) < 2:  # Should have at least header + 1 data row
                logger.warning(f"CSV response from {url} has insufficient data rows")
                return False
            
            # Check that we have actual data columns
            first_line = lines[0]
            if len(first_line.split(',')) < 3:
                logger.warning(f"CSV response from {url} has too few columns")
                return False

        # Check for JSON responses
        elif data.strip().startswith('{') or data.strip().startswith('['):
            import json
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict) and len(parsed) == 0:
                    logger.warning(f"JSON response from {url} is empty object")
                    return False
                elif isinstance(parsed, list) and len(parsed) == 0:
                    logger.warning(f"JSON response from {url} is empty array")
                    return False
                    
                # Check for error fields in JSON
                if isinstance(parsed, dict):
                    error_fields = ['error', 'status', 'message']
                    for field in error_fields:
                        if field in parsed and parsed[field]:
                            error_value = str(parsed[field]).lower()
                            if any(err in error_value for err in ['error', 'fail', 'invalid', 'not found']):
                                logger.warning(f"JSON error field '{field}': {parsed[field]} in response from {url}")
                                return False
                                
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON response from {url}")
                return False

        # Additional validation for API endpoints
        if "api" in url.lower():
            # API responses should be structured (JSON/XML) or have substantial data
            if not (data.strip().startswith(('{', '[', '<')) or len(data) > 200):
                logger.warning(f"API response from {url} appears malformed or too small")
                return False

        logger.debug(f"Response validation passed for {url} ({len(data)} chars)")
        return True
