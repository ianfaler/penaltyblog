"""Data parsing utilities for converting scraped data to standardized DataFrames."""

import pandas as pd
import re
import json
from typing import Dict, List, Optional, Union
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def parse_data_to_dataframe(data: str, league_code: str = None) -> pd.DataFrame:
    """
    Parse data content and convert to a standardized match DataFrame.
    Automatically detects data format (HTML, JSON, CSV, API) and applies appropriate parser.
    
    Parameters
    ----------
    data : str
        The data content to parse (HTML, JSON, CSV, etc.)
    league_code : str, optional
        League code for league-specific parsing logic
        
    Returns
    -------
    pd.DataFrame
        Standardized DataFrame with columns: date, home, away, home_score, away_score, etc.
    """
    if not data or not data.strip():
        logger.warning("Empty data provided to parser")
        return create_empty_fixture_dataframe()
    
    data = data.strip()
    
    # Detect data format and parse accordingly
    try:
        # JSON/API format detection
        if data.startswith('{') or data.startswith('['):
            return parse_json_to_dataframe(data, league_code)
        
        # CSV format detection
        elif ',' in data and ('\n' in data or '\r' in data):
            return parse_csv_to_dataframe(data, league_code)
        
        # HTML format (default fallback)
        else:
            return parse_html_to_dataframe(data, league_code)
            
    except Exception as e:
        logger.error(f"Failed to parse data for {league_code}: {e}")
        return create_empty_fixture_dataframe()

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
    try:
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
        
    except Exception as e:
        logger.error(f"HTML parsing failed for {league_code}: {e}")
        return create_empty_fixture_dataframe()

def parse_json_to_dataframe(json_data: str, league_code: str = None) -> pd.DataFrame:
    """
    Parse JSON/API content and convert to a standardized match DataFrame.
    
    Parameters
    ----------
    json_data : str
        The JSON content to parse
    league_code : str, optional
        League code for league-specific parsing logic
        
    Returns
    -------
    pd.DataFrame
        Standardized DataFrame with columns: date, home, away, home_score, away_score, etc.
    """
    try:
        data = json.loads(json_data)
        
        # Handle different JSON structures
        if isinstance(data, list):
            # Direct list of matches
            matches = data
        elif isinstance(data, dict):
            # Look for common keys that contain match data
            possible_keys = ['fixtures', 'matches', 'games', 'events', 'data', 'results']
            matches = None
            
            for key in possible_keys:
                if key in data:
                    matches = data[key]
                    break
            
            if matches is None:
                # If no standard key found, try to find list values
                for value in data.values():
                    if isinstance(value, list) and len(value) > 0:
                        matches = value
                        break
                        
            if matches is None:
                logger.warning(f"No match data found in JSON for {league_code}")
                return create_empty_fixture_dataframe()
        else:
            logger.warning(f"Unexpected JSON structure for {league_code}")
            return create_empty_fixture_dataframe()
        
        # Convert JSON matches to DataFrame
        if not matches:
            return create_empty_fixture_dataframe()
        
        # Apply league-specific JSON parsing if available
        if league_code:
            parsed_matches = parse_league_specific_json(matches, league_code)
            if parsed_matches:
                matches = parsed_matches
        
        # Convert to DataFrame
        df = pd.DataFrame(matches)
        return normalize_fixture_dataframe(df, league_code)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON data for {league_code}: {e}")
        return create_empty_fixture_dataframe()
    except Exception as e:
        logger.error(f"JSON parsing failed for {league_code}: {e}")
        return create_empty_fixture_dataframe()

def parse_csv_to_dataframe(csv_data: str, league_code: str = None) -> pd.DataFrame:
    """
    Parse CSV content and convert to a standardized match DataFrame.
    
    Parameters
    ----------
    csv_data : str
        The CSV content to parse
    league_code : str, optional
        League code for league-specific parsing logic
        
    Returns
    -------
    pd.DataFrame
        Standardized DataFrame with columns: date, home, away, home_score, away_score, etc.
    """
    try:
        from io import StringIO
        
        # Try different separators
        separators = [',', ';', '\t']
        
        for sep in separators:
            try:
                df = pd.read_csv(StringIO(csv_data), sep=sep)
                if not df.empty and len(df.columns) > 2:
                    # Check if this looks like fixture data
                    if is_fixture_table(df):
                        return normalize_fixture_dataframe(df, league_code)
            except Exception as e:
                logger.debug(f"Failed to parse CSV with separator '{sep}': {e}")
                continue
        
        logger.warning(f"Could not parse CSV data for {league_code}")
        return create_empty_fixture_dataframe()
        
    except Exception as e:
        logger.error(f"CSV parsing failed for {league_code}: {e}")
        return create_empty_fixture_dataframe()

def parse_league_specific_json(matches: List[Dict], league_code: str) -> Optional[List[Dict]]:
    """
    Apply league-specific JSON parsing logic.
    
    Parameters
    ----------
    matches : List[Dict]
        Raw match data from JSON
    league_code : str
        League code for specific parsing logic
        
    Returns
    -------
    Optional[List[Dict]]
        Parsed match data or None if no specific logic applies
    """
    if league_code == 'ENG_PL':
        # Premier League Fantasy API specific parsing
        return parse_fpl_api_matches(matches)
    
    # Add more league-specific parsers here as needed
    # elif league_code == 'ESP_LL':
    #     return parse_laliga_api_matches(matches)
    
    return None

def parse_fpl_api_matches(matches: List[Dict]) -> List[Dict]:
    """
    Parse Fantasy Premier League API fixtures format.
    
    Parameters
    ----------
    matches : List[Dict]
        Raw FPL API fixture data
        
    Returns
    -------
    List[Dict]
        Standardized match data
    """
    parsed_matches = []
    
    for match in matches:
        try:
            # FPL API structure: team_h, team_a, team_h_score, team_a_score, kickoff_time
            if 'team_h' in match and 'team_a' in match:
                parsed_match = {
                    'home': get_fpl_team_name(match.get('team_h')),
                    'away': get_fpl_team_name(match.get('team_a')),
                    'home_score': match.get('team_h_score'),
                    'away_score': match.get('team_a_score'),
                    'date': match.get('kickoff_time', '').split('T')[0] if match.get('kickoff_time') else None
                }
                parsed_matches.append(parsed_match)
        except Exception as e:
            logger.debug(f"Failed to parse FPL match: {e}")
            continue
    
    return parsed_matches

def get_fpl_team_name(team_id: int) -> str:
    """
    Convert FPL team ID to team name.
    This is a basic mapping - in production you'd want to fetch this from the API.
    """
    fpl_teams = {
        1: "Arsenal", 2: "Aston Villa", 3: "Bournemouth", 4: "Brentford",
        5: "Brighton", 6: "Burnley", 7: "Chelsea", 8: "Crystal Palace",
        9: "Everton", 10: "Fulham", 11: "Liverpool", 12: "Luton",
        13: "Man City", 14: "Man Utd", 15: "Newcastle", 16: "Nottm Forest",
        17: "Sheffield Utd", 18: "Spurs", 19: "West Ham", 20: "Wolves"
    }
    return fpl_teams.get(team_id, f"Team_{team_id}")

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