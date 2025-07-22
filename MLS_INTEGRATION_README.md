# MLS Integration for PenaltyBlog

This document describes the comprehensive MLS (Major League Soccer) integration added to the PenaltyBlog framework.

## Overview

The MLS integration provides:
- **Complete team data** for all 30 MLS teams (2025 season with San Diego FC)
- **Team name mappings** with aliases and abbreviations  
- **Scraping infrastructure** for MLS data sources
- **League configuration** integrated with existing framework
- **Data standardization** following PenaltyBlog patterns

## Features Added

### 1. Team Mappings (`penaltyblog/scrapers/team_mappings.py`)

```python
from penaltyblog.scrapers import get_mls_team_mappings

# Get comprehensive MLS team mappings
mls_teams = get_mls_team_mappings()
```

**Teams included (30 total):**

**Eastern Conference (15 teams):**
- Atlanta United FC
- Charlotte FC  
- Chicago Fire FC
- FC Cincinnati
- Columbus Crew
- D.C. United
- Inter Miami CF
- CF Montréal
- Nashville SC
- New England Revolution
- New York City FC
- New York Red Bulls
- Orlando City SC
- Philadelphia Union
- Toronto FC

**Western Conference (15 teams):**
- Austin FC
- Colorado Rapids
- FC Dallas
- Houston Dynamo FC
- LA Galaxy
- Los Angeles FC
- Minnesota United FC
- Portland Timbers
- Real Salt Lake
- San Diego FC (new 2025 expansion team)
- San Jose Earthquakes
- Seattle Sounders FC
- Sporting Kansas City
- St. Louis City SC
- Vancouver Whitecaps FC

Each team includes comprehensive aliases (e.g., "Atlanta United FC": ["Atlanta United", "ATL", "Atlanta", "ATLUTD"]).

### 2. MLS Official Scraper (`penaltyblog/scrapers/mls_official.py`)

```python
from penaltyblog.scrapers import MLSOfficial

# Initialize scraper
scraper = MLSOfficial(season="2024")

# Get teams data
teams_df = scraper.get_teams()

# Get fixtures/results
fixtures_df = scraper.get_fixtures()
```

**Features:**
- Official MLS website scraping
- Team metadata (conference, founding year, city)
- Fixtures and results parsing
- Standardized data output
- Robust error handling

### 3. League Configuration (`penaltyblog/config/leagues.yaml`)

MLS is configured as:
```yaml
USA_ML:
  name: "MLS"
  country: "United States"
  tier: 1
  season_id: "2024"
  url_template: "https://www.mlssoccer.com/schedule"
```

Access via:
```python
from penaltyblog.config.leagues import get_league_by_code

mls_league = get_league_by_code("USA_ML")
print(f"{mls_league.display_name}: {mls_league.url_template}")
```

### 4. Competition Mappings (`penaltyblog/scrapers/common.py`)

MLS added to `COMPETITION_MAPPINGS`:
```python
"USA Major League Soccer": {
    "fbref": {
        "slug": "22",
        "stats": ["standard", "goalkeeping", "advanced_goalkeeping", 
                 "shooting", "passing", "passing_types", 
                 "goal_shot_creation", "defensive_actions", 
                 "possession", "playing_time", "misc"],
    },
    "mls_official": {"base_url": "https://www.mlssoccer.com"},
    "espn": {"slug": "usa.1"},
}
```

### 5. Unified Scraper Integration (`penaltyblog/scrapers/unified_scraper.py`)

MLS integrated into the unified scraping framework:
```python
LEAGUE_TO_COMPETITION = {
    # ... existing leagues ...
    "USA_ML": "USA Major League Soccer",
}
```

## Usage Examples

### Basic Team Information

```python
from penaltyblog.scrapers import MLSOfficial

# Initialize scraper
mls = MLSOfficial(season="2024")

# Get all teams
teams = mls.get_teams()

# Filter by conference
eastern_teams = teams[teams['conference'] == 'Eastern']
western_teams = teams[teams['conference'] == 'Western']

# Get specific team info
inter_miami = teams[teams['team_name'] == 'Inter Miami CF']
print(f"Founded: {inter_miami.iloc[0]['founded']}")
print(f"City: {inter_miami.iloc[0]['city']}")
```

### Team Name Mapping

