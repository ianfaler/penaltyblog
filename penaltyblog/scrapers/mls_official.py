import logging
import pandas as pd
import json
from datetime import datetime
from typing import Optional, Dict, Any

from .base_scrapers import RequestsScraper
from .common import sanitize_columns, move_column_inplace, create_game_id
from .team_mappings import get_mls_team_mappings

logger = logging.getLogger(__name__)


class MLSOfficial(RequestsScraper):
    """
    Scraper for official MLS data sources and APIs.
    
    Parameters
    ----------
    season : str
        Season in format "2024" or "2024-25" 
    team_mappings : dict or None
        Dictionary of team name mappings
    """

    source = "mls_official"

    def __init__(self, season: str, team_mappings=None):
        self.season = season
        self.base_url = "https://www.mlssoccer.com"
        
        # Use MLS-specific team mappings if none provided
        if team_mappings is None:
            team_mappings = get_mls_team_mappings()
            
        super().__init__(team_mappings=team_mappings)

    @classmethod
    def list_competitions(cls) -> list:
        return ["USA Major League Soccer"]

    def get_fixtures(self) -> pd.DataFrame:
        """
        Get MLS fixtures/results data.
        
        Returns
        -------
        pd.DataFrame
            DataFrame with fixture information
        """
        try:
            # MLS API endpoint for schedule data
            url = f"{self.base_url}/schedule"
            
            logger.info(f"Fetching MLS fixtures for {self.season}")
            html_content = self.get(url)
            
            # Parse the HTML to extract fixtures data
            fixtures_df = self._parse_fixtures_html(html_content)
            
            if fixtures_df.empty:
                logger.warning("No fixtures data found")
                return pd.DataFrame()
            
            # Clean and standardize the data
            fixtures_df = self._clean_fixtures_data(fixtures_df)
            
            return fixtures_df
            
        except Exception as e:
            logger.error(f"Error fetching MLS fixtures: {e}")
            return pd.DataFrame()

    def _parse_fixtures_html(self, html_content: str) -> pd.DataFrame:
        """
        Parse HTML content to extract fixtures data.
        
        Parameters
        ----------
        html_content : str
            Raw HTML content from MLS website
            
        Returns
        -------
        pd.DataFrame
            Parsed fixtures data
        """
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for schedule/fixture data in the HTML
            # This is a simplified parser - the actual implementation would need
            # to be tailored to the specific HTML structure of mlssoccer.com
            
            fixtures = []
            
            # Find fixture containers (this would need to be adjusted based on actual HTML structure)
            fixture_elements = soup.find_all(['div', 'article'], class_=['match', 'fixture', 'game'])
            
            for element in fixture_elements:
                try:
                    fixture_data = self._extract_fixture_data(element)
                    if fixture_data:
                        fixtures.append(fixture_data)
                except Exception as e:
                    logger.debug(f"Error parsing fixture element: {e}")
                    continue
            
            if not fixtures:
                logger.warning("No fixtures found in HTML content")
                return pd.DataFrame()
            
            return pd.DataFrame(fixtures)
            
        except ImportError:
            logger.error("BeautifulSoup4 not available for HTML parsing")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error parsing fixtures HTML: {e}")
            return pd.DataFrame()

    def _extract_fixture_data(self, element) -> Optional[Dict[str, Any]]:
        """
        Extract fixture data from a single HTML element.
        
        Parameters
        ----------
        element
            BeautifulSoup element containing fixture information
            
        Returns
        -------
        dict or None
            Fixture data dictionary
        """
        try:
            # This is a template - would need to be customized based on actual HTML structure
            fixture = {}
            
            # Extract teams (look for team names)
            team_elements = element.find_all(['span', 'div'], class_=['team', 'club'])
            if len(team_elements) >= 2:
                fixture['team_home'] = team_elements[0].get_text(strip=True)
                fixture['team_away'] = team_elements[1].get_text(strip=True)
            
            # Extract date/time
            date_element = element.find(['time', 'span'], class_=['date', 'datetime'])
            if date_element:
                date_str = date_element.get('datetime') or date_element.get_text(strip=True)
                fixture['date'] = self._parse_date(date_str)
            
            # Extract score if available
            score_element = element.find(['span', 'div'], class_=['score', 'result'])
            if score_element:
                score_text = score_element.get_text(strip=True)
                goals = self._parse_score(score_text)
                if goals:
                    fixture['goals_home'] = goals[0]
                    fixture['goals_away'] = goals[1]
            
            # Extract match status
            status_element = element.find(['span', 'div'], class_=['status', 'state'])
            if status_element:
                fixture['status'] = status_element.get_text(strip=True)
            
            return fixture if len(fixture) > 2 else None
            
        except Exception as e:
            logger.debug(f"Error extracting fixture data: {e}")
            return None

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string into standardized format."""
        try:
            # Handle various date formats that might be found
            for fmt in ['%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y']:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            logger.debug(f"Could not parse date: {date_str}")
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing date {date_str}: {e}")
            return None

    def _parse_score(self, score_str: str) -> Optional[tuple]:
        """Parse score string into home and away goals."""
        try:
            # Handle formats like "2-1", "2 - 1", "2:1"
            for separator in ['-', ':', '–']:
                if separator in score_str:
                    parts = score_str.split(separator)
                    if len(parts) == 2:
                        home_goals = int(parts[0].strip())
                        away_goals = int(parts[1].strip())
                        return (home_goals, away_goals)
            
            return None
            
        except (ValueError, IndexError) as e:
            logger.debug(f"Error parsing score {score_str}: {e}")
            return None

    def _clean_fixtures_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and standardize fixtures data.
        
        Parameters
        ----------
        df : pd.DataFrame
            Raw fixtures data
            
        Returns
        -------
        pd.DataFrame
            Cleaned fixtures data
        """
        try:
            # Apply team mappings
            df = self._map_teams(df, ['team_home', 'team_away'])
            
            # Sanitize column names
            df = sanitize_columns(df)
            
            # Ensure required columns exist
            required_cols = ['team_home', 'team_away', 'date']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                logger.warning(f"Missing required columns: {missing_cols}")
                for col in missing_cols:
                    df[col] = None
            
            # Convert date column
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            # Create game IDs
            if all(col in df.columns for col in ['team_home', 'team_away', 'date']):
                df = create_game_id(df)
            
            # Sort by date
            if 'date' in df.columns:
                df = df.sort_values('date')
            
            # Reset index
            df = df.reset_index(drop=True)
            
            logger.info(f"Cleaned fixtures data: {len(df)} matches")
            
            return df
            
        except Exception as e:
            logger.error(f"Error cleaning fixtures data: {e}")
            return df

    def get_teams(self) -> pd.DataFrame:
        """
        Get MLS teams data.
        
        Returns
        -------
        pd.DataFrame
            DataFrame with team information
        """
        try:
            # Create teams DataFrame from mappings
            teams_data = []
            mls_teams = get_mls_team_mappings()
            
            for team_name, aliases in mls_teams.items():
                teams_data.append({
                    'team_name': team_name,
                    'aliases': aliases,
                    'conference': self._get_team_conference(team_name),
                    'founded': self._get_team_founded_year(team_name),
                    'city': self._get_team_city(team_name)
                })
            
            df = pd.DataFrame(teams_data)
            df = sanitize_columns(df)
            
            logger.info(f"Retrieved {len(df)} MLS teams")
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting teams data: {e}")
            return pd.DataFrame()

    def _get_team_conference(self, team_name: str) -> str:
        """Get conference for a team."""
        eastern_teams = {
            "Atlanta United FC", "Charlotte FC", "Chicago Fire FC", "FC Cincinnati",
            "Columbus Crew", "D.C. United", "Inter Miami CF", "CF Montréal",
            "Nashville SC", "New England Revolution", "New York City FC",
            "New York Red Bulls", "Orlando City SC", "Philadelphia Union", "Toronto FC"
        }
        
        return "Eastern" if team_name in eastern_teams else "Western"

    def _get_team_founded_year(self, team_name: str) -> Optional[int]:
        """Get founding year for a team."""
        founding_years = {
            "Atlanta United FC": 2017,
            "Austin FC": 2021,
            "Charlotte FC": 2022,
            "Chicago Fire FC": 1997,
            "FC Cincinnati": 2019,
            "Colorado Rapids": 1996,
            "Columbus Crew": 1996,
            "D.C. United": 1996,
            "FC Dallas": 1996,
            "Houston Dynamo FC": 2006,
            "Inter Miami CF": 2020,
            "LA Galaxy": 1996,
            "Los Angeles FC": 2018,
            "Minnesota United FC": 2017,
            "CF Montréal": 2012,
            "Nashville SC": 2020,
            "New England Revolution": 1996,
            "New York City FC": 2015,
            "New York Red Bulls": 1996,
            "Orlando City SC": 2015,
            "Philadelphia Union": 2010,
            "Portland Timbers": 2011,
            "Real Salt Lake": 2005,
            "San Diego FC": 2025,
            "San Jose Earthquakes": 1996,
            "Seattle Sounders FC": 2009,
            "Sporting Kansas City": 1996,
            "St. Louis City SC": 2023,
            "Toronto FC": 2007,
            "Vancouver Whitecaps FC": 2011
        }
        
        return founding_years.get(team_name)

    def _get_team_city(self, team_name: str) -> str:
        """Get city for a team."""
        cities = {
            "Atlanta United FC": "Atlanta",
            "Austin FC": "Austin",
            "Charlotte FC": "Charlotte",
            "Chicago Fire FC": "Chicago",
            "FC Cincinnati": "Cincinnati",
            "Colorado Rapids": "Commerce City",
            "Columbus Crew": "Columbus",
            "D.C. United": "Washington",
            "FC Dallas": "Frisco",
            "Houston Dynamo FC": "Houston",
            "Inter Miami CF": "Fort Lauderdale",
            "LA Galaxy": "Carson",
            "Los Angeles FC": "Los Angeles",
            "Minnesota United FC": "Saint Paul",
            "CF Montréal": "Montreal",
            "Nashville SC": "Nashville",
            "New England Revolution": "Foxborough",
            "New York City FC": "New York",
            "New York Red Bulls": "Harrison",
            "Orlando City SC": "Orlando",
            "Philadelphia Union": "Chester",
            "Portland Timbers": "Portland",
            "Real Salt Lake": "Sandy",
            "San Diego FC": "San Diego",
            "San Jose Earthquakes": "San Jose",
            "Seattle Sounders FC": "Seattle",
            "Sporting Kansas City": "Kansas City",
            "St. Louis City SC": "St. Louis",
            "Toronto FC": "Toronto",
            "Vancouver Whitecaps FC": "Vancouver"
        }
        
        return cities.get(team_name, "Unknown")