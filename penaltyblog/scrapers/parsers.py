"""HTML parsing utilities for converting scraped data to standardized DataFrames."""

import pandas as pd
import re
import json
from typing import Dict, List, Optional, Union
from bs4 import BeautifulSoup
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class DataFormatParser:
    """Parser for different data formats (HTML, JSON, API responses)."""
    
    def __init__(self):
        """Initialize parser with robust session configuration."""
        self.session = requests.Session()
        
        # Configure retry strategy for network failures
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set reasonable timeouts and headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def parse_data(self, url_or_data: str, league_code: str = None, data_format: str = 'auto') -> pd.DataFrame:
        """
        Parse data from URL or raw data string in different formats.
        
        Parameters
        ----------
        url_or_data : str
            URL to fetch data from or raw data string
        league_code : str, optional
            League code for league-specific parsing logic
        data_format : str, default 'auto'
            Expected data format: 'html', 'json', 'api', or 'auto' for auto-detection
            
        Returns
        -------
        pd.DataFrame
            Standardized DataFrame with match data
        """
        try:
            # Check if input is a URL or raw data
            if url_or_data.startswith(('http://', 'https://')):
                data = self._fetch_data_with_error_handling(url_or_data)
                if data is None:
                    return create_empty_fixture_dataframe()
            else:
                data = url_or_data
            
            # Auto-detect format if not specified
            if data_format == 'auto':
                data_format = self._detect_data_format(data)
            
            # Parse based on detected/specified format
            if data_format == 'json' or data_format == 'api':
                return self._parse_json_data(data, league_code)
            else:  # Default to HTML parsing
                return self._parse_html_data(data, league_code)
                
        except Exception as e:
            logger.error(f"Failed to parse data for {league_code}: {str(e)}")
            return create_empty_fixture_dataframe()
    
    def _fetch_data_with_error_handling(self, url: str) -> Optional[str]:
        """
        Fetch data from URL with comprehensive error handling.
        
        Parameters
        ----------
        url : str
            URL to fetch data from
            
        Returns
        -------
        Optional[str]
            Response content or None if failed
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Check if response is empty or invalid
            if not response.content:
                logger.warning(f"Empty response from {url}")
                return None
                
            # Check content type for JSON APIs
            content_type = response.headers.get('content-type', '').lower()
            if 'application/json' in content_type:
                # Validate JSON structure
                try:
                    json.loads(response.text)
                    return response.text
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response from {url}: {e}")
                    return None
            
            return response.text
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching data from {url}")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error while fetching data from {url}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code} while fetching data from {url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error while fetching data from {url}: {str(e)}")
        
        return None
    
    def _detect_data_format(self, data: str) -> str:
        """
        Auto-detect data format from content.
        
        Parameters
        ----------
        data : str
            Raw data content
            
        Returns
        -------
        str
            Detected format: 'json' or 'html'
        """
        data_stripped = data.strip()
        
        # Check if it's JSON
        if data_stripped.startswith(('{', '[')):
            try:
                json.loads(data_stripped)
                return 'json'
            except json.JSONDecodeError:
                pass
        
        # Check if it contains HTML tags
        if '<' in data_stripped and '>' in data_stripped:
            return 'html'
        
        # Default to HTML if uncertain
        return 'html'
    
    def _parse_json_data(self, data: str, league_code: str = None) -> pd.DataFrame:
        """
        Parse JSON/API data into standardized DataFrame.
        
        Parameters
        ----------
        data : str
            JSON data string
        league_code : str, optional
            League code for league-specific parsing
            
        Returns
        -------
        pd.DataFrame
            Standardized match data DataFrame
        """
        try:
            json_data = json.loads(data)
            
            # Handle different JSON structures based on league
            if league_code == 'ENG_PL':
                return self._parse_fpl_api_data(json_data)
            else:
                return self._parse_generic_json_data(json_data, league_code)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON data for {league_code}: {e}")
            return create_empty_fixture_dataframe()
        except Exception as e:
            logger.error(f"Error processing JSON data for {league_code}: {e}")
            return create_empty_fixture_dataframe()
    
    def _parse_fpl_api_data(self, json_data: Union[Dict, List]) -> pd.DataFrame:
        """
        Parse Fantasy Premier League API data.
        
        Parameters
        ----------
        json_data : Union[Dict, List]
            FPL API response data
            
        Returns
        -------
        pd.DataFrame
            Standardized match data DataFrame
        """
        matches = []
        
        try:
            # FPL API returns a list of fixtures
            if isinstance(json_data, list):
                fixtures = json_data
            elif isinstance(json_data, dict) and 'fixtures' in json_data:
                fixtures = json_data['fixtures']
            else:
                logger.warning("Unexpected FPL API data structure")
                return create_empty_fixture_dataframe()
            
            for fixture in fixtures:
                if not isinstance(fixture, dict):
                    continue
                
                # Extract match data from FPL structure
                match_data = {
                    'date': fixture.get('kickoff_time', '').split('T')[0] if fixture.get('kickoff_time') else None,
                    'home': self._get_team_name(fixture.get('team_h')),
                    'away': self._get_team_name(fixture.get('team_a')),
                    'home_score': fixture.get('team_h_score'),
                    'away_score': fixture.get('team_a_score'),
                }
                
                # Only include if we have essential data
                if match_data['home'] and match_data['away']:
                    matches.append(match_data)
            
        except Exception as e:
            logger.error(f"Error parsing FPL API data: {e}")
            return create_empty_fixture_dataframe()
        
        if matches:
            df = pd.DataFrame(matches)
            return normalize_fixture_dataframe(df, 'ENG_PL')
        
        return create_empty_fixture_dataframe()
    
    def _parse_generic_json_data(self, json_data: Union[Dict, List], league_code: str = None) -> pd.DataFrame:
        """
        Parse generic JSON data into standardized DataFrame.
        
        Parameters
        ----------
        json_data : Union[Dict, List]
            Generic JSON data
        league_code : str, optional
            League code for context
            
        Returns
        -------
        pd.DataFrame
            Standardized match data DataFrame
        """
        matches = []
        
        try:
            # Handle different JSON structures
            if isinstance(json_data, list):
                data_items = json_data
            elif isinstance(json_data, dict):
                # Look for common array keys
                for key in ['matches', 'fixtures', 'games', 'results', 'data']:
                    if key in json_data and isinstance(json_data[key], list):
                        data_items = json_data[key]
                        break
                else:
                    data_items = [json_data]  # Single match object
            else:
                return create_empty_fixture_dataframe()
            
            for item in data_items:
                if not isinstance(item, dict):
                    continue
                
                # Extract match data using common field names
                match_data = self._extract_match_from_json_item(item)
                if match_data and match_data.get('home') and match_data.get('away'):
                    matches.append(match_data)
            
        except Exception as e:
            logger.error(f"Error parsing generic JSON data for {league_code}: {e}")
            return create_empty_fixture_dataframe()
        
        if matches:
            df = pd.DataFrame(matches)
            return normalize_fixture_dataframe(df, league_code)
        
        return create_empty_fixture_dataframe()
    
    def _extract_match_from_json_item(self, item: Dict) -> Optional[Dict]:
        """Extract match data from a single JSON item."""
        try:
            # Common field mappings for JSON data
            field_mappings = {
                'date': ['date', 'kickoff_time', 'match_date', 'datetime', 'start_time'],
                'home': ['home', 'home_team', 'team_home', 'homeTeam', 'team_h'],
                'away': ['away', 'away_team', 'team_away', 'awayTeam', 'team_a'],
                'home_score': ['home_score', 'goals_home', 'homeScore', 'team_h_score'],
                'away_score': ['away_score', 'goals_away', 'awayScore', 'team_a_score'],
            }
            
            match_data = {}
            
            for standard_field, possible_fields in field_mappings.items():
                for field in possible_fields:
                    if field in item:
                        value = item[field]
                        # Handle nested team objects
                        if isinstance(value, dict) and 'name' in value:
                            value = value['name']
                        match_data[standard_field] = value
                        break
            
            return match_data
            
        except Exception as e:
            logger.debug(f"Failed to extract match from JSON item: {e}")
            return None
    
    def _parse_html_data(self, data: str, league_code: str = None) -> pd.DataFrame:
        """
        Parse HTML data with enhanced error handling.
        
        Parameters
        ----------
        data : str
            HTML content
        league_code : str, optional
            League code for league-specific parsing
            
        Returns
        -------
        pd.DataFrame
            Standardized match data DataFrame
        """
        try:
            return parse_html_to_dataframe(data, league_code)
        except Exception as e:
            logger.error(f"Failed to parse HTML data for {league_code}: {e}")
            return create_empty_fixture_dataframe()
    
    def _get_team_name(self, team_id: Union[int, str, None]) -> Optional[str]:
        """
        Convert team ID to team name (basic implementation).
        
        Parameters
        ----------
        team_id : Union[int, str, None]
            Team identifier
            
        Returns
        -------
        Optional[str]
            Team name or None if not found
        """
        if team_id is None:
            return None
        
        # Basic FPL team ID mapping (would need to be expanded)
        fpl_teams = {
            1: "Arsenal", 2: "Aston Villa", 3: "Bournemouth", 4: "Brentford",
            5: "Brighton", 6: "Chelsea", 7: "Crystal Palace", 8: "Everton",
            9: "Fulham", 10: "Liverpool", 11: "Luton", 12: "Man City",
            13: "Man Utd", 14: "Newcastle", 15: "Nottm Forest", 16: "Sheffield Utd",
            17: "Spurs", 18: "West Ham", 19: "Wolves", 20: "Burnley"
        }
        
        return fpl_teams.get(int(team_id) if str(team_id).isdigit() else None, f"Team_{team_id}")

# Create global parser instance
data_parser = DataFormatParser()

def parse_html_to_dataframe(html: str, league_code: str = None) -> pd.DataFrame:
    """
    Parse HTML content and convert to a standardized match DataFrame.
    
    Parameters
    ----------
    html : str
        The HTML content to parse
    league_code : str, optional
        League code for league-specific parsing logic
        
    Returns
    -------
    pd.DataFrame
        Standardized DataFrame with columns: date, home, away, home_score, away_score, etc.
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # First try to find existing HTML tables and parse them
    tables = soup.find_all('table')
    
    for table in tables:
        try:
            # Try pandas read_html on the table
            df_list = pd.read_html(str(table))
            if df_list:
                df = df_list[0]
                # Check if this looks like a fixture table
                if is_fixture_table(df):
                    return normalize_fixture_dataframe(df, league_code)
        except Exception as e:
            logger.debug(f"Failed to parse table with pandas: {e}")
            continue
    
    # If no tables found, try to extract fixture data from HTML structure
    matches = extract_matches_from_html(soup, league_code)
    
    if matches:
        df = pd.DataFrame(matches)
        return normalize_fixture_dataframe(df, league_code)
    
    # If no matches found, return empty DataFrame with correct structure
    return create_empty_fixture_dataframe()

