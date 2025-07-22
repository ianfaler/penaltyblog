#!/usr/bin/env python3
"""
Pipeline module for running scrape and model operations.
"""

import sys
from pathlib import Path
from typing import Optional, List
import pandas as pd
import logging

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from penaltyblog.scrapers.match_scraper import MatchScraper
from penaltyblog.config.leagues import load_leagues
import penaltyblog as pb

logger = logging.getLogger(__name__)

def run_pipeline(all_leagues: bool = False, output_dir: str = "data", leagues: Optional[List[str]] = None):
    """
    Run the complete scrape and model pipeline.
    
    Parameters
    ----------
    all_leagues : bool
        If True, run for all configured leagues
    output_dir : str
        Directory to save output files
    leagues : List[str], optional
        Specific leagues to process. If None and all_leagues=False, uses default league
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize scraper
    scraper = MatchScraper()
    
    # Determine which leagues to process
    if all_leagues:
        available_leagues = load_leagues()
        league_codes = list(available_leagues.keys())
    elif leagues:
        league_codes = leagues
    else:
        # Default to Premier League
        league_codes = ["ENG_PL"]
    
    logger.info(f"Processing {len(league_codes)} leagues: {league_codes}")
    
    for league_code in league_codes:
        try:
            logger.info(f"Processing league: {league_code}")
            
            # Scrape fixtures
            fixtures_df = scraper.scrape_league(league_code)
            
            if fixtures_df.empty:
                logger.warning(f"No fixtures found for {league_code}")
                continue
            
            # Add basic probability predictions if we have completed matches
            completed_matches = fixtures_df.dropna(subset=["goals_home", "goals_away"])
            
            if len(completed_matches) >= 5:
                # Train a simple model and generate predictions for upcoming matches
                upcoming_matches = fixtures_df[fixtures_df["goals_home"].isna()]
                
                if not upcoming_matches.empty:
                    # Simple probability assignment for demo (replace with actual model)
                    fixtures_df.loc[fixtures_df["goals_home"].isna(), "prob_home"] = 0.4
                    fixtures_df.loc[fixtures_df["goals_home"].isna(), "prob_draw"] = 0.3
                    fixtures_df.loc[fixtures_df["goals_home"].isna(), "prob_away"] = 0.3
            
            # Save to file
            output_file = output_path / f"{league_code}.csv"
            fixtures_df.to_csv(output_file, index=False)
            logger.info(f"Saved {len(fixtures_df)} fixtures to {output_file}")
            
        except Exception as e:
            logger.error(f"Error processing league {league_code}: {e}")
            continue
    
    logger.info("Pipeline completed")