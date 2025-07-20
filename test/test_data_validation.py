"""
Tests for data validation and monitoring functionality.
"""

import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import penaltyblog as pb
from penaltyblog.utils.data_validation import DataQualityValidator, DataValidationError
from penaltyblog.utils.data_monitoring import DataFreshnessMonitor, hash_dataframe


class TestDataQualityValidator:
    """Test the data quality validator."""
    
    def test_validate_good_fixtures_data(self):
        """Test validation with good fixtures data."""
        df = pd.DataFrame({
            'team_home': ['Arsenal', 'Chelsea', 'Liverpool'],
            'team_away': ['Man City', 'Tottenham', 'Arsenal'],
            'goals_home': [2, 1, 3],
            'goals_away': [1, 2, 0],
            'date': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])
        })
        
        validator = DataQualityValidator(strict_mode=False)
        report = validator.validate_fixtures_data(df, "Premier League", "2022-2023")
        
        assert len(report['errors']) == 0
        assert 'Found 4 unique teams' in ' '.join(report['info'])
    
    def test_validate_empty_dataframe(self):
        """Test validation with empty dataframe."""
        df = pd.DataFrame()
        
        validator = DataQualityValidator(strict_mode=False)
        report = validator.validate_fixtures_data(df, "Premier League", "2022-2023")
        
        assert len(report['errors']) > 0
        assert any('Empty fixtures dataframe' in error for error in report['errors'])
    
    def test_validate_missing_columns(self):
        """Test validation with missing required columns."""
        df = pd.DataFrame({
            'team_home': ['Arsenal', 'Chelsea'],
            'team_away': ['Man City', 'Tottenham']
            # Missing goals columns
        })
        
        validator = DataQualityValidator(strict_mode=False)
        report = validator.validate_fixtures_data(df)
        
        assert len(report['errors']) > 0
        assert any('Missing required columns' in error for error in report['errors'])
    
    def test_validate_negative_goals(self):
        """Test validation with negative goal values."""
        df = pd.DataFrame({
            'team_home': ['Arsenal', 'Chelsea'],
            'team_away': ['Man City', 'Tottenham'],
            'goals_home': [2, -1],  # Negative goals
            'goals_away': [1, 2]
        })
        
        validator = DataQualityValidator(strict_mode=False)
        report = validator.validate_fixtures_data(df)
        
        assert len(report['errors']) > 0
        assert any('negative values' in error for error in report['errors'])
    
    def test_validate_empty_team_names(self):
        """Test validation with empty team names."""
        df = pd.DataFrame({
            'team_home': ['Arsenal', ''],  # Empty team name
            'team_away': ['Man City', 'Tottenham'],
            'goals_home': [2, 1],
            'goals_away': [1, 2]
        })
        
        validator = DataQualityValidator(strict_mode=False)
        report = validator.validate_fixtures_data(df)
        
        assert len(report['errors']) > 0
        assert any('empty team names' in error for error in report['errors'])
    
    def test_validate_self_matches(self):
        """Test validation with teams playing themselves."""
        df = pd.DataFrame({
            'team_home': ['Arsenal', 'Arsenal'],  # Team playing itself
            'team_away': ['Arsenal', 'Tottenham'],
            'goals_home': [2, 1],
            'goals_away': [1, 2]
        })
        
        validator = DataQualityValidator(strict_mode=False)
        report = validator.validate_fixtures_data(df)
        
        assert len(report['errors']) > 0
        assert any('teams play themselves' in error for error in report['errors'])
    
    def test_validate_future_dates(self):
        """Test validation with future dates."""
        future_date = datetime.now() + timedelta(days=365)
        df = pd.DataFrame({
            'team_home': ['Arsenal'],
            'team_away': ['Man City'],
            'goals_home': [2],
            'goals_away': [1],
            'date': [future_date]
        })
        
        validator = DataQualityValidator(strict_mode=False)
        report = validator.validate_fixtures_data(df)
        
        assert len(report['warnings']) > 0
        assert any('future dates' in warning for warning in report['warnings'])
    
    def test_cross_validate_sources(self):
        """Test cross-validation between two data sources."""
        source1 = pd.DataFrame({
            'team_home': ['Arsenal', 'Chelsea'],
            'team_away': ['Man City', 'Tottenham'],
            'goals_home': [2, 1],
            'goals_away': [1, 2],
            'date': pd.to_datetime(['2023-01-01', '2023-01-02'])
        })
        
        source2 = pd.DataFrame({
            'team_home': ['Arsenal', 'Chelsea'],
            'team_away': ['Man City', 'Tottenham'],
            'goals_home': [2, 1],  # Same goals
            'goals_away': [1, 3],  # Different goals for second match
            'date': pd.to_datetime(['2023-01-01', '2023-01-02'])
        })
        
        validator = DataQualityValidator(strict_mode=False)
        report = validator.cross_validate_sources(source1, source2, "Source1", "Source2")
        
        assert 'cross_validation' in report
        assert report['cross_validation']['goal_mismatches'] == 1
        assert report['cross_validation']['mismatch_rate'] == 0.5
    
    def test_strict_mode(self):
        """Test that strict mode raises exceptions for warnings."""
        df = pd.DataFrame({
            'team_home': ['Arsenal'],
            'team_away': ['Man City'],
            'goals_home': [15],  # Unusually high score
            'goals_away': [1]
        })
        
        validator = DataQualityValidator(strict_mode=True)
        
        with pytest.raises(DataValidationError):
            validator.validate_fixtures_data(df)