def is_fixture_table(df: pd.DataFrame) -> bool:
    """
    Check if a DataFrame appears to contain fixture data.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to check
        
    Returns
    -------
    bool
        True if the DataFrame appears to contain fixture data
    """
    if df.empty or len(df.columns) < 3:
        return False
    
    # Look for common fixture table patterns
    text_content = ' '.join(df.astype(str).values.flatten()).lower()
    
    # Check for common fixture indicators
    fixture_indicators = ['vs', 'v', '-', 'home', 'away', 'date', 'result', 'score']
    
    return any(indicator in text_content for indicator in fixture_indicators)

def extract_matches_from_html(soup: BeautifulSoup, league_code: str = None) -> List[Dict]:
    """
    Extract match data from HTML structure when no tables are available.
    
    Parameters
    ----------
    soup : BeautifulSoup
        Parsed HTML content
    league_code : str, optional
        League code for league-specific parsing
        
    Returns
    -------
    List[Dict]
        List of match dictionaries
    """
    matches = []
    
    # Look for common fixture patterns in divs/sections
    fixture_containers = soup.find_all(['div', 'section', 'article'], 
                                     class_=re.compile(r'(match|fixture|game|result)', re.I))
    
    for container in fixture_containers:
        match_data = extract_single_match(container)
        if match_data:
            matches.append(match_data)
    
    return matches

