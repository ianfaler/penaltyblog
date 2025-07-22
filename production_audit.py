#!/usr/bin/env python3
"""
Production Penaltyblog Audit Script
===================================

Production-ready audit that only tests enabled leagues
and provides GitHub Actions compatible output.
"""

import sys
import yaml
import requests
import time
from pathlib import Path
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning
import warnings

# Suppress SSL warnings for problematic endpoints
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

class ProductionAuditConfig:
    """Production configuration for the audit process."""
    
    # Request settings optimized for GitHub Actions
    TIMEOUT = 10
    MAX_RETRIES = 2
    RETRY_DELAY = 1
    
    # Headers to avoid bot detection
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

def load_leagues():
    """Load only enabled leagues from configuration."""
    config_path = Path('penaltyblog/config/leagues.yaml')
    
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        all_leagues = yaml.safe_load(f)
    
    # Filter to only enabled leagues
    enabled_leagues = {}
    for league_code, config in all_leagues.items():
        if isinstance(config, dict):
            if config.get('enabled', True):  # Default to enabled if not specified
                enabled_leagues[league_code] = config
        else:
            # If config is not a dict, assume it's enabled (legacy format)
            enabled_leagues[league_code] = config
    
    print(f"📋 Found {len(all_leagues)} total leagues, {len(enabled_leagues)} enabled")
    return enabled_leagues

def test_league_endpoint(league_code, config):
    """Test a single league endpoint with retries."""
    url = config.get('url') if isinstance(config, dict) else config
    
    if not url:
        return False, "No URL configured"
    
    for attempt in range(1, ProductionAuditConfig.MAX_RETRIES + 1):
        try:
            response = requests.get(
                url, 
                headers=ProductionAuditConfig.HEADERS,
                timeout=ProductionAuditConfig.TIMEOUT,
                verify=False,  # Ignore SSL issues for stability
                allow_redirects=True
            )
            
            if response.status_code == 200:
                return True, f"OK ({response.status_code})"
            else:
                error_msg = f"HTTP {response.status_code}"
                if attempt < ProductionAuditConfig.MAX_RETRIES:
                    time.sleep(ProductionAuditConfig.RETRY_DELAY)
                    continue
                return False, error_msg
                
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if attempt < ProductionAuditConfig.MAX_RETRIES:
                time.sleep(ProductionAuditConfig.RETRY_DELAY)
                continue
            return False, error_msg
    
    return False, "Max retries exceeded"

def run_production_audit():
    """Run the production audit process."""
    print("🔍 Starting Production Penaltyblog Audit...")
    print(f"⚙️  Configuration: {ProductionAuditConfig.MAX_RETRIES} retries, {ProductionAuditConfig.TIMEOUT}s timeout")
    
    # Load enabled leagues
    leagues = load_leagues()
    
    if not leagues:
        print("❌ No enabled leagues found!")
        sys.exit(1)
    
    # Test each enabled league
    results = {}
    passed = 0
    failed = 0
    critical_failures = []
    
    for i, (league_code, config) in enumerate(leagues.items(), 1):
        league_name = config.get('name', 'Unknown') if isinstance(config, dict) else 'Unknown'
        print(f"[{i:2d}/{len(leagues)}] Testing {league_code} ({league_name})...")
        
        success, message = test_league_endpoint(league_code, config)
        results[league_code] = {'success': success, 'message': message, 'name': league_name}
        
        if success:
            print(f"   ✅ {message}")
            passed += 1
        else:
            print(f"   ❌ {message}")
            failed += 1
            
            # Check if this is a critical league
            tier = config.get('tier', 'TIER1') if isinstance(config, dict) else 'TIER1'
            if tier == 'TIER1':
                critical_failures.append(league_code)
    
    # Generate report
    print("\n" + "=" * 70)
    print("📊 PRODUCTION AUDIT REPORT")
    print("=" * 70)
    print(f"🕒 Audit completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"📈 Overall Results:")
    print(f"   Total enabled leagues: {len(leagues)}")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📊 Success rate: {passed/len(leagues)*100:.1f}%")
    
    # Report critical failures
    if critical_failures:
        print(f"\n🚨 CRITICAL FAILURES ({len(critical_failures)}):")
        for league_code in critical_failures:
            print(f"   💥 {league_code} - {results[league_code]['message']}")
    
    # List failed leagues
    if failed > 0:
        print(f"\n❌ FAILED LEAGUES ({failed}):")
        failed_leagues = [(code, result) for code, result in results.items() if not result['success']]
        for i, (league_code, result) in enumerate(failed_leagues[:10], 1):  # Show first 10
            print(f"   {i:2d}. {league_code}: {result['message']}")
        if len(failed_leagues) > 10:
            print(f"   ... and {len(failed_leagues) - 10} more failures")
    
    # Determine overall result
    success_rate = passed / len(leagues) * 100
    
    if success_rate == 100:
        print(f"\n🎯 AUDIT VERDICT:")
        print("✅ PASSED - All enabled leagues are working")
        return 0
    elif success_rate >= 95:
        print(f"\n🎯 AUDIT VERDICT:")
        print("⚠️ WARNING - High success rate but some failures")
        return 0 if not critical_failures else 1
    else:
        print(f"\n🎯 AUDIT VERDICT:")
        print("❌ FAILED - Too many league failures")
        return 1

def main():
    """Main execution function."""
    try:
        return run_production_audit()
    except KeyboardInterrupt:
        print("\n❌ Audit interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Audit failed with error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())