```python
from penaltyblog.scrapers import get_mls_team_mappings

# Get mappings for data consistency
mappings = get_mls_team_mappings()

# Check aliases for a team
atlanta_aliases = mappings["Atlanta United FC"]
print(f"Atlanta United aliases: {atlanta_aliases}")
# Output: ['Atlanta United', 'ATL', 'Atlanta', 'ATLUTD']
```

### Using with FBRef

```python
from penaltyblog.scrapers import FBRef, get_mls_team_mappings

# Check if MLS is available in FBRef
if "USA Major League Soccer" in FBRef.list_competitions():
    # Initialize with MLS team mappings
    fbref = FBRef(
        competition="USA Major League Soccer",
        season="2024", 
        team_mappings=get_mls_team_mappings()
    )
    
    # Get fixtures
    fixtures = fbref.get_fixtures()
```

### Integration with Existing Workflow

```python
from penaltyblog.scrapers.unified_scraper import UnifiedScraper

# Use unified scraper for MLS
scraper = UnifiedScraper()
mls_data = scraper.scrape_league("USA_ML", season="2024")
```

## Data Structure

### Teams DataFrame Columns

- `team_name`: Official team name
- `aliases`: List of alternative names/abbreviations
- `conference`: "Eastern" or "Western"
- `founded`: Year team was founded
- `city`: Primary city location

### Fixtures DataFrame Columns

- `team_home`: Home team name
- `team_away`: Away team name  
- `date`: Match date (standardized format)
- `goals_home`: Home team goals (if available)
- `goals_away`: Away team goals (if available)
- `status`: Match status
- `id`: Unique game identifier

## Installation Requirements

The MLS integration requires:
- `pandas` (for data handling)
- `requests` (for web scraping)
- `beautifulsoup4` (for HTML parsing) - optional but recommended

Install via:
```bash
pip install pandas requests beautifulsoup4
```

## Testing

Run the MLS integration tests:
```bash
python test/test_mls_integration.py
```

Or run the demonstration script:
```bash
python examples/demo_mls_scraping.py
```

## Data Sources

The integration supports multiple data sources:

1. **Official MLS Website** (`mlssoccer.com`)
   - Primary source for schedules and results
   - Most up-to-date information
   - Direct from league

2. **FBRef** (if available)
   - Advanced statistics
   - Historical data
   - International coverage

3. **ESPN** 
   - Alternative data source
   - Broadcast schedules
   - News integration

## Conference Structure (2025)

**Eastern Conference:**
- 15 teams after league expansion
- Includes major markets: New York, Miami, Atlanta, Toronto

**Western Conference:**  
- 15 teams including new San Diego FC
- Covers Pacific, Mountain, and Central time zones
- Includes Los Angeles rivalry (Galaxy vs LAFC)

## Historical Context

- **MLS Founded:** 1996 (29th season in 2024)
- **Original Teams:** 10 teams in 1996
- **Current Teams:** 30 teams (as of 2025)
- **Recent Expansion:** San Diego FC joined in 2025
- **Future Growth:** League targeting 32+ teams

## Key Features

1. **Comprehensive Coverage:** All 30 teams with complete metadata
2. **Data Consistency:** Standardized team names and aliases
3. **Multiple Sources:** Support for various data providers
4. **Conference Aware:** Proper Eastern/Western conference assignment  
5. **Future Ready:** Designed to accommodate league expansion
6. **Integration:** Seamlessly works with existing PenaltyBlog infrastructure

## Configuration

The MLS integration is configured in several key files:

- `penaltyblog/config/leagues.yaml` - League definitions
- `penaltyblog/scrapers/common.py` - Competition mappings  
- `penaltyblog/scrapers/team_mappings.py` - Team name mappings
- `penaltyblog/scrapers/mls_official.py` - MLS-specific scraper
- `penaltyblog/scrapers/unified_scraper.py` - Integration layer

## Maintenance

To update the MLS integration:

1. **New Teams:** Add to `mls_team_mappings` in `team_mappings.py`
2. **Team Changes:** Update aliases and metadata as needed
3. **New Season:** Update `season_id` in `leagues.yaml`  
4. **Data Sources:** Add new scrapers to `common.py` mappings

## Support

For issues with MLS integration:

1. Check test suite: `python test/test_mls_integration.py`
2. Run demo script: `python examples/demo_mls_scraping.py`
3. Verify league configuration: `get_league_by_code("USA_ML")`
4. Check team mappings: `get_mls_team_mappings()`

The MLS integration is now fully operational and ready for use in your football analytics projects!