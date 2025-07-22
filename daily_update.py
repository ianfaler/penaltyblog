#!/usr/bin/env python3
"""
Daily Schedule Update Script - FIXED VERSION
===========================================

This script fetches REAL data from proven sources and fails explicitly 
if data cannot be retrieved, rather than generating fake data.

CRITICAL FIXES:
- Removed demo data generation in production
- Added proper error handling that fails explicitly
- Added temporal validation to reject completed results for future dates
- Ensures scrapers actually connect to real data sources

"""

import sys
import logging
import pandas as pd
from datetime import datetime, timedelta, date
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def get_current_monday():
    """Get the current Monday's date."""
    today = datetime.now().date()
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    return monday

def validate_temporal_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate temporal data - reject completed results for future dates.
    
    This is a critical fix to prevent fake data from being accepted.
    """
    if df.empty:
        return df
    
    # Convert date column to datetime if it exists
    if 'date' in df.columns:
        df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')
        current_date = datetime.now().date()
        
        # Find future dates with completed results
        future_mask = df['date_parsed'].dt.date > current_date
        completed_mask = df['goals_home'].notna() & df['goals_away'].notna()
        invalid_future_results = future_mask & completed_mask
        
        if invalid_future_results.any():
            invalid_count = invalid_future_results.sum()
            logger.error(f"TEMPORAL VALIDATION FAILED: Found {invalid_count} completed results for future dates")
            logger.error("This indicates fake/demo data. Rejecting entire dataset.")
            
            # Log the problematic entries
            problematic = df[invalid_future_results][['date', 'team_home', 'team_away', 'goals_home', 'goals_away']]
            logger.error(f"Problematic entries:\n{problematic.to_string()}")
            
            raise ValueError(f"Temporal validation failed: {invalid_count} future completed results detected")
        
        # Remove the temporary column
        df = df.drop('date_parsed', axis=1)
    
    return df

def fetch_real_data_from_scrapers():
    """
    Fetch real data using the unified scraper system.
    
    This replaces the old demo data generation with actual scraping.
    """
    try:
        from penaltyblog.scrapers.unified_scraper import UnifiedScraper
        
        logger.info("🔄 Fetching real data from proven sources...")
        scraper = UnifiedScraper(season="2024-25")
        
        # Try Premier League first as default
        df = scraper.scrape_league("ENG_PL", preferred_source="fbref")
        
        if df.empty:
            logger.error("Failed to fetch data from unified scraper")
            return pd.DataFrame()
        
        logger.info(f"✅ Successfully fetched {len(df)} fixtures from real sources")
        
        # Apply temporal validation
        df = validate_temporal_data(df)
        
        return df
        
    except Exception as e:
        logger.error(f"❌ Real data scraping failed: {e}")
        return pd.DataFrame()

def archive_old_data():
    """Archive old data files."""
    data_dir = Path("data")
    if not data_dir.exists():
        data_dir.mkdir(parents=True)
        return
    
    # Archive files older than 7 days
    cutoff_date = datetime.now() - timedelta(days=7)
    
    for csv_file in data_dir.glob("*.csv"):
        if csv_file.stat().st_mtime < cutoff_date.timestamp():
            archive_dir = data_dir / "archive"
            archive_dir.mkdir(exist_ok=True)
            
            archived_path = archive_dir / csv_file.name
            csv_file.rename(archived_path)
            logger.info(f"📦 Archived old file: {csv_file.name}")

def update_schedule():
    """
    Main function to update the schedule with REAL data only.
    
    CRITICAL CHANGES:
    - No demo data generation
    - Explicit failure when real data unavailable
    - Temporal validation enforced
    """
    print("🔄 Running daily schedule update with REAL data only...")
    
    # Archive old files
    archive_old_data()
    
    # Fetch real data - NO FALLBACK TO FAKE DATA
    real_data = fetch_real_data_from_scrapers()
    
    if real_data.empty:
        print("❌ CRITICAL FAILURE: No real data available")
        print("❌ Refusing to generate fake data in production")
        print("❌ Please check data source connections")
        print("❌ System will continue with existing data if available")
        return None
    
    # Validate data quality
    if len(real_data) < 10:
        logger.warning(f"⚠️  Low data volume: only {len(real_data)} fixtures")
        print("⚠️  Warning: Limited real data available")
    
    # Get current week's data if applicable
    current_week_data = real_data
    
    # Filter for current/upcoming matches only
    if 'date' in current_week_data.columns:
        current_week_data['date_parsed'] = pd.to_datetime(current_week_data['date'], errors='coerce')
        today = datetime.now().date()
        
        # Include matches from today onwards for the next 7 days
        start_date = today
        end_date = today + timedelta(days=7)
        
        date_mask = (
            (current_week_data['date_parsed'].dt.date >= start_date) &
            (current_week_data['date_parsed'].dt.date <= end_date)
        )
        
        current_week_data = current_week_data[date_mask].drop('date_parsed', axis=1)
    
    if current_week_data.empty:
        print("❌ No upcoming fixtures found in real data")
        print("❌ This may be normal during off-season")
        return None
    
    # Save to CSV with current Monday's date
    monday = get_current_monday()
    filename = f"data/{monday.strftime('%Y-%m-%d')}.csv"
    
    # Ensure data directory exists
    Path("data").mkdir(parents=True, exist_ok=True)
    
    current_week_data.to_csv(filename, index=False)
    
    print(f"✅ Real data saved to: {filename}")
    print(f"📅 Week of: {monday.strftime('%Y-%m-%d')} to {(monday + timedelta(days=6)).strftime('%Y-%m-%d')}")
    print(f"🏈 Processed {len(current_week_data)} REAL fixtures")
    
    # Display sample
    if not current_week_data.empty:
        print("\n📋 Sample REAL fixtures:")
        display_cols = ['date', 'home', 'away']
        # Use available columns
        available_cols = [col for col in display_cols if col in current_week_data.columns]
        if not available_cols:
            available_cols = list(current_week_data.columns)[:3]  # First 3 columns
        
        sample_df = current_week_data.head(5)[available_cols]
        print(sample_df.to_string(index=False))
    
    print("\n🎯 SUCCESS: Using REAL data from proven sources!")
    print("📊 Data Source: FBRef/Understat/Football-Data")
    print("✅ No fake data generation in production")
    
    return filename

if __name__ == "__main__":
    try:
        result = update_schedule()
        if result:
            print(f"\n✅ Daily update completed successfully: {result}")
        else:
            print("\n❌ Daily update failed - no real data available")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Daily update failed with error: {e}")
        logger.error(f"Daily update failed: {e}")
        sys.exit(1)