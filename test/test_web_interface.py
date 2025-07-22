"""Tests for the web interface functionality."""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from penaltyblog.web import app

class TestWebInterface:
    """Test the FastAPI web interface."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
    
    def test_root_endpoint(self):
        """Test the root endpoint returns HTML."""
        response = self.client.get("/")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "PenaltyBlog" in response.text
        assert "League:" in response.text  # Should contain league dropdown
    
    @patch('penaltyblog.web.find_league_csv')
    @patch('pandas.read_csv')
    def test_data_endpoint_no_league(self, mock_read_csv, mock_find_csv):
        """Test the data endpoint without league filter."""
        # Mock CSV data
        mock_df = pd.DataFrame({
            'date': ['2024-01-15', '2024-01-16'],
            'home': ['Team A', 'Team C'],
            'away': ['Team B', 'Team D'],
            'home_score': [2, 0],
            'away_score': [1, 0]
        })
        mock_read_csv.return_value = mock_df
        mock_find_csv.return_value = Path("/fake/path.csv")
        
        response = self.client.get("/data")
        
        assert response.status_code == 200
        assert "Team A" in response.text
        assert "Team B" in response.text
    
    @patch('penaltyblog.web.find_league_csv')
    @patch('pandas.read_csv')
    def test_data_endpoint_with_league(self, mock_read_csv, mock_find_csv):
        """Test the data endpoint with league filter."""
        # Mock CSV data with league codes
        mock_df = pd.DataFrame({
            'date': ['2024-01-15', '2024-01-16'],
            'home': ['Team A', 'Team C'],
            'away': ['Team B', 'Team D'],
            'home_score': [2, 0],
            'away_score': [1, 0],
            'league_code': ['ENG_PL', 'ESP_LL'],
            'league_name': ['Premier League', 'La Liga'],
            'country': ['England', 'Spain']
        })
        mock_read_csv.return_value = mock_df
        mock_find_csv.return_value = Path("/fake/path.csv")
        
        response = self.client.get("/data?league=ENG_PL")
        
        assert response.status_code == 200
        # Should only contain Premier League data
        assert "Team A" in response.text
        assert "Team C" not in response.text  # This is ESP_LL data
    
    @patch('penaltyblog.web.find_league_csv')
    @patch('pandas.read_csv')
    def test_data_json_endpoint(self, mock_read_csv, mock_find_csv):
        """Test the JSON data endpoint."""
        # Mock CSV data
        mock_df = pd.DataFrame({
            'date': ['2024-01-15'],
            'home': ['Team A'],
            'away': ['Team B'],
            'home_score': [2],
            'away_score': [1]
        })
        mock_read_csv.return_value = mock_df
        mock_find_csv.return_value = Path("/fake/path.csv")
        
        response = self.client.get("/data/json")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        assert len(data) == 1
        assert data[0]['home'] == 'Team A'
    
    def test_status_endpoint(self):
        """Test the status endpoint."""
        with patch('penaltyblog.web.latest_csv') as mock_latest:
            with patch('pandas.read_csv') as mock_read:
                # Mock file and data
                mock_file = Path("/fake/path.csv")
                mock_file.stat = Mock()
                mock_file.stat.return_value.st_mtime = 1234567890
                mock_file.name = "test.csv"
                mock_latest.return_value = mock_file
                
                mock_df = pd.DataFrame({
                    'date': ['2024-01-15', '2024-01-16'],
                    'home': ['Team A', 'Team C'],
                    'away': ['Team B', 'Team D']
                })
                mock_read.return_value = mock_df
                
                response = self.client.get("/status")
                
                assert response.status_code == 200
                data = response.json()
                
                assert 'data_file' in data
                assert 'total_fixtures' in data
                assert data['total_fixtures'] == 2
    
    def test_leagues_endpoint(self):
        """Test the leagues endpoint."""
        with patch('penaltyblog.web.load_leagues') as mock_load:
            with patch('penaltyblog.web.get_available_leagues_from_data') as mock_available:
                # Mock leagues
                from penaltyblog.config.leagues import League
                
                mock_leagues = {
                    'ENG_PL': League('ENG_PL', 'Premier League', 'England', 1, '2024-25', 'http://example.com'),
                    'ESP_LL': League('ESP_LL', 'La Liga', 'Spain', 1, '2024-25', 'http://example.com')
                }
                mock_load.return_value = mock_leagues
                mock_available.return_value = ['ENG_PL']
                
                response = self.client.get("/leagues")
                
                assert response.status_code == 200
                data = response.json()
                
                assert 'total_configured' in data
                assert 'total_with_data' in data
                assert 'leagues' in data
                assert data['total_configured'] == 2
                assert data['total_with_data'] == 1
    
    @patch('subprocess.run')
    def test_scrape_endpoint_success(self, mock_run):
        """Test the scrape endpoint with successful execution."""
        # Mock successful subprocess
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "✅ Successfully scraped 10 matches"
        mock_run.return_value = mock_result
        
        response = self.client.get("/scrape")
        
        assert response.status_code == 200
        assert "✅ Data scraped successfully!" in response.text
        assert "Successfully scraped 10 matches" in response.text
    
    @patch('subprocess.run')
    def test_scrape_endpoint_failure(self, mock_run):
        """Test the scrape endpoint with failed execution."""
        # Mock failed subprocess
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Error: Network timeout"
        mock_run.return_value = mock_result
        
        response = self.client.get("/scrape")
        
        assert response.status_code == 200
        assert "❌ Scrape failed" in response.text
        assert "Network timeout" in response.text
    
    def test_update_endpoint_legacy(self):
        """Test the legacy update endpoint."""
        response = self.client.get("/update")
        
        assert response.status_code == 200
        assert "ℹ️ This endpoint has been updated" in response.text

class TestWebHelpers:
    """Test helper functions for the web interface."""
    
    @patch('penaltyblog.web.CSV_DIR')
    def test_find_league_csv_dated_structure(self, mock_csv_dir):
        """Test finding CSV files in dated directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mock_csv_dir.__str__ = lambda: str(temp_path)
            mock_csv_dir.__truediv__ = lambda self, other: temp_path / other
            mock_csv_dir.iterdir.return_value = [temp_path / "2024-01-15"]
            
            # Create dated directory and files
            dated_dir = temp_path / "2024-01-15"
            dated_dir.mkdir()
            combined_file = dated_dir / "combined_leagues.csv"
            combined_file.touch()
            
            from penaltyblog.web import find_league_csv
            
            result = find_league_csv()
            
            assert result == combined_file
    
    @patch('penaltyblog.web.load_leagues')
    @patch('penaltyblog.web.CSV_DIR')
    def test_get_available_leagues_from_data(self, mock_csv_dir, mock_load_leagues):
        """Test getting available leagues from data files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mock_csv_dir.__str__ = lambda: str(temp_path)
            mock_csv_dir.__truediv__ = lambda self, other: temp_path / other
            mock_csv_dir.iterdir.return_value = [temp_path / "2024-01-15"]
            
            # Create dated directory and league files
            dated_dir = temp_path / "2024-01-15"
            dated_dir.mkdir()
            
            # Create league files
            (dated_dir / "England_Premier_League.csv").touch()
            (dated_dir / "Spain_La_Liga.csv").touch()
            
            # Mock glob to return our files
            dated_dir.glob = lambda pattern: [
                dated_dir / "England_Premier_League.csv",
                dated_dir / "Spain_La_Liga.csv"
            ]
            
            # Mock leagues
            from penaltyblog.config.leagues import League
            mock_leagues = {
                'ENG_PL': League('ENG_PL', 'Premier League', 'England', 1, '2024-25', 'http://example.com'),
                'ESP_LL': League('ESP_LL', 'La Liga', 'Spain', 1, '2024-25', 'http://example.com')
            }
            mock_load_leagues.return_value = mock_leagues
            
            from penaltyblog.web import get_available_leagues_from_data
            
            result = get_available_leagues_from_data()
            
            # Should find both leagues
            assert 'ENG_PL' in result
            assert 'ESP_LL' in result

@pytest.mark.integration
class TestWebIntegration:
    """Integration tests for the web interface."""
    
    def test_full_web_interface_flow(self):
        """Test a complete flow through the web interface."""
        client = TestClient(app)
        
        # Test that root page loads
        response = client.get("/")
        assert response.status_code == 200
        
        # Test that status endpoint works (even if it returns an error due to no data)
        response = client.get("/status")
        assert response.status_code == 200
        
        # Test that leagues endpoint works
        response = client.get("/leagues")
        assert response.status_code == 200