def extract_single_match(container) -> Optional[Dict]:
    """
    Extract match data from a single HTML container.
    
    Parameters
    ----------
    container
        BeautifulSoup element containing match data
        
    Returns
    -------
    Optional[Dict]
        Match data dictionary or None if extraction fails
    """
    try:
        text = container.get_text(' ', strip=True)
        
        # Look for score patterns like "2-1", "3 - 0", etc.
        score_pattern = r'(\d+)\s*[-–]\s*(\d+)'
        score_match = re.search(score_pattern, text)
        
        if score_match:
            home_score = int(score_match.group(1))
            away_score = int(score_match.group(2))
            
            # Try to extract team names (this is basic and may need refinement)
            # Split text around the score and try to identify teams
            parts = re.split(score_pattern, text)
            if len(parts) >= 4:
                home_team = clean_team_name(parts[0])
                away_team = clean_team_name(parts[3])
                
                return {
                    'home': home_team,
                    'away': away_team,
                    'home_score': home_score,
                    'away_score': away_score,
                    'date': extract_date_from_text(text)
                }
    except Exception as e:
        logger.debug(f"Failed to extract match from container: {e}")
    
    return None

def clean_team_name(text: str) -> str:
    """Clean and normalize team name."""
    if not text:
        return "Unknown"
    
    # Remove common prefixes/suffixes and extra whitespace
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    
    # Remove time indicators, scores, etc.
    text = re.sub(r'\b\d{1,2}:\d{2}\b', '', text)  # Remove times
    text = re.sub(r'\b\d{1,2}/\d{1,2}\b', '', text)  # Remove dates
    
    return text.strip() or "Unknown"

