"""Tests for the match scraper functionality."""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from penaltyblog.scrapers.match_scraper import MatchScraper, parse_league_list, create_output_directory
from penaltyblog.scrapers.parsers import (
    parse_html_to_dataframe, 
    is_fixture_table, 
    normalize_fixture_dataframe,
    clean_fixture_data,
    merge_fixture_dataframes
)
from penaltyblog.config.leagues import load_leagues, get_league_by_code

class TestParsers:
    """Test the HTML parsing utilities."""
    
    def test_is_fixture_table_valid(self):
        """Test identification of valid fixture tables."""
        # Create a DataFrame that looks like fixtures
        df = pd.DataFrame({
            'Date': ['2024-01-15', '2024-01-16'],
            'Home': ['Team A', 'Team C'],
            'Away': ['Team B', 'Team D'],
            'Result': ['2-1', '0-0']
        })
        
        assert is_fixture_table(df) == True
    
    def test_is_fixture_table_invalid(self):
        """Test identification of invalid fixture tables."""
        # Create a DataFrame that doesn't look like fixtures
        df = pd.DataFrame({
            'Column1': ['data1', 'data2'],
            'Column2': ['data3', 'data4']
        })
        
        assert is_fixture_table(df) == False
    
    def test_is_fixture_table_empty(self):
        """Test handling of empty DataFrames."""
        df = pd.DataFrame()
        assert is_fixture_table(df) == False
    
    def test_normalize_fixture_dataframe(self):
        """Test normalization of fixture DataFrames."""
        # Create a DataFrame with various column names
        df = pd.DataFrame({
            'match_date': ['2024-01-15', '2024-01-16'],
            'team_home': ['Team A', 'Team C'],
            'team_away': ['Team B', 'Team D'],
            'goals_home': [2, 0],
            'goals_away': [1, 0]
        })
        
        normalized = normalize_fixture_dataframe(df)
        
        # Check that columns are properly renamed
        assert 'date' in normalized.columns
        assert 'home' in normalized.columns
        assert 'away' in normalized.columns
        assert 'home_score' in normalized.columns
        assert 'away_score' in normalized.columns
    
    def test_clean_fixture_data(self):
        """Test cleaning of fixture data."""
        df = pd.DataFrame({
            'date': ['2024-01-15', '2024-01-16', None],
            'home': ['Team A', 'Team C', 'Team E'],
            'away': ['Team B', 'Team D', None],
            'home_score': ['2', '0', 'invalid'],
            'away_score': ['1', '0', '1']
        })
        
        cleaned = clean_fixture_data(df)
        
        # Check that rows with missing essential data are removed
        assert len(cleaned) == 2
        # Check that scores are converted to numeric
        assert cleaned['home_score'].dtype in ['int64', 'float64']
    
    def test_merge_fixture_dataframes(self):
        """Test merging of multiple fixture DataFrames."""
        df1 = pd.DataFrame({
            'date': ['2024-01-15'],
            'home': ['Team A'],
            'away': ['Team B'],
            'home_score': [2],
            'away_score': [1]
        })
        
        df2 = pd.DataFrame({
            'date': ['2024-01-16'],
            'home': ['Team C'],
            'away': ['Team D'],
            'home_score': [0],
            'away_score': [0]
        })
        
        merged = merge_fixture_dataframes([df1, df2])
        
        assert len(merged) == 2
        assert 'date' in merged.columns
    
    def test_parse_html_simple_table(self):
        """Test parsing of simple HTML table."""
        html = """
        <table>
            <tr><th>Date</th><th>Home</th><th>Away</th><th>Score</th></tr>
            <tr><td>2024-01-15</td><td>Team A</td><td>Team B</td><td>2-1</td></tr>
            <tr><td>2024-01-16</td><td>Team C</td><td>Team D</td><td>0-0</td></tr>
        </table>
        """
        
        df = parse_html_to_dataframe(html)
        
        # Should return a DataFrame (even if empty due to parsing limitations)
        assert isinstance(df, pd.DataFrame)
    
    def test_parse_html_empty(self):
        """Test parsing of empty HTML."""
        html = "<html><body></body></html>"
        
        df = parse_html_to_dataframe(html)
        
        # Should return empty DataFrame with correct structure
        assert isinstance(df, pd.DataFrame)
        expected_columns = ['date', 'home', 'away', 'home_score', 'away_score', 'xg_home', 'xg_away']
        assert all(col in df.columns for col in expected_columns)

