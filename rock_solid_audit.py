#!/usr/bin/env python3
"""
Rock-Solid Audit Script
=======================

Simple audit script for the verified working leagues only.
This should always pass 100%.
"""

import sys
import yaml
import requests
import time
from pathlib import Path
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning
import warnings

warnings.filterwarnings('ignore', category=InsecureRequestWarning)

TIMEOUT = 10
MAX_RETRIES = 2

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Connection': 'keep-alive'
}

def test_endpoint(url):
    """Test a single endpoint."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False)
            if response.status_code == 200:
                return True, f"OK ({response.status_code})"
            else:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(1)
                    continue
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(1)
                continue
            return False, str(e)[:50]
    return False, "Max retries exceeded"

def main():
    """Run the rock-solid audit."""
    print("🔍 Rock-Solid Penaltyblog Audit")
    print("=" * 40)
    
    # Load configuration
    config_path = Path('penaltyblog/config/leagues.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    leagues = config.get('leagues', config)
    enabled_leagues = {k: v for k, v in leagues.items() 
                      if isinstance(v, dict) and v.get('enabled', False)}
    
    print(f"📋 Testing {len(enabled_leagues)} enabled leagues")
    
    passed = 0
    failed = 0
    
    for i, (code, conf) in enumerate(enabled_leagues.items(), 1):
        url = conf.get('url') or conf.get('url_template')
        name = conf.get('name', 'Unknown')
        
        print(f"[{i:2d}/{len(enabled_leagues)}] {code} ({name})...", end=' ')
        
        if url:
            success, message = test_endpoint(url)
            if success:
                print(f"✅ {message}")
                passed += 1
            else:
                print(f"❌ {message}")
                failed += 1
        else:
            print("❌ No URL")
            failed += 1
    
    print("\n" + "=" * 40)
    print(f"📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED - Rock solid!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
