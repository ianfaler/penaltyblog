#!/usr/bin/env python3
"""
Simplified Audit Script for Penaltyblog
========================================

This script tests the core audit functionality without complex imports.
"""

import sys
import yaml
from pathlib import Path
import requests
from datetime import datetime

def load_leagues_simple():
    """Load leagues from YAML file."""
    config_path = Path("penaltyblog/config/leagues.yaml")
    if not config_path.exists():
        raise FileNotFoundError(f"League config not found: {config_path}")
    
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
    
    return data.get('leagues', {})

def test_league_endpoint(league_code, league_config):
    """Test if a league endpoint is accessible."""
    try:
        url = league_config.get('url_template', '')
        if not url:
            return False, "No URL template"
        
        # Make a simple request to test connectivity
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if response.status_code == 200:
            return True, f"OK ({response.status_code})"
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    """Run simplified audit."""
    print("🔍 Starting simplified audit...")
    
    # Load leagues
    try:
        leagues = load_leagues_simple()
        print(f"📋 Found {len(leagues)} leagues to test")
    except Exception as e:
        print(f"❌ Failed to load leagues: {e}")
        return 1
    
    failed_leagues = []
    passed_leagues = []
    
    # Test each league
    for i, (league_code, league_config) in enumerate(leagues.items(), 1):
        print(f"[{i}/{len(leagues)}] Testing {league_code} ({league_config.get('name', 'Unknown')})...")
        
        success, message = test_league_endpoint(league_code, league_config)
        
        if success:
            passed_leagues.append(league_code)
            print(f"   ✅ {message}")
        else:
            failed_leagues.append((league_code, message))
            print(f"   ❌ {message}")
    
    # Print summary
    print("\n" + "="*70)
    print("📊 SIMPLIFIED AUDIT SUMMARY")
    print("="*70)
    print(f"📈 Total leagues: {len(leagues)}")
    print(f"✅ Passed: {len(passed_leagues)}")
    print(f"❌ Failed: {len(failed_leagues)}")
    
    if failed_leagues:
        print(f"\n❌ FAILURES ({len(failed_leagues)}):")
        for league_code, error in failed_leagues[:10]:  # Show first 10
            print(f"   {league_code}: {error}")
        if len(failed_leagues) > 10:
            print(f"   ... and {len(failed_leagues) - 10} more")
    
    if failed_leagues:
        print("💥 AUDIT FAILED - Some leagues are not accessible")
        return 1
    else:
        print("🎉 AUDIT PASSED - All leagues are accessible")
        return 0

if __name__ == '__main__':
    sys.exit(main())