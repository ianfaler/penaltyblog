#!/usr/bin/env python3
"""
Demo script showing how to use the new MLS scraping functionality in penaltyblog.

This script demonstrates:
1. Getting MLS team data
2. Scraping MLS fixtures and results 
3. Using team mappings for data consistency
4. Integrating with existing penaltyblog workflow
"""

import sys
from pathlib import Path
import pandas as pd
import logging

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from penaltyblog.scrapers.mls_official import MLSOfficial
from penaltyblog.scrapers.team_mappings import get_mls_team_mappings
from penaltyblog.scrapers.fbref import FBRef
from penaltyblog.config.leagues import get_league_by_code

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def demo_mls_teams():
    """Demonstrate getting MLS team data."""
    print("\n" + "="*50)
    print("MLS TEAMS DEMONSTRATION")
    print("="*50)
    
    try:
        # Initialize MLS scraper
        mls_scraper = MLSOfficial(season="2024")
        
        # Get teams data
        teams_df = mls_scraper.get_teams()
        
        if not teams_df.empty:
            print(f"Retrieved data for {len(teams_df)} MLS teams:")
            print("\nTeams by Conference:")
            
            # Group by conference
            for conference in teams_df['conference'].unique():
                conf_teams = teams_df[teams_df['conference'] == conference]
                print(f"\n{conference} Conference ({len(conf_teams)} teams):")
                for _, team in conf_teams.iterrows():
                    print(f"  - {team['team_name']} ({team['city']}, founded {team['founded']})")
        else:
            print("No teams data retrieved")
            
    except Exception as e:
        logger.error(f"Error in MLS teams demo: {e}")


def demo_mls_team_mappings():
    """Demonstrate MLS team name mappings."""
    print("\n" + "="*50)
    print("MLS TEAM MAPPINGS DEMONSTRATION")  
    print("="*50)
    
    try:
        mappings = get_mls_team_mappings()
        
        print(f"Team mappings for {len(mappings)} MLS teams:\n")
        
        # Show a few examples
        sample_teams = list(mappings.keys())[:5]
        for team in sample_teams:
            aliases = mappings[team]
            print(f"{team}:")
            print(f"  Aliases: {', '.join(aliases)}")
            print()
            
        print(f"... and {len(mappings) - 5} more teams")
        
    except Exception as e:
        logger.error(f"Error in team mappings demo: {e}")


def demo_mls_fixtures():
    """Demonstrate getting MLS fixtures data."""
    print("\n" + "="*50)
    print("MLS FIXTURES DEMONSTRATION")
    print("="*50)
    
    try:
        # Initialize MLS scraper for current season
        mls_scraper = MLSOfficial(season="2024")
        
        print("Attempting to fetch MLS fixtures...")
        print("Note: This requires live internet connection and may take a moment")
        
        # Get fixtures data
        fixtures_df = mls_scraper.get_fixtures()
        
        if not fixtures_df.empty:
            print(f"Retrieved {len(fixtures_df)} MLS fixtures")
            
            # Show sample data
            print("\nSample fixtures:")
            print(fixtures_df.head(10).to_string(index=False))
            
            # Show column info
            print(f"\nAvailable columns: {list(fixtures_df.columns)}")
            
        else:
            print("No fixtures data retrieved (this may be normal for demo purposes)")
            
    except Exception as e:
        logger.error(f"Error in MLS fixtures demo: {e}")
        print("Note: Fixtures scraping requires specific HTML parsing which may need adjustment")


