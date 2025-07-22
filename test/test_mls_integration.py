#!/usr/bin/env python3
"""
Test suite for MLS integration in penaltyblog.

This test file verifies:
1. MLS team mappings are properly configured
2. MLS scraper initializes correctly  
3. League configuration is properly set up
4. Integration with existing framework works
"""

import unittest
import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from penaltyblog.scrapers.team_mappings import get_mls_team_mappings
from penaltyblog.scrapers.mls_official import MLSOfficial
from penaltyblog.scrapers.common import COMPETITION_MAPPINGS
from penaltyblog.config.leagues import get_league_by_code


class TestMLSIntegration(unittest.TestCase):
    """Test cases for MLS integration."""
    
    def test_mls_team_mappings(self):
        """Test that MLS team mappings are properly configured."""
        mappings = get_mls_team_mappings()
        
        # Should have 30 teams (as of 2025 with San Diego FC)
        self.assertEqual(len(mappings), 30, "Should have 30 MLS teams")
        
        # Check that all teams have aliases
        for team, aliases in mappings.items():
            self.assertIsInstance(team, str, f"Team name {team} should be string")
            self.assertIsInstance(aliases, list, f"Aliases for {team} should be list")
            self.assertGreater(len(aliases), 0, f"Team {team} should have at least one alias")
        
        # Check for specific known teams
        expected_teams = [
            "Inter Miami CF",
            "LA Galaxy", 
            "Seattle Sounders FC",
            "Atlanta United FC",
            "New York City FC",
            "San Diego FC"  # New 2025 expansion team
        ]
        
        for team in expected_teams:
            self.assertIn(team, mappings, f"Expected team {team} not found in mappings")
    
    def test_mls_competition_mapping(self):
        """Test that MLS is properly added to competition mappings."""
        self.assertIn("USA Major League Soccer", COMPETITION_MAPPINGS,
                      "MLS should be in competition mappings")
        
        mls_mapping = COMPETITION_MAPPINGS["USA Major League Soccer"]
        
        # Should have FBRef mapping
        self.assertIn("fbref", mls_mapping, "MLS should have FBRef mapping")
        self.assertIn("slug", mls_mapping["fbref"], "FBRef mapping should have slug")
        self.assertIn("stats", mls_mapping["fbref"], "FBRef mapping should have stats")
        
        # Should have MLS official mapping
        self.assertIn("mls_official", mls_mapping, "MLS should have official source mapping")
        
        # Should have ESPN mapping  
        self.assertIn("espn", mls_mapping, "MLS should have ESPN mapping")
    
    def test_mls_league_configuration(self):
        """Test that MLS league is properly configured."""
        mls_league = get_league_by_code("USA_ML")
        
        self.assertIsNotNone(mls_league, "MLS league should be found by code USA_ML")
        self.assertEqual(mls_league.code, "USA_ML", "League code should be USA_ML")
        self.assertEqual(mls_league.name, "MLS", "League name should be MLS")
        self.assertEqual(mls_league.country, "United States", "Country should be United States")
        self.assertEqual(mls_league.tier, 1, "MLS should be tier 1")
        self.assertIn("mlssoccer.com", mls_league.url_template, 
                      "URL template should reference official MLS site")
    
    def test_mls_scraper_initialization(self):
        """Test that MLS scraper initializes correctly."""
        # Test initialization with default team mappings
        scraper = MLSOfficial(season="2024")
        
        self.assertEqual(scraper.season, "2024", "Season should be set correctly")
        self.assertEqual(scraper.source, "mls_official", "Source should be mls_official")
        self.assertIsNotNone(scraper.team_mappings, "Team mappings should be initialized")
        
        # Test with custom team mappings
        custom_mappings = {"Test Team": ["Test", "TT"]}
        scraper_custom = MLSOfficial(season="2024", team_mappings=custom_mappings)
        
        # Should create reverse mapping
        self.assertIn("Test", scraper_custom.team_mappings, 
                      "Custom mappings should be processed")
    
    def test_mls_scraper_competitions(self):
        """Test that MLS scraper reports correct competitions."""
        competitions = MLSOfficial.list_competitions()
        
        self.assertIsInstance(competitions, list, "Competitions should be a list")
        self.assertIn("USA Major League Soccer", competitions, 
                      "MLS should be in supported competitions")
    
    def test_teams_data_structure(self):
        """Test that MLS teams data has correct structure."""
        scraper = MLSOfficial(season="2024")
        teams_df = scraper.get_teams()
        
        self.assertFalse(teams_df.empty, "Teams dataframe should not be empty")
        
        # Check required columns
        expected_columns = ['team_name', 'aliases', 'conference', 'founded', 'city']
        for col in expected_columns:
            self.assertIn(col, teams_df.columns, f"Teams data should have {col} column")
        
        # Check conferences
        conferences = teams_df['conference'].unique()
        self.assertIn("Eastern", conferences, "Should have Eastern conference teams")
        self.assertIn("Western", conferences, "Should have Western conference teams")
        
        # Check that we have the right number of teams
        self.assertEqual(len(teams_df), 30, "Should have 30 teams total")
        
        # Check conference distribution (15 teams each in 2025)
        eastern_count = len(teams_df[teams_df['conference'] == 'Eastern'])
        western_count = len(teams_df[teams_df['conference'] == 'Western'])
        self.assertEqual(eastern_count, 15, "Should have 15 Eastern conference teams")
        self.assertEqual(western_count, 15, "Should have 15 Western conference teams")
    
    def test_team_metadata(self):
        """Test team metadata like founding years and cities."""
        scraper = MLSOfficial(season="2024")
        teams_df = scraper.get_teams()
        
        # Check some specific team data
        inter_miami = teams_df[teams_df['team_name'] == 'Inter Miami CF']
        self.assertFalse(inter_miami.empty, "Inter Miami should be in teams data")
        self.assertEqual(inter_miami.iloc[0]['founded'], 2020, "Inter Miami founded in 2020")
        
        san_diego = teams_df[teams_df['team_name'] == 'San Diego FC']
        self.assertFalse(san_diego.empty, "San Diego FC should be in teams data")
        self.assertEqual(san_diego.iloc[0]['founded'], 2025, "San Diego FC founded in 2025")
        
        # Check that all teams have founding years
        founded_years = teams_df['founded'].dropna()
        self.assertEqual(len(founded_years), len(teams_df), 
                         "All teams should have founding years")
        
        # Check that founding years are reasonable (between 1996 and 2025)
        self.assertTrue(all(1996 <= year <= 2025 for year in founded_years),
                        "All founding years should be between 1996 and 2025")


