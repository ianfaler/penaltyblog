#!/usr/bin/env python3
"""
Unified scraper for penaltyblog that uses proven data sources.

This module replaces the generic HTML parsing approach with specialized scrapers
for reliable data sources like FBRef, Understat, and Football-Data.co.uk.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import pandas as pd
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the project root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import only what we need to avoid dependency issues
try:
    from penaltyblog.config.leagues import load_leagues, get_league_by_code, get_default_league
    from penaltyblog.scrapers.fbref import FBRef
    from penaltyblog.scrapers.understat import Understat
    from penaltyblog.scrapers.footballdata import FootballData
    from penaltyblog.scrapers.common import COMPETITION_MAPPINGS
except ImportError as e:
    # Fallback direct imports to avoid package dependency issues
    config_path = Path(__file__).parent.parent / "config"
    scrapers_path = Path(__file__).parent
    
    sys.path.insert(0, str(config_path))
    sys.path.insert(0, str(scrapers_path))
    
    from leagues import load_leagues, get_league_by_code, get_default_league
    from fbref import FBRef
    from understat import Understat
    from footballdata import FootballData
    from common import COMPETITION_MAPPINGS

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# League code to competition name mapping for the three data sources
LEAGUE_TO_COMPETITION = {
    # Premier League
    "ENG_PL": "ENG Premier League",
    
    # La Liga  
    "ESP_LL": "ESP La Liga",
    
    # Bundesliga
    "GER_BL": "DEU Bundesliga 1",
    
    # Serie A
    "ITA_SA": "ITA Serie A",
    
    # Ligue 1
    "FRA_L1": "FRA Ligue 1",
    
    # Eredivisie
    "NED_ED": "NLD Eredivisie",
    
    # Portuguese Liga
    "POR_PL": "PRT Liga 1",
    
    # Championship
    "ENG_CH": "ENG Championship",
    
    # Segunda División
    "ESP_L2": "ESP La Liga Segunda",
    
    # 2. Bundesliga
    "GER_B2": "DEU Bundesliga 2",
    
    # Serie B
    "ITA_SB": "ITA Serie B",
    
    # Ligue 2
    "FRA_L2": "FRA Ligue 2",
    
    # Belgian First Division A
    "BEL_PD": "BEL First Division A",
    
    # Turkish Super Lig
    "TUR_SL": "TUR Super Lig",
    
    # Greek Super League
    "GRE_SL": "GRC Super League",
    
    # Scottish Premier League
    "SCO_PL": "SCO Premier League",
    
    # English League One
    "ENG_L1": "ENG League 1",
    
    # English League Two  
    "ENG_L2": "ENG League 2",
    
    # English Conference
    "ENG_CN": "ENG Conference",
    
    # Scottish Division 1
    "SCO_D1": "SCO Division 1",
    
    # Scottish Division 2
    "SCO_D2": "SCO Division 2",
    
    # Scottish Division 3
    "SCO_D3": "SCO Division 3",
}

class UnifiedScraper:
    """Main scraper class that coordinates data collection from multiple sources."""
    
    def __init__(self, season: str = "2024-25", timeout: int = 30, max_workers: int = 3):
        """
        Initialize the unified scraper.
        
        Parameters
        ----------
        season : str
            Season in format YYYY-YY (e.g., "2024-25")
        timeout : int
            Request timeout in seconds
        max_workers : int
            Maximum number of concurrent threads for scraping
        """
        self.season = season
        self.timeout = timeout
        self.max_workers = max_workers
        
        # Convert season to different formats needed by scrapers
        self.fbref_season = self._convert_season_for_fbref(season)
        self.understat_season = self._convert_season_for_understat(season)
        self.footballdata_season = self._convert_season_for_footballdata(season)
        
    def _convert_season_for_fbref(self, season: str) -> str:
        """Convert season format for FBRef (2024-25 -> 2024-2025)."""
        if "-" in season:
            start_year, end_year = season.split("-")
            if len(end_year) == 2:
                end_year = "20" + end_year
            return f"{start_year}-{end_year}"
        return season
    
    def _convert_season_for_understat(self, season: str) -> str:
        """Convert season format for Understat (2024-25 -> 2024)."""
        if "-" in season:
            return season.split("-")[0]
        return season
    
    def _convert_season_for_footballdata(self, season: str) -> str:
        """Convert season format for Football-Data (2024-25 -> 2024-2025)."""
        if "-" in season:
            start_year, end_year = season.split("-")
            if len(end_year) == 2:
                end_year = "20" + end_year
            return f"{start_year}-{end_year}"
        return season
    
    def get_available_sources_for_league(self, league_code: str) -> List[str]:
        """Get available data sources for a specific league."""
        competition = LEAGUE_TO_COMPETITION.get(league_code)
        if not competition:
            logger.warning(f"No competition mapping found for league {league_code}")
            return []
        
        available_sources = []
        if competition in COMPETITION_MAPPINGS:
            comp_data = COMPETITION_MAPPINGS[competition]
            if "fbref" in comp_data:
                available_sources.append("fbref")
            if "understat" in comp_data:
                available_sources.append("understat")
            if "footballdata" in comp_data:
                available_sources.append("footballdata")
        
        return available_sources
    
    def scrape_league_from_source(self, league_code: str, source: str) -> Optional[pd.DataFrame]:
        """
        Scrape data for a specific league from a specific source.
        
        Enhanced to fail explicitly when no real data is available.
        
        Parameters
        ----------
        league_code : str
            League code (e.g., 'ENG_PL')
        source : str
            Data source ('fbref', 'understat', 'footballdata')
            
        Returns
        -------
        Optional[pd.DataFrame]
            DataFrame containing match data or None if failed
        """
        competition = LEAGUE_TO_COMPETITION.get(league_code)
        if not competition:
            logger.error(f"No competition mapping found for league {league_code}")
            return None
        
        league = get_league_by_code(league_code)
        if not league:
            logger.error(f"League not found: {league_code}")
            return None
        
        logger.info(f"🔄 Scraping {league.display_name} from {source.upper()}")
        
        try:
            if source == "fbref":
                scraper = FBRef(competition, self.fbref_season)
                df = scraper.get_fixtures()
            elif source == "understat":
                scraper = Understat(competition, self.understat_season)
                df = scraper.get_fixtures()
            elif source == "footballdata":
                scraper = FootballData(competition, self.footballdata_season)
                df = scraper.get_fixtures()
            else:
                logger.error(f"Unknown source: {source}")
                return None
            
            if df.empty:
                logger.warning(f"No data returned from {source} for {league.display_name}")
                return None
            
            # CRITICAL: Validate that this is real data, not demo data
            if not self._validate_real_data(df, league_code, source):
                logger.error(f"Data validation failed - rejecting data from {source} for {league.display_name}")
                return None
            
            # Standardize the DataFrame
            df = self._standardize_dataframe(df, league_code, source)
            
            logger.info(f"✅ Successfully scraped {len(df)} matches from {source.upper()} for {league.display_name}")
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to scrape {league.display_name} from {source}: {e}")
            return None
    
    def _validate_real_data(self, df: pd.DataFrame, league_code: str, source: str) -> bool:
        """
        Validate that the scraped data is real, not demo/fake data.
        
        This is a critical validation to prevent fake data from entering the system.
        
        Parameters
        ----------
        df : pd.DataFrame
            The scraped data
        league_code : str
            League code for context
        source : str
            Data source for context
            
        Returns
        -------
        bool
            True if data appears to be real, False otherwise
        """
        if df.empty:
            logger.warning(f"Empty dataframe from {source} for {league_code}")
            return False
        
        # Check for temporal validation issues (completed results for future dates)
        if 'date' in df.columns and 'goals_home' in df.columns and 'goals_away' in df.columns:
            df_copy = df.copy()
            df_copy['date_parsed'] = pd.to_datetime(df_copy['date'], errors='coerce')
            current_date = datetime.now().date()
            
            # Find future dates with completed results
            future_mask = df_copy['date_parsed'].dt.date > current_date
            completed_mask = df_copy['goals_home'].notna() & df_copy['goals_away'].notna()
            invalid_future = future_mask & completed_mask
            
            if invalid_future.any():
                invalid_count = invalid_future.sum()
                logger.error(f"CRITICAL: {source} for {league_code} has {invalid_count} completed results for future dates")
                logger.error("This indicates demo/fake data generation - REJECTING")
                return False
        
        # Check for suspicious patterns that indicate fake data
        if 'team_home' in df.columns and 'team_away' in df.columns:
            # Check for obviously fake team names
            fake_patterns = ['test', 'demo', 'fake', 'sample', 'placeholder']
            all_teams = list(df['team_home'].unique()) + list(df['team_away'].unique())
            
            for team in all_teams:
                if pd.isna(team):
                    continue
                team_lower = str(team).lower()
                for pattern in fake_patterns:
                    if pattern in team_lower:
                        logger.error(f"Fake team name detected: '{team}' from {source} for {league_code}")
                        return False
        
        # Check data size - real data should have reasonable amount
        if len(df) < 5:  # Too few rows might indicate fake/test data
            logger.warning(f"Very small dataset from {source} for {league_code}: {len(df)} rows")
            return False
        
        logger.debug(f"Data validation passed for {source} {league_code}: {len(df)} rows")
        return True
    
    def _standardize_dataframe(self, df: pd.DataFrame, league_code: str, source: str) -> pd.DataFrame:
        """Standardize DataFrame format across different sources."""
        # Reset index if it's set
        if df.index.name is not None:
            df = df.reset_index()
        
        # Add standard metadata
        df['league_code'] = league_code
        df['data_source'] = source
        
        # Get league info
        league = get_league_by_code(league_code)
        if league:
            df['league_name'] = league.name
            df['country'] = league.country
            df['tier'] = league.tier
        
        # Standardize column names across sources
        column_mapping = {
            'team_home': 'home',
            'team_away': 'away',
            'goals_home': 'home_score',
            'goals_away': 'away_score',
            'fthg': 'home_score',
            'ftag': 'away_score',
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df[new_col] = df[old_col]
        
        # Ensure required columns exist
        required_columns = ['date', 'home', 'away']
        for col in required_columns:
            if col not in df.columns:
                logger.warning(f"Missing required column '{col}' for {league_code} from {source}")
        
        # Add optional columns if they don't exist
        optional_columns = ['home_score', 'away_score', 'xg_home', 'xg_away']
        for col in optional_columns:
            if col not in df.columns:
                df[col] = None
        
        return df
    
    def scrape_league(self, league_code: str, preferred_source: str = None) -> pd.DataFrame:
        """
        Scrape data for a specific league, trying multiple sources if needed.
        
        Enhanced to fail explicitly when no real data sources work.
        
        Parameters
        ----------
        league_code : str
            League code (e.g., 'ENG_PL')
        preferred_source : str, optional
            Preferred data source to try first
            
        Returns
        -------
        pd.DataFrame
            DataFrame containing match data
            
        Raises
        ------
        RuntimeError
            If no real data could be obtained from any source
        """
        available_sources = self.get_available_sources_for_league(league_code)
        
        if not available_sources:
            error_msg = f"No data sources available for league {league_code}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Prioritize sources: FBRef > Football-Data > Understat
        source_priority = ["fbref", "footballdata", "understat"]
        
        # If a preferred source is specified and available, try it first
        if preferred_source and preferred_source in available_sources:
            sources_to_try = [preferred_source] + [s for s in source_priority if s in available_sources and s != preferred_source]
        else:
            sources_to_try = [s for s in source_priority if s in available_sources]
        
        last_error = None
        attempted_sources = []
        
        for source in sources_to_try:
            attempted_sources.append(source)
            try:
                df = self.scrape_league_from_source(league_code, source)
                if df is not None and not df.empty:
                    logger.info(f"✅ Successfully obtained real data from {source} for {league_code}")
                    return df
                else:
                    logger.warning(f"Source {source} returned no data for {league_code}")
            except Exception as e:
                last_error = e
                logger.error(f"Source {source} failed for {league_code}: {e}")
        
        # If we get here, all sources failed
        error_msg = (
            f"CRITICAL FAILURE: All data sources failed for {league_code}. "
            f"Attempted sources: {attempted_sources}. "
            f"This system will NOT generate fake data as a fallback. "
            f"Last error: {last_error}"
        )
        logger.error(error_msg)
        
        # Return empty DataFrame but log that this is an explicit failure
        logger.error("Returning empty DataFrame - no fake data generation")
        return pd.DataFrame()
    
    def scrape_multiple_leagues(self, league_codes: List[str], preferred_source: str = None) -> Dict[str, pd.DataFrame]:
        """
        Scrape multiple leagues concurrently.
        
        Parameters
        ----------
        league_codes : List[str]
            List of league codes to scrape
        preferred_source : str, optional
            Preferred data source to try first
            
        Returns
        -------
        Dict[str, pd.DataFrame]
            Dictionary mapping league codes to DataFrames
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all scraping tasks
            future_to_league = {
                executor.submit(self.scrape_league, league_code, preferred_source): league_code
                for league_code in league_codes
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_league):
                league_code = future_to_league[future]
                try:
                    df = future.result()
                    results[league_code] = df
                except Exception as e:
                    logger.error(f"❌ Error scraping {league_code}: {e}")
                    results[league_code] = pd.DataFrame()
        
        return results
    
    def scrape_all_supported_leagues(self, preferred_source: str = None) -> Dict[str, pd.DataFrame]:
        """
        Scrape all leagues that have mappings to supported data sources.
        
        Parameters
        ----------
        preferred_source : str, optional
            Preferred data source to try first
            
        Returns
        -------
        Dict[str, pd.DataFrame]
            Dictionary mapping league codes to DataFrames
        """
        supported_leagues = list(LEAGUE_TO_COMPETITION.keys())
        
        logger.info(f"🚀 Starting to scrape {len(supported_leagues)} supported leagues")
        return self.scrape_multiple_leagues(supported_leagues, preferred_source)
    
    def get_supported_leagues(self) -> List[Dict[str, Any]]:
        """Get list of all supported leagues with their available sources."""
        supported = []
        
        for league_code, competition in LEAGUE_TO_COMPETITION.items():
            league = get_league_by_code(league_code)
            if league:
                sources = self.get_available_sources_for_league(league_code)
                supported.append({
                    'league_code': league_code,
                    'league_name': league.name,
                    'country': league.country,
                    'tier': league.tier,
                    'competition': competition,
                    'sources': sources
                })
        
        return supported