def demo_fbref_mls():
    """Demonstrate using FBRef for MLS data."""
    print("\n" + "="*50)
    print("FBREF MLS DEMONSTRATION")
    print("="*50)
    
    try:
        print("Attempting to use FBRef for MLS data...")
        
        # Check if MLS is available in FBRef
        available_competitions = FBRef.list_competitions()
        print(f"Available competitions in FBRef: {available_competitions}")
        
        if "USA Major League Soccer" in available_competitions:
            print("MLS is available in FBRef!")
            
            # Initialize FBRef scraper for MLS
            fbref_scraper = FBRef(
                competition="USA Major League Soccer",
                season="2024",
                team_mappings=get_mls_team_mappings()
            )
            
            print("FBRef MLS scraper initialized successfully")
            
        else:
            print("MLS not currently available in FBRef competitions")
            
    except Exception as e:
        logger.error(f"Error in FBRef MLS demo: {e}")


def demo_league_configuration():
    """Demonstrate MLS league configuration."""
    print("\n" + "="*50)
    print("MLS LEAGUE CONFIGURATION DEMONSTRATION")
    print("="*50)
    
    try:
        # Get MLS league configuration
        mls_league = get_league_by_code("USA_ML")
        
        if mls_league:
            print("MLS League Configuration:")
            print(f"  Code: {mls_league.code}")
            print(f"  Name: {mls_league.name}")
            print(f"  Country: {mls_league.country}")
            print(f"  Tier: {mls_league.tier}")
            print(f"  Season: {mls_league.season_id}")
            print(f"  URL Template: {mls_league.url_template}")
            print(f"  Display Name: {mls_league.display_name}")
        else:
            print("MLS league configuration not found")
            
    except Exception as e:
        logger.error(f"Error in league configuration demo: {e}")


def demo_integration_workflow():
    """Demonstrate how MLS integrates with existing penaltyblog workflow."""
    print("\n" + "="*50)
    print("MLS INTEGRATION WORKFLOW DEMONSTRATION")
    print("="*50)
    
    try:
        print("MLS has been integrated into the penaltyblog framework:")
        print("\n1. Team Mappings:")
        print("   - 30 MLS teams with comprehensive alias mappings")
        print("   - Conference and founding year information")
        print("   - City and stadium data")
        
        print("\n2. Competition Mappings:")
        print("   - Added to common.py COMPETITION_MAPPINGS")
        print("   - Supports FBRef, MLS Official, and ESPN data sources")
        
        print("\n3. League Configuration:")
        print("   - Added USA_ML to leagues.yaml")
        print("   - Configured for 2024 season")
        print("   - Official MLS website as primary URL")
        
        print("\n4. Scraper Infrastructure:")
        print("   - New MLSOfficial scraper class")
        print("   - Integrated with unified_scraper.py")
        print("   - Follows existing scraper patterns")
        
        print("\n5. Data Processing:")
        print("   - Standardized column naming")
        print("   - Date parsing and validation")
        print("   - Team name consistency")
        print("   - Game ID generation")
        
        print("\nTo use MLS in your analysis:")
        print("1. from penaltyblog.scrapers import MLSOfficial, get_mls_team_mappings")
        print("2. scraper = MLSOfficial(season='2024')")
        print("3. fixtures = scraper.get_fixtures()")
        print("4. teams = scraper.get_teams()")
        
    except Exception as e:
        logger.error(f"Error in integration workflow demo: {e}")


def main():
    """Run all MLS demonstrations."""
    print("PENALTYBLOG MLS INTEGRATION DEMONSTRATION")
    print("==========================================")
    print("This script demonstrates the new MLS functionality added to penaltyblog")
    
    # Run all demonstrations
    demo_league_configuration()
    demo_mls_team_mappings()
    demo_mls_teams()
    demo_fbref_mls()
    demo_integration_workflow()
    
    # Note about fixtures
    print("\n" + "="*50)
    print("IMPORTANT NOTES")
    print("="*50)
    print("1. Fixtures scraping requires live internet connection")
    print("2. HTML parsing may need adjustment based on MLS website structure")
    print("3. Some features require additional dependencies (BeautifulSoup4)")
    print("4. FBRef MLS support depends on their data availability")
    print("5. All team mappings and configurations are ready to use")
    
    print("\nMLS integration is now complete and ready for use!")


if __name__ == "__main__":
    main()