class TestMLSIntegrationImports(unittest.TestCase):
    """Test that MLS components can be imported correctly."""
    
    def test_import_mls_scraper(self):
        """Test importing MLS scraper."""
        try:
            from penaltyblog.scrapers import MLSOfficial
            self.assertTrue(True, "MLSOfficial should be importable")
        except ImportError as e:
            self.fail(f"Failed to import MLSOfficial: {e}")
    
    def test_import_mls_team_mappings(self):
        """Test importing MLS team mappings."""
        try:
            from penaltyblog.scrapers import get_mls_team_mappings
            mappings = get_mls_team_mappings()
            self.assertIsInstance(mappings, dict, "Should return dictionary")
        except ImportError as e:
            self.fail(f"Failed to import get_mls_team_mappings: {e}")
    
    def test_unified_scraper_includes_mls(self):
        """Test that unified scraper includes MLS support."""
        try:
            # Import the unified scraper module
            from penaltyblog.scrapers import unified_scraper
            
            # Check that MLS league mapping exists
            self.assertIn("USA_ML", unified_scraper.LEAGUE_TO_COMPETITION,
                          "Unified scraper should include MLS mapping")
            
            expected_competition = "USA Major League Soccer"
            actual_competition = unified_scraper.LEAGUE_TO_COMPETITION["USA_ML"]
            self.assertEqual(actual_competition, expected_competition,
                           "MLS should map to correct competition name")
            
        except ImportError as e:
            self.fail(f"Failed to import unified_scraper: {e}")


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)