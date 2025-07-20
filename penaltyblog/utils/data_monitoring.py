"""
Data monitoring and freshness utilities for penaltyblog package.

This module provides tools to monitor data quality, freshness, and detect
changes in external data sources over time.
"""

import json
import logging
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class DataFreshnessMonitor:
    """
    Monitor data freshness and detect stale data sources.
    """
    
    def __init__(self, cache_dir: str = ".penaltyblog_cache"):
        """
        Initialize the data freshness monitor.
        
        Parameters
        ----------
        cache_dir : str
            Directory to store monitoring cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.metadata_file = self.cache_dir / "data_metadata.json"
        self.load_metadata()
    
    def load_metadata(self):
        """Load existing metadata from cache."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    self.metadata = json.load(f)
            else:
                self.metadata = {}
        except Exception as e:
            logger.warning(f"Could not load metadata cache: {e}")
            self.metadata = {}
    
    def save_metadata(self):
        """Save metadata to cache."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Could not save metadata cache: {e}")
    
    def record_data_fetch(self, source: str, competition: str, season: str, 
                         data_hash: str = None, record_count: int = None):
        """
        Record a data fetch operation.
        
        Parameters
        ----------
        source : str
            Data source name (e.g., 'fbref', 'footballdata')
        competition : str
            Competition name
        season : str
            Season identifier
        data_hash : str, optional
            Hash of the data content for change detection
        record_count : int, optional
            Number of records fetched
        """
        key = f"{source}_{competition}_{season}".replace(" ", "_").lower()
        
        self.metadata[key] = {
            'source': source,
            'competition': competition,
            'season': season,
            'last_fetched': datetime.now().isoformat(),
            'data_hash': data_hash,
            'record_count': record_count,
            'fetch_count': self.metadata.get(key, {}).get('fetch_count', 0) + 1
        }
        
        self.save_metadata()
        logger.info(f"Recorded data fetch: {key}")
    
    def check_data_freshness(self, source: str, competition: str, season: str,
                           max_age_hours: int = 24) -> Dict[str, Any]:
        """
        Check if data is fresh or needs updating.
        
        Parameters
        ----------
        source : str
            Data source name
        competition : str
            Competition name
        season : str
            Season identifier
        max_age_hours : int
            Maximum age in hours before data is considered stale
            
        Returns
        -------
        Dict[str, Any]
            Freshness status and metadata
        """
        key = f"{source}_{competition}_{season}".replace(" ", "_").lower()
        
        if key not in self.metadata:
            return {
                'is_fresh': False,
                'status': 'never_fetched',
                'last_fetched': None,
                'age_hours': None,
                'recommendation': 'fetch_data'
            }
        
        meta = self.metadata[key]
        last_fetched = datetime.fromisoformat(meta['last_fetched'])
        age = datetime.now() - last_fetched
        age_hours = age.total_seconds() / 3600
        
        is_fresh = age_hours <= max_age_hours
        
        status = 'fresh' if is_fresh else 'stale'
        recommendation = 'use_cached' if is_fresh else 'fetch_new'
        
        return {
            'is_fresh': is_fresh,
            'status': status,
            'last_fetched': last_fetched,
            'age_hours': age_hours,
            'recommendation': recommendation,
            'record_count': meta.get('record_count'),
            'fetch_count': meta.get('fetch_count')
        }
    
    def detect_data_changes(self, source: str, competition: str, season: str,
                          current_data_hash: str, current_record_count: int = None) -> Dict[str, Any]:
        """
        Detect if data has changed since last fetch.
        
        Parameters
        ----------
        source : str
            Data source name
        competition : str
            Competition name
        season : str
            Season identifier
        current_data_hash : str
            Hash of current data
        current_record_count : int, optional
            Current number of records
            
        Returns
        -------
        Dict[str, Any]
            Change detection results
        """
        key = f"{source}_{competition}_{season}".replace(" ", "_").lower()
        
        if key not in self.metadata:
            return {
                'has_changed': True,
                'change_type': 'new_data',
                'previous_hash': None,
                'current_hash': current_data_hash,
                'record_count_change': None
            }
        
        meta = self.metadata[key]
        previous_hash = meta.get('data_hash')
        previous_count = meta.get('record_count')
        
        hash_changed = previous_hash != current_data_hash
        count_changed = (previous_count is not None and 
                        current_record_count is not None and
                        previous_count != current_record_count)
        
        has_changed = hash_changed or count_changed
        
        if has_changed:
            if hash_changed and count_changed:
                change_type = 'content_and_count_changed'
            elif hash_changed:
                change_type = 'content_changed'
            elif count_changed:
                change_type = 'count_changed'
            else:
                change_type = 'unknown_change'
        else:
            change_type = 'no_change'
        
        record_count_change = None
        if previous_count is not None and current_record_count is not None:
            record_count_change = current_record_count - previous_count
        
        return {
            'has_changed': has_changed,
            'change_type': change_type,
            'previous_hash': previous_hash,
            'current_hash': current_data_hash,
            'previous_count': previous_count,
            'current_count': current_record_count,
            'record_count_change': record_count_change
        }
    
    def get_stale_data_report(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """
        Generate a report of all stale data sources.
        
        Parameters
        ----------
        max_age_hours : int
            Maximum age in hours before data is considered stale
            
        Returns
        -------
        Dict[str, Any]
            Report of stale data sources
        """
        stale_sources = []
        fresh_sources = []
        
        for key, meta in self.metadata.items():
            try:
                last_fetched = datetime.fromisoformat(meta['last_fetched'])
                age = datetime.now() - last_fetched
                age_hours = age.total_seconds() / 3600
                
                source_info = {
                    'key': key,
                    'source': meta['source'],
                    'competition': meta['competition'],
                    'season': meta['season'],
                    'age_hours': age_hours,
                    'last_fetched': last_fetched,
                    'record_count': meta.get('record_count'),
                    'fetch_count': meta.get('fetch_count')
                }
                
                if age_hours > max_age_hours:
                    stale_sources.append(source_info)
                else:
                    fresh_sources.append(source_info)
                    
            except Exception as e:
                logger.warning(f"Error processing metadata for {key}: {e}")
        
        return {
            'stale_sources': stale_sources,
            'fresh_sources': fresh_sources,
            'stale_count': len(stale_sources),
            'fresh_count': len(fresh_sources),
            'total_sources': len(stale_sources) + len(fresh_sources)
        }
    
    def cleanup_old_metadata(self, days_to_keep: int = 90):
        """
        Clean up old metadata entries.
        
        Parameters
        ----------
        days_to_keep : int
            Number of days to keep metadata entries
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        keys_to_remove = []
        
        for key, meta in self.metadata.items():
            try:
                last_fetched = datetime.fromisoformat(meta['last_fetched'])
                if last_fetched < cutoff_date:
                    keys_to_remove.append(key)
            except Exception:
                keys_to_remove.append(key)  # Remove invalid entries
        
        for key in keys_to_remove:
            del self.metadata[key]
        
        if keys_to_remove:
            self.save_metadata()
            logger.info(f"Cleaned up {len(keys_to_remove)} old metadata entries")