def create_output_directory() -> Path:
    """Create output directory with current date."""
    today = datetime.now()
    output_dir = Path("data") / today.strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def save_league_data(league_code: str, df: pd.DataFrame, output_dir: Path) -> Optional[Path]:
    """Save league data to CSV file."""
    if df.empty:
        logger.warning(f"No data to save for {league_code}")
        return None
    
    try:
        league = get_league_by_code(league_code)
        if not league:
            logger.error(f"League not found: {league_code}")
            return None
        
        # Create filename: country_league.csv
        filename = f"{league.country.replace(' ', '_')}_{league.name.replace(' ', '_')}.csv"
        # Remove special characters
        filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        
        filepath = output_dir / filename
        df.to_csv(filepath, index=False)
        
        logger.info(f"💾 Saved {len(df)} matches to {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"❌ Failed to save data for {league_code}: {e}")
        return None

def merge_fixture_dataframes(dataframes: List[pd.DataFrame]) -> pd.DataFrame:
    """Merge multiple fixture DataFrames into a single DataFrame."""
    if not dataframes:
        return pd.DataFrame()
    
    # Filter out empty DataFrames
    valid_dfs = [df for df in dataframes if not df.empty]
    
    if not valid_dfs:
        return pd.DataFrame()
    
    # Concatenate all DataFrames
    combined_df = pd.concat(valid_dfs, ignore_index=True)
    
    # Remove duplicates based on date, home, and away teams
    duplicate_cols = ['date', 'home', 'away']
    available_cols = [col for col in duplicate_cols if col in combined_df.columns]
    
    if available_cols:
        combined_df = combined_df.drop_duplicates(subset=available_cols, keep='first')
    
    # Sort by date if available
    if 'date' in combined_df.columns:
        combined_df = combined_df.sort_values('date')
    
    return combined_df.reset_index(drop=True)

def parse_league_list(league_str: str) -> List[str]:
    """Parse a comma-separated list of league codes."""
    if not league_str:
        return []
    
    return [code.strip().upper() for code in league_str.split(',') if code.strip()]

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape match data using proven data sources (FBRef, Understat, Football-Data)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Scrape default league (Premier League)
  %(prog)s --league ENG_PL                   # Scrape Premier League
  %(prog)s --league ENG_PL,ESP_LL            # Scrape Premier League and La Liga
  %(prog)s --all-supported                   # Scrape all leagues with data source mappings
  %(prog)s --list-supported                  # List all supported leagues
  %(prog)s --source fbref --league ENG_PL    # Use FBRef specifically for Premier League
        """
    )
    
    parser.add_argument(
        '--league', '-l',
        type=str,
        help='League code(s) to scrape (comma-separated, e.g., ENG_PL,ESP_LL)'
    )
    
    parser.add_argument(
        '--all-supported', '-a',
        action='store_true',
        help='Scrape all leagues that have data source mappings'
    )
    
    parser.add_argument(
        '--list-supported',
        action='store_true',
        help='List all supported leagues and their available sources'
    )
    
    parser.add_argument(
        '--source', '-s',
        choices=['fbref', 'understat', 'footballdata'],
        help='Preferred data source to use'
    )
    
    parser.add_argument(
        '--season',
        type=str,
        default="2024-25",
        help='Season to scrape (default: 2024-25)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        type=Path,
        help='Output directory (default: data/YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--max-workers', '-w',
        type=int,
        default=3,
        help='Maximum concurrent workers (default: 3)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize scraper
    scraper = UnifiedScraper(
        season=args.season,
        timeout=args.timeout,
        max_workers=args.max_workers
    )
    
    # List supported leagues if requested
    if args.list_supported:
        supported = scraper.get_supported_leagues()
        print("📋 Supported leagues and their data sources:")
        print("=" * 60)
        
        # Group by tier
        tiers = {}
        for league in supported:
            tier = league['tier']
            if tier not in tiers:
                tiers[tier] = []
            tiers[tier].append(league)
        
        for tier in sorted(tiers.keys()):
            print(f"\nTier {tier} Leagues:")
            print("-" * 20)
            
            for league in sorted(tiers[tier], key=lambda x: x['country']):
                sources_str = ", ".join(league['sources'])
                print(f"  {league['league_code']:<8} - {league['country']} {league['league_name']:<20} [{sources_str}]")
        
        print(f"\nTotal: {len(supported)} leagues supported")
        return
    
    # Determine leagues to scrape
    if args.all_supported:
        leagues_to_scrape = list(LEAGUE_TO_COMPETITION.keys())
    elif args.league:
        leagues_to_scrape = parse_league_list(args.league)
    else:
        # Default to Premier League for backward compatibility
        leagues_to_scrape = ["ENG_PL"]
    
    if not leagues_to_scrape:
        logger.error("No leagues specified. Use --league, --all-supported, or --list-supported")
        return 1
    
    # Validate league codes
    invalid_leagues = [code for code in leagues_to_scrape if code not in LEAGUE_TO_COMPETITION]
    if invalid_leagues:
        logger.error(f"Unsupported league codes: {', '.join(invalid_leagues)}")
        logger.info("Use --list-supported to see available leagues")
        return 1
    
    # Set up output directory
    output_dir = args.output_dir or create_output_directory()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"📁 Output directory: {output_dir}")
    logger.info(f"🗓️  Season: {args.season}")
    if args.source:
        logger.info(f"📊 Preferred source: {args.source.upper()}")
    
    # Start scraping
    if len(leagues_to_scrape) == 1:
        # Single league
        league_code = leagues_to_scrape[0]
        df = scraper.scrape_league(league_code, args.source)
        save_league_data(league_code, df, output_dir)
    else:
        # Multiple leagues
        results = scraper.scrape_multiple_leagues(leagues_to_scrape, args.source)
        
        # Save individual league files
        saved_files = []
        for league_code, df in results.items():
            if not df.empty:
                filepath = save_league_data(league_code, df, output_dir)
                if filepath:
                    saved_files.append(filepath)
        
        # Create combined file if multiple leagues were scraped
        if len(saved_files) > 1:
            all_dfs = [df for df in results.values() if not df.empty]
            if all_dfs:
                combined_df = merge_fixture_dataframes(all_dfs)
                combined_path = output_dir / "combined_leagues.csv"
                combined_df.to_csv(combined_path, index=False)
                logger.info(f"💾 Saved combined data ({len(combined_df)} matches) to {combined_path}")
    
    logger.info("🏁 Scraping completed")
    return 0

if __name__ == "__main__":
    sys.exit(main())