class TestDataFreshnessMonitor:
    """Test the data freshness monitor."""
    
    def test_record_and_check_freshness(self, tmp_path):
        """Test recording and checking data freshness."""
        monitor = DataFreshnessMonitor(cache_dir=str(tmp_path))
        
        # Record a data fetch
        monitor.record_data_fetch("fbref", "Premier League", "2022-2023", 
                                data_hash="abc123", record_count=380)
        
        # Check freshness immediately (should be fresh)
        freshness = monitor.check_data_freshness("fbref", "Premier League", "2022-2023", 
                                               max_age_hours=24)
        
        assert freshness['is_fresh'] is True
        assert freshness['status'] == 'fresh'
        assert freshness['recommendation'] == 'use_cached'
    
    def test_stale_data_detection(self, tmp_path):
        """Test detection of stale data."""
        monitor = DataFreshnessMonitor(cache_dir=str(tmp_path))
        
        # Manually set old timestamp
        old_timestamp = (datetime.now() - timedelta(hours=25)).isoformat()
        monitor.metadata = {
            "fbref_premier_league_2022-2023": {
                'source': 'fbref',
                'competition': 'Premier League',
                'season': '2022-2023',
                'last_fetched': old_timestamp,
                'data_hash': 'abc123',
                'record_count': 380,
                'fetch_count': 1
            }
        }
        
        # Check freshness (should be stale)
        freshness = monitor.check_data_freshness("fbref", "Premier League", "2022-2023", 
                                               max_age_hours=24)
        
        assert freshness['is_fresh'] is False
        assert freshness['status'] == 'stale'
        assert freshness['recommendation'] == 'fetch_new'
    
    def test_never_fetched_data(self, tmp_path):
        """Test handling of never-fetched data."""
        monitor = DataFreshnessMonitor(cache_dir=str(tmp_path))
        
        freshness = monitor.check_data_freshness("fbref", "Premier League", "2022-2023")
        
        assert freshness['is_fresh'] is False
        assert freshness['status'] == 'never_fetched'
        assert freshness['recommendation'] == 'fetch_data'
    
    def test_data_change_detection(self, tmp_path):
        """Test detection of data changes."""
        monitor = DataFreshnessMonitor(cache_dir=str(tmp_path))
        
        # Record initial data
        monitor.record_data_fetch("fbref", "Premier League", "2022-2023", 
                                data_hash="abc123", record_count=380)
        
        # Check for changes with same data (no change)
        changes = monitor.detect_data_changes("fbref", "Premier League", "2022-2023",
                                           current_data_hash="abc123", 
                                           current_record_count=380)
        
        assert changes['has_changed'] is False
        assert changes['change_type'] == 'no_change'
        
        # Check for changes with different data (content changed)
        changes = monitor.detect_data_changes("fbref", "Premier League", "2022-2023",
                                           current_data_hash="def456", 
                                           current_record_count=380)
        
        assert changes['has_changed'] is True
        assert changes['change_type'] == 'content_changed'
    
    def test_stale_data_report(self, tmp_path):
        """Test generation of stale data report."""
        monitor = DataFreshnessMonitor(cache_dir=str(tmp_path))
        
        # Add fresh and stale data
        monitor.record_data_fetch("fbref", "Premier League", "2022-2023", 
                                data_hash="abc123", record_count=380)
        
        old_timestamp = (datetime.now() - timedelta(hours=25)).isoformat()
        monitor.metadata["old_source_data"] = {
            'source': 'footballdata',
            'competition': 'Premier League',
            'season': '2021-2022',
            'last_fetched': old_timestamp,
            'data_hash': 'old123',
            'record_count': 380,
            'fetch_count': 1
        }
        
        report = monitor.get_stale_data_report(max_age_hours=24)
        
        assert report['fresh_count'] >= 1
        assert report['stale_count'] >= 1
        assert len(report['fresh_sources']) >= 1
        assert len(report['stale_sources']) >= 1