class DataQualityTrend:
    """
    Track data quality trends over time.
    """
    
    def __init__(self, cache_dir: str = ".penaltyblog_cache"):
        """
        Initialize the data quality trend tracker.
        
        Parameters
        ----------
        cache_dir : str
            Directory to store trend data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.trends_file = self.cache_dir / "quality_trends.json"
        self.load_trends()
    
    def load_trends(self):
        """Load existing trend data from cache."""
        try:
            if self.trends_file.exists():
                with open(self.trends_file, 'r') as f:
                    self.trends = json.load(f)
            else:
                self.trends = {}
        except Exception as e:
            logger.warning(f"Could not load trends cache: {e}")
            self.trends = {}
    
    def save_trends(self):
        """Save trend data to cache."""
        try:
            with open(self.trends_file, 'w') as f:
                json.dump(self.trends, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Could not save trends cache: {e}")
    
    def record_quality_metrics(self, source: str, competition: str, season: str,
                             metrics: Dict[str, Any]):
        """
        Record quality metrics for trend analysis.
        
        Parameters
        ----------
        source : str
            Data source name
        competition : str
            Competition name
        season : str
            Season identifier
        metrics : Dict[str, Any]
            Quality metrics (errors, warnings, completeness, etc.)
        """
        key = f"{source}_{competition}_{season}".replace(" ", "_").lower()
        
        if key not in self.trends:
            self.trends[key] = {
                'source': source,
                'competition': competition,
                'season': season,
                'history': []
            }
        
        metrics_with_timestamp = {
            'timestamp': datetime.now().isoformat(),
            **metrics
        }
        
        self.trends[key]['history'].append(metrics_with_timestamp)
        
        # Keep only last 100 entries to prevent unbounded growth
        if len(self.trends[key]['history']) > 100:
            self.trends[key]['history'] = self.trends[key]['history'][-100:]
        
        self.save_trends()
    
    def get_quality_trend(self, source: str, competition: str, season: str,
                         days_back: int = 30) -> Dict[str, Any]:
        """
        Get quality trend for a specific data source.
        
        Parameters
        ----------
        source : str
            Data source name
        competition : str
            Competition name
        season : str
            Season identifier
        days_back : int
            Number of days to look back
            
        Returns
        -------
        Dict[str, Any]
            Quality trend analysis
        """
        key = f"{source}_{competition}_{season}".replace(" ", "_").lower()
        
        if key not in self.trends:
            return {'status': 'no_data', 'trend': None}
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        recent_history = []
        
        for entry in self.trends[key]['history']:
            try:
                entry_date = datetime.fromisoformat(entry['timestamp'])
                if entry_date >= cutoff_date:
                    recent_history.append(entry)
            except Exception:
                continue
        
        if not recent_history:
            return {'status': 'no_recent_data', 'trend': None}
        
        # Analyze trends
        error_counts = [entry.get('error_count', 0) for entry in recent_history]
        warning_counts = [entry.get('warning_count', 0) for entry in recent_history]
        completeness_scores = [entry.get('completeness', 1.0) for entry in recent_history]
        
        trend_analysis = {
            'status': 'analyzed',
            'period_days': days_back,
            'data_points': len(recent_history),
            'error_trend': self._calculate_trend(error_counts),
            'warning_trend': self._calculate_trend(warning_counts),
            'completeness_trend': self._calculate_trend(completeness_scores),
            'recent_metrics': recent_history[-1] if recent_history else None,
            'average_errors': sum(error_counts) / len(error_counts) if error_counts else 0,
            'average_warnings': sum(warning_counts) / len(warning_counts) if warning_counts else 0,
            'average_completeness': sum(completeness_scores) / len(completeness_scores) if completeness_scores else 1.0
        }
        
        return {'status': 'analyzed', 'trend': trend_analysis}
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a list of values."""
        if len(values) < 2:
            return 'insufficient_data'
        
        # Simple linear trend calculation
        n = len(values)
        x = list(range(n))
        y = values
        
        # Calculate slope
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 'stable'
        
        slope = numerator / denominator
        
        # Classify trend
        if abs(slope) < 0.1:
            return 'stable'
        elif slope > 0:
            return 'increasing'
        else:
            return 'decreasing'