def extract_date_from_text(text: str) -> Optional[str]:
    """Extract date from text content."""
    # Look for common date patterns
    date_patterns = [
        r'\b(\d{4}-\d{2}-\d{2})\b',  # YYYY-MM-DD
        r'\b(\d{2}/\d{2}/\d{4})\b',  # DD/MM/YYYY
        r'\b(\d{2}-\d{2}-\d{4})\b',  # DD-MM-YYYY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return None

def normalize_fixture_dataframe(df: pd.DataFrame, league_code: str = None) -> pd.DataFrame:
    """
    Normalize a DataFrame to the standard fixture format.
    
    Parameters
    ----------
    df : pd.DataFrame
        Raw DataFrame to normalize
    league_code : str, optional
        League code for league-specific normalization
        
    Returns
    -------
    pd.DataFrame
        Normalized DataFrame with standard columns
    """
    # Create a copy to avoid modifying the original
    normalized_df = df.copy()
    
    # Define standard column mappings
    column_mappings = {
        'date': ['date', 'kick_off', 'datetime', 'match_date'],
        'home': ['home', 'home_team', 'team_home', 'home_side'],
        'away': ['away', 'away_team', 'team_away', 'away_side'],
        'home_score': ['home_score', 'goals_home', 'home_goals', 'score_home'],
        'away_score': ['away_score', 'goals_away', 'away_goals', 'score_away'],
        'xg_home': ['xg_home', 'home_xg', 'expected_goals_home'],
        'xg_away': ['xg_away', 'away_xg', 'expected_goals_away'],
    }
    
    # Apply column mappings
    for standard_col, possible_cols in column_mappings.items():
        for col in possible_cols:
            if col in normalized_df.columns:
                normalized_df = normalized_df.rename(columns={col: standard_col})
                break
    
    # Ensure required columns exist
    required_columns = ['date', 'home', 'away']
    for col in required_columns:
        if col not in normalized_df.columns:
            normalized_df[col] = None
    
    # Add optional columns if they don't exist
    optional_columns = ['home_score', 'away_score', 'xg_home', 'xg_away']
    for col in optional_columns:
        if col not in normalized_df.columns:
            normalized_df[col] = None
    
    # Clean and validate data
    normalized_df = clean_fixture_data(normalized_df)
    
    return normalized_df

def clean_fixture_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate fixture data."""
    df = df.copy()
    
    # Remove rows with missing essential data
    df = df.dropna(subset=['home', 'away'])
    
    # Clean team names
    if 'home' in df.columns:
        df['home'] = df['home'].astype(str).str.strip()
    if 'away' in df.columns:
        df['away'] = df['away'].astype(str).str.strip()
    
    # Convert scores to numeric, handling non-numeric values
    for col in ['home_score', 'away_score', 'xg_home', 'xg_away']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Standardize date format
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
    
    return df

def create_empty_fixture_dataframe() -> pd.DataFrame:
    """Create an empty DataFrame with the standard fixture structure."""
    return pd.DataFrame(columns=[
        'date', 'home', 'away', 'home_score', 'away_score', 
        'xg_home', 'xg_away'
    ])

def merge_fixture_dataframes(dataframes: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Merge multiple fixture DataFrames into a single DataFrame.
    
    Parameters
    ----------
    dataframes : List[pd.DataFrame]
        List of DataFrames to merge
        
    Returns
    -------
    pd.DataFrame
        Combined DataFrame
    """
    if not dataframes:
        return create_empty_fixture_dataframe()
    
    # Filter out empty DataFrames
    valid_dfs = [df for df in dataframes if not df.empty]
    
    if not valid_dfs:
        return create_empty_fixture_dataframe()
    
    # Concatenate all DataFrames
    combined_df = pd.concat(valid_dfs, ignore_index=True)
    
    # Remove duplicates based on date, home, and away teams
    combined_df = combined_df.drop_duplicates(subset=['date', 'home', 'away'], keep='first')
    
    # Sort by date
    if 'date' in combined_df.columns:
        combined_df = combined_df.sort_values('date')
    
    return combined_df.reset_index(drop=True)

def parse_league_data(url_or_data: str, league_code: str = None, data_format: str = 'auto') -> pd.DataFrame:
    """
    Unified interface for parsing league data from different formats.
    
    This function provides a single entry point for parsing data from URLs or raw data
    in various formats (HTML, JSON, API responses) with comprehensive error handling.
    
    Parameters
    ----------
    url_or_data : str
        URL to fetch data from or raw data string
    league_code : str, optional
        League code for league-specific parsing logic (e.g., 'ENG_PL')
    data_format : str, default 'auto'
        Expected data format: 'html', 'json', 'api', or 'auto' for auto-detection
        
    Returns
    -------
    pd.DataFrame
        Standardized DataFrame with columns: date, home, away, home_score, away_score, etc.
        Returns empty DataFrame if parsing fails.
        
    Examples
    --------
    >>> # Parse from URL with auto-detection
    >>> df = parse_league_data("https://fantasy.premierleague.com/api/fixtures/", "ENG_PL")
    
    >>> # Parse JSON data directly
    >>> json_str = '{"fixtures": [...]}'
    >>> df = parse_league_data(json_str, "ENG_PL", "json")
    
    >>> # Parse HTML content
    >>> html = "<table>...</table>"
    >>> df = parse_league_data(html, "ESP_LL", "html")
    """
    return data_parser.parse_data(url_or_data, league_code, data_format)