class TestMatchScraper:
    """Test the MatchScraper class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scraper = MatchScraper(timeout=5, max_workers=2)
    
    @patch('penaltyblog.scrapers.match_scraper.get_league_by_code')
    def test_scrape_league_not_found(self, mock_get_league):
        """Test scraping with invalid league code."""
        mock_get_league.return_value = None
        
        result = self.scraper.scrape_league('INVALID')
        
        assert result.empty
    
    @patch('penaltyblog.scrapers.match_scraper.get_league_by_code')
    @patch('requests.Session.get')
    def test_scrape_league_success(self, mock_get, mock_get_league):
        """Test successful league scraping."""
        # Mock league
        mock_league = Mock()
        mock_league.display_name = "Test League"
        mock_league.name = "Test League"
        mock_league.country = "Test Country"
        mock_league.get_url.return_value = "http://example.com"
        mock_get_league.return_value = mock_league
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.text = "<html><body>No matches</body></html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.scraper.scrape_league('TEST')
        
        # Should return DataFrame (possibly empty)
        assert isinstance(result, pd.DataFrame)
        mock_get.assert_called_once()
    
    @patch('penaltyblog.scrapers.match_scraper.get_league_by_code')
    @patch('requests.Session.get')
    def test_scrape_league_network_error(self, mock_get, mock_get_league):
        """Test handling of network errors."""
        # Mock league
        mock_league = Mock()
        mock_league.display_name = "Test League"
        mock_league.get_url.return_value = "http://example.com"
        mock_get_league.return_value = mock_league
        
        # Mock network error
        mock_get.side_effect = Exception("Network error")
        
        result = self.scraper.scrape_league('TEST')
        
        # Should return empty DataFrame on error
        assert result.empty
    
    def test_parse_league_list(self):
        """Test parsing of league list strings."""
        # Test normal case
        result = parse_league_list("ENG_PL,ESP_LL,GER_BL")
        assert result == ['ENG_PL', 'ESP_LL', 'GER_BL']
        
        # Test with spaces
        result = parse_league_list("ENG_PL, ESP_LL , GER_BL")
        assert result == ['ENG_PL', 'ESP_LL', 'GER_BL']
        
        # Test empty string
        result = parse_league_list("")
        assert result == []
        
        # Test None
        result = parse_league_list(None)
        assert result == []
    
    def test_create_output_directory(self):
        """Test creation of output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory
            original_cwd = Path.cwd()
            temp_path = Path(temp_dir)
            
            # Create a data directory in temp location
            data_dir = temp_path / "data"
            
            # Mock Path("data") to return our temp data dir
            with patch('pathlib.Path') as mock_path:
                mock_path.return_value = data_dir
                
                output_dir = create_output_directory()
                
                # Should create directory with today's date
                assert output_dir.name.startswith('20')  # Year starts with 20
                assert len(output_dir.name) == 10  # YYYY-MM-DD format

class TestLeagueIntegration:
    """Test integration with league configuration."""
    
    def test_load_leagues(self):
        """Test loading of league configuration."""
        leagues = load_leagues()
        
        # Should load leagues from YAML
        assert isinstance(leagues, dict)
        assert len(leagues) > 0
        
        # Check that ENG_PL exists (Premier League)
        assert 'ENG_PL' in leagues
        
        # Check league structure
        pl = leagues['ENG_PL']
        assert pl.name == "Premier League"
        assert pl.country == "England"
        assert pl.tier == 1
    
    def test_get_league_by_code(self):
        """Test getting specific league by code."""
        league = get_league_by_code('ENG_PL')
        
        assert league is not None
        assert league.name == "Premier League"
        assert league.country == "England"
    
    def test_get_league_by_code_invalid(self):
        """Test getting invalid league code."""
        league = get_league_by_code('INVALID_CODE')
        
        assert league is None

@pytest.mark.integration
class TestEndToEndScraping:
    """Integration tests for end-to-end scraping."""
    
    def test_scraper_with_mock_data(self):
        """Test scraper with mocked HTML data."""
        # Create a mock HTML response that looks like a fixture page
        mock_html = """
        <html>
        <body>
            <div class="fixture">
                <span>2024-01-15</span>
                <span>Team A</span>
                <span>2-1</span>
                <span>Team B</span>
            </div>
            <div class="fixture">
                <span>2024-01-16</span>
                <span>Team C</span>
                <span>0-0</span>
                <span>Team D</span>
            </div>
        </body>
        </html>
        """
        
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.text = mock_html
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            scraper = MatchScraper()
            result = scraper.scrape_league('ENG_PL')
            
            # Should return a DataFrame
            assert isinstance(result, pd.DataFrame)
    
    def test_save_league_data(self):
        """Test saving league data to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test DataFrame
            df = pd.DataFrame({
                'date': ['2024-01-15'],
                'home': ['Team A'],
                'away': ['Team B'],
                'home_score': [2],
                'away_score': [1],
                'league_code': ['ENG_PL'],
                'league_name': ['Premier League'],
                'country': ['England']
            })
            
            scraper = MatchScraper()
            result_path = scraper.save_league_data('ENG_PL', df, temp_path)
            
            # Check that file was created
            assert result_path is not None
            assert result_path.exists()
            
            # Check file contents
            saved_df = pd.read_csv(result_path)
            assert len(saved_df) == 1
            assert saved_df.iloc[0]['home'] == 'Team A'