class TestDataFrameHashing:
    """Test DataFrame hashing functionality."""
    
    def test_identical_dataframes_same_hash(self):
        """Test that identical DataFrames produce the same hash."""
        df1 = pd.DataFrame({
            'a': [1, 2, 3],
            'b': ['x', 'y', 'z']
        })
        
        df2 = pd.DataFrame({
            'a': [1, 2, 3],
            'b': ['x', 'y', 'z']
        })
        
        hash1 = hash_dataframe(df1)
        hash2 = hash_dataframe(df2)
        
        assert hash1 == hash2
        assert hash1 != "hash_error"
    
    def test_different_dataframes_different_hash(self):
        """Test that different DataFrames produce different hashes."""
        df1 = pd.DataFrame({
            'a': [1, 2, 3],
            'b': ['x', 'y', 'z']
        })
        
        df2 = pd.DataFrame({
            'a': [1, 2, 4],  # Different value
            'b': ['x', 'y', 'z']
        })
        
        hash1 = hash_dataframe(df1)
        hash2 = hash_dataframe(df2)
        
        assert hash1 != hash2


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_validate_fixtures_convenience(self):
        """Test the validate_fixtures convenience function."""
        df = pd.DataFrame({
            'team_home': ['Arsenal', 'Chelsea'],
            'team_away': ['Man City', 'Tottenham'],
            'goals_home': [2, 1],
            'goals_away': [1, 2]
        })
        
        report = pb.validate_fixtures(df, "Premier League", "2022-2023")
        
        assert 'errors' in report
        assert 'warnings' in report
        assert 'info' in report
    
    def test_cross_validate_sources_convenience(self):
        """Test the cross_validate_sources convenience function."""
        source1 = pd.DataFrame({
            'team_home': ['Arsenal'],
            'team_away': ['Man City'],
            'goals_home': [2],
            'goals_away': [1],
            'date': pd.to_datetime(['2023-01-01'])
        })
        
        source2 = pd.DataFrame({
            'team_home': ['Arsenal'],
            'team_away': ['Man City'],
            'goals_home': [2],
            'goals_away': [1],
            'date': pd.to_datetime(['2023-01-01'])
        })
        
        report = pb.cross_validate_sources(source1, source2, "Source1", "Source2")
        
        assert 'cross_validation' in report
    
    @patch('penaltyblog.utils.data_monitoring.DataFreshnessMonitor')
    def test_check_data_freshness_convenience(self, mock_monitor):
        """Test the check_data_freshness convenience function."""
        mock_instance = MagicMock()
        mock_monitor.return_value = mock_instance
        mock_instance.check_data_freshness.return_value = {'is_fresh': True}
        
        result = pb.check_data_freshness("fbref", "Premier League", "2022-2023")
        
        assert result['is_fresh'] is True
        mock_instance.check_data_freshness.assert_called_once()
    
    @patch('penaltyblog.utils.data_monitoring.DataFreshnessMonitor')
    def test_record_data_fetch_convenience(self, mock_monitor):
        """Test the record_data_fetch convenience function."""
        mock_instance = MagicMock()
        mock_monitor.return_value = mock_instance
        
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        
        pb.record_data_fetch("fbref", "Premier League", "2022-2023", df)
        
        mock_instance.record_data_fetch.assert_called_once()
        args = mock_instance.record_data_fetch.call_args[0]
        assert args[0] == "fbref"
        assert args[1] == "Premier League"
        assert args[2] == "2022-2023"