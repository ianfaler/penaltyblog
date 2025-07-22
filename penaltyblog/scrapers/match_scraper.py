#!/usr/bin/env python3
"""
Match scraper for penaltyblog supporting all configured leagues.

This module provides functionality to scrape match data from official league
websites using native HTML scraping with requests + BeautifulSoup + pandas.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
import pandas as pd
import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the project root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from penaltyblog.config.leagues import load_leagues, get_league_by_code, get_default_league
from penaltyblog.scrapers.parsers import parse_html_to_dataframe, merge_fixture_dataframes

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MatchScraper:
    """Main scraper class for fetching match data from league websites."""
    
    def __init__(self, timeout: int = 30, max_workers: int = 5):
        """
        Initialize the match scraper.
        
        Parameters
        ----------
        timeout : int
            Request timeout in seconds
        max_workers : int
            Maximum number of concurrent threads for scraping
        """
        self.timeout = timeout
        self.max_workers = max_workers
        self.session = requests.Session()
        
        # Set a realistic user agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
    def scrape_league(self, league_code: str) -> pd.DataFrame:
        """
        Scrape match data for a specific league.
        
        Parameters
        ----------
        league_code : str
            League code (e.g., 'ENG_PL', 'ESP_LL')
            
        Returns
        -------
        pd.DataFrame
            DataFrame containing match data
        """
        league = get_league_by_code(league_code)
        if not league:
            logger.error(f"League not found: {league_code}")
            return pd.DataFrame()
        
        logger.info(f"🔄 Scraping {league.display_name} ({league_code})")
        
        try:
            url = league.get_url()
            logger.debug(f"Fetching data from: {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse HTML to DataFrame
            df = parse_html_to_dataframe(response.text, league_code)
            
            if df.empty:
                logger.warning(f"No match data found for {league.display_name}")
                return df
            
            # Add league metadata
            df['league_code'] = league_code
            df['league_name'] = league.name
            df['country'] = league.country
            
            logger.info(f"✅ Successfully scraped {len(df)} matches from {league.display_name}")
            return df
            
        except requests.RequestException as e:
            logger.error(f"❌ Failed to fetch data for {league.display_name}: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ Failed to parse data for {league.display_name}: {e}")
            return pd.DataFrame()
    
    def scrape_multiple_leagues(self, league_codes: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Scrape multiple leagues concurrently.
        
        Parameters
        ----------
        league_codes : List[str]
            List of league codes to scrape
            
        Returns
        -------
        Dict[str, pd.DataFrame]
            Dictionary mapping league codes to DataFrames
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all scraping tasks
            future_to_league = {
                executor.submit(self.scrape_league, league_code): league_code
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
    
    def scrape_all_leagues(self) -> Dict[str, pd.DataFrame]:
        """
        Scrape all configured leagues.
        
        Returns
        -------
        Dict[str, pd.DataFrame]
            Dictionary mapping league codes to DataFrames
        """
        leagues = load_leagues()
        league_codes = list(leagues.keys())
        
        logger.info(f"🚀 Starting to scrape {len(league_codes)} leagues")
        return self.scrape_multiple_leagues(league_codes)
    
    def save_league_data(self, league_code: str, df: pd.DataFrame, output_dir: Path) -> Optional[Path]:
        """
        Save league data to CSV file.
        
        Parameters
        ----------
        league_code : str
            League code
        df : pd.DataFrame
            Match data
        output_dir : Path
            Output directory
            
        Returns
        -------
        Optional[Path]
            Path to saved file or None if save failed
        """
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

def parse_league_list(league_str: str) -> List[str]:
    """
    Parse a comma-separated list of league codes.
    
    Parameters
    ----------
    league_str : str
        Comma-separated league codes (e.g., "ENG_PL,ESP_LL")
        
    Returns
    -------
    List[str]
        List of league codes
    """
    if not league_str:
        return []
    
    return [code.strip().upper() for code in league_str.split(',') if code.strip()]

def create_output_directory() -> Path:
    """Create output directory with current date."""
    today = datetime.now()
    output_dir = Path("data") / today.strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape match data from football league websites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Scrape default league (Premier League)
  %(prog)s --league ENG_PL           # Scrape Premier League
  %(prog)s --league ENG_PL,ESP_LL    # Scrape Premier League and La Liga
  %(prog)s --all-leagues             # Scrape all configured leagues
  %(prog)s --list-leagues            # List all available leagues
        """
    )
    
    parser.add_argument(
        '--league', '-l',
        type=str,
        help='League code(s) to scrape (comma-separated, e.g., ENG_PL,ESP_LL)'
    )
    
    parser.add_argument(
        '--all-leagues', '-a',
        action='store_true',
        help='Scrape all configured leagues'
    )
    
    parser.add_argument(
        '--list-leagues',
        action='store_true',
        help='List all available leagues and exit'
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
        default=5,
        help='Maximum concurrent workers (default: 5)'
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
    
    # List leagues if requested
    if args.list_leagues:
        leagues = load_leagues()
        print("📋 Available leagues:")
        print("=" * 50)
        
        # Group by tier
        for tier in sorted(set(league.tier for league in leagues.values())):
            tier_leagues = {code: league for code, league in leagues.items() if league.tier == tier}
            print(f"\nTier {tier} Leagues:")
            print("-" * 20)
            
            for code, league in sorted(tier_leagues.items()):
                print(f"  {code:<8} - {league.display_name}")
        
        print(f"\nTotal: {len(leagues)} leagues configured")
        return
    
    # Determine leagues to scrape
    if args.all_leagues:
        leagues_to_scrape = list(load_leagues().keys())
    elif args.league:
        leagues_to_scrape = parse_league_list(args.league)
    else:
        # Default to Premier League for backward compatibility
        default_league = get_default_league()
        leagues_to_scrape = [default_league.code] if default_league else []
    
    if not leagues_to_scrape:
        logger.error("No leagues specified. Use --league, --all-leagues, or --list-leagues")
        return 1
    
    # Validate league codes
    available_leagues = load_leagues()
    invalid_leagues = [code for code in leagues_to_scrape if code not in available_leagues]
    if invalid_leagues:
        logger.error(f"Invalid league codes: {', '.join(invalid_leagues)}")
        logger.info("Use --list-leagues to see available leagues")
        return 1
    
    # Set up output directory
    output_dir = args.output_dir or create_output_directory()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"📁 Output directory: {output_dir}")
    
    # Initialize scraper and start scraping
    scraper = MatchScraper(timeout=args.timeout, max_workers=args.max_workers)
    
    if len(leagues_to_scrape) == 1:
        # Single league
        league_code = leagues_to_scrape[0]
        df = scraper.scrape_league(league_code)
        scraper.save_league_data(league_code, df, output_dir)
    else:
        # Multiple leagues
        results = scraper.scrape_multiple_leagues(leagues_to_scrape)
        
        # Save individual league files
        saved_files = []
        for league_code, df in results.items():
            if not df.empty:
                filepath = scraper.save_league_data(league_code, df, output_dir)
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