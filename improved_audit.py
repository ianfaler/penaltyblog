#!/usr/bin/env python3
"""
Improved Penaltyblog Audit Script
=================================

Enhanced audit with better error handling, retry mechanisms,
and comprehensive reporting for GitHub Actions.
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

class AuditConfig:
    """Configuration for the audit process."""
    
    # Request settings
    TIMEOUT = 15
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    
    # Headers to avoid bot detection
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # Success criteria
    MIN_SUCCESS_RATE = 60  # Minimum acceptable success rate
    CRITICAL_LEAGUES = {   # Leagues that must work
        'ENG_PL', 'ESP_LL', 'ITA_SA', 'GER_BL', 'FRA_L1', 'USA_ML'
    }

class LeagueAuditor:
    """Main audit functionality."""
    
    def __init__(self):
        self.config = AuditConfig()
        self.session = requests.Session()
        self.session.headers.update(self.config.HEADERS)
        
    def load_leagues(self):
        """Load leagues from YAML configuration."""
        config_path = Path("penaltyblog/config/leagues.yaml")
        if not config_path.exists():
            raise FileNotFoundError(f"League config not found: {config_path}")
        
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return data.get('leagues', {})
    
    def test_endpoint(self, league_code, league_config):
        """Test a league endpoint with retry logic."""
        url = league_config.get('url_template', '')
        if not url:
            return False, "No URL template configured"
        
        last_error = None
        
        for attempt in range(self.config.MAX_RETRIES):
            try:
                # Add delay between retries
                if attempt > 0:
                    time.sleep(self.config.RETRY_DELAY)
                
                response = self.session.get(
                    url, 
                    timeout=self.config.TIMEOUT,
                    verify=False,  # Ignore SSL issues for now
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    return True, f"OK ({response.status_code}) - Attempt {attempt + 1}"
                elif response.status_code in [301, 302, 307, 308]:
                    # Handle redirects manually for better control
                    redirect_url = response.headers.get('Location', '')
                    return False, f"Redirect ({response.status_code}) to {redirect_url[:50]}..."
                else:
                    last_error = f"HTTP {response.status_code}"
                    
            except requests.exceptions.Timeout:
                last_error = f"Timeout after {self.config.TIMEOUT}s"
            except requests.exceptions.SSLError as e:
                last_error = f"SSL Error: {str(e)[:50]}..."
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection Error: {str(e)[:50]}..."
            except requests.exceptions.RequestException as e:
                last_error = f"Request Error: {str(e)[:50]}..."
            except Exception as e:
                last_error = f"Unexpected Error: {str(e)[:50]}..."
        
        return False, f"{last_error} (after {self.config.MAX_RETRIES} attempts)"
    
    def categorize_leagues(self, leagues):
        """Categorize leagues by tier and importance."""
        categories = {
            'tier1': [],
            'tier2': [],
            'tier3': [],
            'international': [],
            'other': []
        }
        
        for code, config in leagues.items():
            tier = config.get('tier', 3)
            country = config.get('country', '').upper()
            
            if tier == 1:
                categories['tier1'].append(code)
            elif tier == 2:
                categories['tier2'].append(code)
            elif tier == 3:
                categories['tier3'].append(code)
            elif country in ['USA', 'BRA', 'ARG', 'MEX', 'JPN', 'KOR', 'CHN', 'AUS']:
                categories['international'].append(code)
            else:
                categories['other'].append(code)
        
        return categories
    
    def run_audit(self):
        """Execute the complete audit process."""
        print("🔍 Starting Enhanced Penaltyblog Audit...")
        print(f"⚙️  Configuration: {self.config.MAX_RETRIES} retries, {self.config.TIMEOUT}s timeout")
        
        # Load leagues
        try:
            leagues = self.load_leagues()
            total_count = len(leagues)
            print(f"📋 Found {total_count} leagues to audit")
        except Exception as e:
            print(f"❌ Failed to load leagues: {e}")
            return 1
        
        # Categorize leagues
        categories = self.categorize_leagues(leagues)
        
        # Track results
        results = {
            'passed': [],
            'failed': [],
            'critical_failed': [],
            'by_category': {}
        }
        
        # Test each league
        for i, (league_code, league_config) in enumerate(leagues.items(), 1):
            league_name = league_config.get('name', 'Unknown')
            country = league_config.get('country', 'Unknown')
            
            print(f"\n[{i:2d}/{total_count}] Testing {league_code} ({league_name}, {country})...")
            
            success, message = self.test_endpoint(league_code, league_config)
            
            if success:
                results['passed'].append(league_code)
                print(f"   ✅ {message}")
            else:
                results['failed'].append((league_code, message))
                print(f"   ❌ {message}")
                
                # Check if it's a critical league
                if league_code in self.config.CRITICAL_LEAGUES:
                    results['critical_failed'].append(league_code)
                    print(f"   ⚠️  CRITICAL LEAGUE FAILURE!")
            
            # Small delay to be respectful to servers
            time.sleep(0.5)
        
        # Calculate statistics by category
        for category, league_list in categories.items():
            if league_list:
                passed_in_category = [code for code in league_list if code in results['passed']]
                success_rate = (len(passed_in_category) / len(league_list)) * 100
                results['by_category'][category] = {
                    'total': len(league_list),
                    'passed': len(passed_in_category),
                    'success_rate': success_rate
                }
        
        # Generate report
        return self.generate_report(results, total_count)
    
    def generate_report(self, results, total_count):
        """Generate a comprehensive audit report."""
        passed_count = len(results['passed'])
        failed_count = len(results['failed'])
        critical_failures = len(results['critical_failed'])
        
        overall_success_rate = (passed_count / total_count) * 100
        
        print("\n" + "="*80)
        print("📊 ENHANCED AUDIT REPORT")
        print("="*80)
        print(f"🕒 Audit completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"📈 Overall Results:")
        print(f"   Total leagues: {total_count}")
        print(f"   ✅ Passed: {passed_count}")
        print(f"   ❌ Failed: {failed_count}")
        print(f"   📊 Success rate: {overall_success_rate:.1f}%")
        
        # Critical league status
        if critical_failures > 0:
            print(f"\n🚨 CRITICAL FAILURES ({critical_failures}):")
            for code in results['critical_failed']:
                print(f"   💥 {code} - Major league offline!")
        
        # Category breakdown
        if results['by_category']:
            print(f"\n📋 Results by Category:")
            for category, stats in results['by_category'].items():
                print(f"   {category.upper()}: {stats['passed']}/{stats['total']} ({stats['success_rate']:.1f}%)")
        
        # Detailed failures
        if results['failed']:
            print(f"\n❌ DETAILED FAILURES ({failed_count}):")
            for i, (league_code, error) in enumerate(results['failed'][:15], 1):
                print(f"   {i:2d}. {league_code}: {error}")
            
            if failed_count > 15:
                print(f"   ... and {failed_count - 15} more failures")
        
        # Determine audit result
        exit_code = self.determine_exit_code(overall_success_rate, critical_failures)
        
        print(f"\n🎯 AUDIT VERDICT:")
        if exit_code == 0:
            print("✅ PASSED - Acceptable success rate achieved")
        elif exit_code == 1:
            print("⚠️  WARNING - Success rate below target but not critical")
        else:
            print("❌ FAILED - Critical issues detected")
        
        print(f"\n💡 Recommendations:")
        if overall_success_rate < 50:
            print("   🔧 Run the league endpoint repair script")
            print("   📞 Contact data providers for major leagues")
        elif overall_success_rate < 70:
            print("   🔍 Investigate specific league failures")
            print("   📝 Update problematic URLs")
        else:
            print("   ✨ System is performing well!")
            print("   🔄 Monitor for any new failures")
        
        return exit_code
    
    def determine_exit_code(self, success_rate, critical_failures):
        """Determine the appropriate exit code for GitHub Actions."""
        # Critical failures always fail the audit
        if critical_failures > 0:
            return 2
        
        # Check against minimum success rate
        if success_rate >= self.config.MIN_SUCCESS_RATE:
            return 0  # Success
        elif success_rate >= 40:
            return 1  # Warning
        else:
            return 2  # Failure

def main():
    """Main entry point."""
    auditor = LeagueAuditor()
    return auditor.run_audit()

if __name__ == '__main__':
    sys.exit(main())