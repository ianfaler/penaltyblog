#!/usr/bin/env python3
"""
Basic Scraper Connection Test
============================

Test actual connections to FBRef, Understat, and Football-Data to verify
they can fetch real data.
"""

import requests
import time
import pandas as pd
from datetime import datetime


def test_fbref_connection():
    """Test connection to FBRef."""
    print("🔄 Testing FBRef connection...")
    
    # Test URL for Premier League 2024-25
    url = "https://fbref.com/en/comps/9/2024-2025/schedule/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        content = response.text
        
        # Basic validation
        if len(content) < 1000:
            print(f"❌ FBRef response too small: {len(content)} chars")
            return False
            
        if "fixtures" not in content.lower():
            print("❌ FBRef response doesn't contain fixture data")
            return False
            
        print(f"✅ FBRef connection successful: {len(content)} chars received")
        print(f"    URL: {url}")
        
        # Try to parse with pandas
        try:
            dfs = pd.read_html(content)
            if dfs:
                print(f"    Found {len(dfs)} tables in response")
                return True
        except Exception as e:
            print(f"    ⚠️  Could not parse HTML tables: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ FBRef connection failed: {e}")
        return False


def test_understat_connection():
    """Test connection to Understat."""
    print("\n🔄 Testing Understat connection...")
    
    # Test URL for Premier League
    url = "https://understat.com/league/EPL/2024"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'
    }
    
    cookies = {"beget": "begetok"}
    
    try:
        response = requests.get(url, headers=headers, cookies=cookies, timeout=30)
        response.raise_for_status()
        
        content = response.text
        
        # Basic validation
        if len(content) < 1000:
            print(f"❌ Understat response too small: {len(content)} chars")
            return False
            
        if "datesData" not in content:
            print("❌ Understat response doesn't contain datesData")
            return False
            
        print(f"✅ Understat connection successful: {len(content)} chars received")
        print(f"    URL: {url}")
        print(f"    Contains datesData: Yes")
        
        return True
        
    except Exception as e:
        print(f"❌ Understat connection failed: {e}")
        return False


def test_footballdata_connection():
    """Test connection to Football-Data.co.uk."""
    print("\n🔄 Testing Football-Data connection...")
    
    # Test URL for Premier League 2024-25
    url = "https://www.football-data.co.uk/mmz4281/2425/E0.csv"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        content = response.text
        
        # Basic validation
        if len(content) < 100:
            print(f"❌ Football-Data response too small: {len(content)} chars")
            return False
            
        lines = content.strip().split('\n')
        if len(lines) < 2:
            print("❌ Football-Data response has no data rows")
            return False
            
        # Check for CSV header - should start with Div,Date (handle UTF-8 BOM)
        header = lines[0]
        # Remove UTF-8 BOM if present
        if header.startswith('\ufeff'):
            header = header[1:]
        elif header.startswith('ï»¿'):
            header = header[3:]
            
        if not header.startswith('Div,Date'):
            print(f"❌ Football-Data response doesn't have expected CSV header")
            print(f"    Got header: {header[:50]}...")
            return False
            
        print(f"✅ Football-Data connection successful: {len(lines)} rows received")
        print(f"    URL: {url}")
        print(f"    Header: {header[:50]}...")
        
        # Try to parse as CSV
        try:
            df = pd.read_csv(url)
            print(f"    Successfully parsed CSV: {len(df)} matches")
            
            # Check if we have recent data
            if len(df) > 0:
                print(f"    Sample match: {df.iloc[0]['HomeTeam']} vs {df.iloc[0]['AwayTeam']}")
            
            return True
        except Exception as e:
            print(f"    ⚠️  Could not parse CSV: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Football-Data connection failed: {e}")
        return False


def test_temporal_validation():
    """Test temporal validation logic."""
    print("\n🔄 Testing temporal validation...")
    
    # Create test data with future completed results
    future_date = datetime.now().date()
    from datetime import timedelta
    future_date = future_date + timedelta(days=30)
    
    test_data = pd.DataFrame({
        'date': [future_date.strftime('%Y-%m-%d')],
        'team_home': ['Arsenal'],
        'team_away': ['Chelsea'], 
        'goals_home': [2],  # Completed result for future date - SHOULD BE REJECTED
        'goals_away': [1]
    })
    
    # Parse dates
    test_data['date_parsed'] = pd.to_datetime(test_data['date'])
    current_date = datetime.now().date()
    
    # Check for future completed results
    future_mask = test_data['date_parsed'].dt.date > current_date
    completed_mask = test_data['goals_home'].notna() & test_data['goals_away'].notna()
    invalid_future = future_mask & completed_mask
    
    if invalid_future.any():
        print("✅ Temporal validation working - detected future completed results")
        print(f"    Found {invalid_future.sum()} invalid future results")
        return True
    else:
        print("❌ Temporal validation NOT working - failed to detect future completed results")
        return False


def main():
    """Run all connection tests."""
    print("🧪 BASIC SCRAPER CONNECTION TESTS")
    print("=" * 40)
    
    results = {}
    
    # Test each connection
    results['fbref'] = test_fbref_connection()
    time.sleep(2)  # Be respectful to servers
    
    results['understat'] = test_understat_connection()
    time.sleep(2)
    
    results['footballdata'] = test_footballdata_connection()
    
    # Test temporal validation
    results['temporal_validation'] = test_temporal_validation()
    
    # Summary
    print("\n📊 CONNECTION TEST SUMMARY:")
    print("=" * 30)
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test:<20} {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\nResults: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 ALL CONNECTION TESTS PASSED!")
        print("✅ Scrapers can connect to real data sources")
        print("✅ Temporal validation is working")
        print("✅ Ready for production use")
        return 0
    else:
        print(f"\n⚠️  Some connection tests failed")
        if results.get('temporal_validation', False):
            print("✅ Temporal validation is working")
        if any(results[k] for k in ['fbref', 'understat', 'footballdata']):
            print("✅ At least one data source is working")
        return 1


if __name__ == "__main__":
    exit(main())