class SourceHealthMonitor:
    """
    Monitor the health of external data sources.
    """
    
    def __init__(self):
        """Initialize the source health monitor."""
        self.health_status = {}
    
    def check_source_health(self, source_name: str, url: str, 
                          timeout: int = 30) -> Dict[str, Any]:
        """
        Check the health of an external data source.
        
        Parameters
        ----------
        source_name : str
            Name of the data source
        url : str
            URL to check
        timeout : int
            Request timeout in seconds
            
        Returns
        -------
        Dict[str, Any]
            Health check results
        """
        import requests
        
        health_check = {
            'source': source_name,
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'status': 'unknown',
            'response_time': None,
            'status_code': None,
            'error': None
        }
        
        try:
            start_time = datetime.now()
            response = requests.head(url, timeout=timeout)
            end_time = datetime.now()
            
            health_check['response_time'] = (end_time - start_time).total_seconds()
            health_check['status_code'] = response.status_code
            
            if response.status_code == 200:
                health_check['status'] = 'healthy'
            elif response.status_code in [429, 503, 504]:
                health_check['status'] = 'rate_limited'
            elif response.status_code >= 500:
                health_check['status'] = 'server_error'
            elif response.status_code >= 400:
                health_check['status'] = 'client_error'
            else:
                health_check['status'] = 'unknown_status'
                
        except requests.exceptions.Timeout:
            health_check['status'] = 'timeout'
            health_check['error'] = 'Request timed out'
        except requests.exceptions.ConnectionError:
            health_check['status'] = 'connection_error'
            health_check['error'] = 'Connection failed'
        except Exception as e:
            health_check['status'] = 'error'
            health_check['error'] = str(e)
        
        self.health_status[source_name] = health_check
        return health_check
    
    def get_all_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status for all monitored sources."""
        return self.health_status.copy()
    
    def get_unhealthy_sources(self) -> List[Dict[str, Any]]:
        """Get list of unhealthy sources."""
        unhealthy = []
        healthy_statuses = ['healthy']
        
        for source, status in self.health_status.items():
            if status.get('status') not in healthy_statuses:
                unhealthy.append(status)
        
        return unhealthy


def hash_dataframe(df: pd.DataFrame) -> str:
    """
    Generate a hash of a DataFrame for change detection.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to hash
        
    Returns
    -------
    str
        Hash string
    """
    import hashlib
    
    try:
        # Create a string representation of the dataframe
        df_str = df.to_string(index=False)
        return hashlib.md5(df_str.encode()).hexdigest()
    except Exception as e:
        logger.warning(f"Error hashing dataframe: {e}")
        return "hash_error"


# Convenience functions
def check_data_freshness(source: str, competition: str, season: str,
                        max_age_hours: int = 24, cache_dir: str = ".penaltyblog_cache") -> Dict[str, Any]:
    """
    Convenience function to check data freshness.
    
    Parameters
    ----------
    source : str
        Data source name
    competition : str
        Competition name
    season : str
        Season identifier
    max_age_hours : int
        Maximum age in hours before data is considered stale
    cache_dir : str
        Cache directory
        
    Returns
    -------
    Dict[str, Any]
        Freshness status
    """
    monitor = DataFreshnessMonitor(cache_dir=cache_dir)
    return monitor.check_data_freshness(source, competition, season, max_age_hours)


def record_data_fetch(source: str, competition: str, season: str, df: pd.DataFrame = None,
                     cache_dir: str = ".penaltyblog_cache"):
    """
    Convenience function to record a data fetch.
    
    Parameters
    ----------
    source : str
        Data source name
    competition : str
        Competition name
    season : str
        Season identifier
    df : pd.DataFrame, optional
        DataFrame that was fetched
    cache_dir : str
        Cache directory
    """
    monitor = DataFreshnessMonitor(cache_dir=cache_dir)
    
    data_hash = None
    record_count = None
    
    if df is not None:
        data_hash = hash_dataframe(df)
        record_count = len(df)
    
    monitor.record_data_fetch(source, competition, season, data_hash, record_count)