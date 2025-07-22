#!/usr/bin/env python3
"""
League Endpoint Repair Script
=============================

This script fixes the broken league endpoints identified in the audit
by updating URLs, improving configuration, and adding fallback mechanisms.
"""

import yaml
import requests
from pathlib import Path
import time
from datetime import datetime

# Working leagues from the audit
WORKING_LEAGUES = {
    'ENG_PL', 'ESP_LL', 'ITA_SA', 'TUR_SL', 'RUS_PL', 'ENG_CH', 'ESP_L2', 
    'FRA_L2', 'USA_ML', 'AUS_AL', 'ENG_L1', 'GER_3L', 'CZE_FL', 'HUN_NB', 
    'CRO_1H', 'AUT_BL'
}

# Updated URLs for broken leagues
UPDATED_URLS = {
    # Major European Leagues - Using official APIs and reliable sources
    'GER_BL': {
        'url_template': 'https://api.openligadb.de/getmatchdata/bl1/2024',
        'source': 'OpenLigaDB API'
    },
    'FRA_L1': {
        'url_template': 'https://www.ligue1.fr/ligue1/calendrier-resultats',
        'source': 'Official Ligue 1'
    },
    'NED_ED': {
        'url_template': 'https://www.eredivisie.nl/wedstrijden',
        'source': 'Official Eredivisie'
    },
    'POR_PL': {
        'url_template': 'https://www.ligaportugal.pt/en/liga/fixture/',
        'source': 'Liga Portugal'
    },
    'BEL_PD': {
        'url_template': 'https://www.sporza.be/nl/matches/voetbal/jupiler-pro-league/',
        'source': 'Sporza'
    },
    'GRE_SL': {
        'url_template': 'https://www.superleague.gr/el/championship/program_results/',
        'source': 'Super League Greece'
    },
    'UKR_PL': {
        'url_template': 'https://upl.ua/en/championship/calendar/',
        'source': 'Ukrainian Premier League'
    },
    'SWE_AS': {
        'url_template': 'https://www.svenskfotboll.se/allsvenskan/tabell-resultat/',
        'source': 'Swedish Football'
    },
    'NOR_EL': {
        'url_template': 'https://www.fotball.no/fotballdata/turnering/hoved/',
        'source': 'Norwegian Football'
    },
    'DEN_SL': {
        'url_template': 'https://www.superliga.dk/kampe/',
        'source': 'Danish Superliga'
    },
    
    # Second tier leagues
    'GER_B2': {
        'url_template': 'https://api.openligadb.de/getmatchdata/bl2/2024',
        'source': 'OpenLigaDB API'
    },
    'ITA_SB': {
        'url_template': 'https://www.legaserieb.it/calendario-e-risultati',
        'source': 'Serie B Official'
    },
    
    # International leagues - Using ESPN as reliable fallback
    'BRA_SP': {
        'url_template': 'https://www.espn.com/soccer/league/_/name/bra.1',
        'source': 'ESPN Brazil'
    },
    'ARG_PL': {
        'url_template': 'https://www.espn.com/soccer/league/_/name/arg.1',
        'source': 'ESPN Argentina'
    },
    'MEX_LM': {
        'url_template': 'https://www.ligamx.net/cancha/estadisticas',
        'source': 'Liga MX Official'
    },
    'COL_PL': {
        'url_template': 'https://www.espn.com/soccer/league/_/name/col.1',
        'source': 'ESPN Colombia'
    },
    'JPN_J1': {
        'url_template': 'https://www.jleague.jp/en/match/',
        'source': 'J-League Official'
    },
    'KOR_KL': {
        'url_template': 'https://www.kleague.com/schedule',
        'source': 'K League Official'
    },
    'CHN_CS': {
        'url_template': 'https://www.espn.com/soccer/league/_/name/chn.1',
        'source': 'ESPN China'
    },
    
    # African/Middle Eastern leagues
    'EGY_PL': {
        'url_template': 'https://www.espn.com/soccer/league/_/name/egy.1',
        'source': 'ESPN Egypt'
    },
    'MAR_BL': {
        'url_template': 'https://www.espn.com/soccer/league/_/name/mar.1',
        'source': 'ESPN Morocco'
    },
    'SAU_PL': {
        'url_template': 'https://www.slstat.com/spl2024-2025en/',
        'source': 'Saudi Pro League'
    },
    
    # Lower tier European leagues
    'NED_KD': {
        'url_template': 'https://www.keuken-kampioen-divisie.nl/programma-uitslagen',
        'source': 'KKD Official',
        'notes': 'DNS issues - may need alternative'
    },
    'POR_L2': {
        'url_template': 'https://www.ligaportugal.pt/en/liga2/fixture/',
        'source': 'Liga Portugal 2'
    },
    'BEL_D2': {
        'url_template': 'https://www.sporza.be/nl/matches/voetbal/challenger-pro-league/',
        'source': 'Sporza'
    },
    'ESP_RF': {
        'url_template': 'https://www.rfef.es/en/competitions/primera-rfef',
        'source': 'RFEF Official'
    },
    'SVK_FL': {
        'url_template': 'https://www.profutbal.sk/zapasy',
        'source': 'Slovak Football',
        'notes': 'Connection timeout issues'
    },
    'ROM_L1': {
        'url_template': 'https://www.frf.ro/liga-1/',
        'source': 'Romanian Football'
    },
    'BUL_FL': {
        'url_template': 'https://www.bfunion.bg/competitions/a-pfg',
        'source': 'Bulgarian Football'
    },
    'SRB_SL': {
        'url_template': 'https://www.fss.rs/sr-cir/competitions/super-league',
        'source': 'Serbian Football'
    },
    'SUI_SL': {
        'url_template': 'https://www.sfl.ch/de/super-league/spiele-resultate/',
        'source': 'Swiss Football'
    },
    'CYP_FL': {
        'url_template': 'https://www.cfa.com.cy/competitions/',
        'source': 'Cyprus Football'
    },
    'ISL_PL': {
        'url_template': 'https://www.ksi.is/mot/neid-madur/',
        'source': 'Iceland Football'
    },
    'FIN_VL': {
        'url_template': 'https://www.veikkausliiga.com/ottelut',
        'source': 'Veikkausliiga',
        'notes': 'SSL certificate issues'
    }
}

def load_leagues_config():
    """Load the current leagues configuration."""
    config_path = Path("penaltyblog/config/leagues.yaml")
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def test_url(url, timeout=10):
    """Test if a URL is accessible."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=timeout, headers=headers, verify=False)
        return response.status_code == 200, response.status_code
    except Exception as e:
        return False, str(e)

def update_league_config(config, league_code, updates):
    """Update a league's configuration."""
    if league_code in config['leagues']:
        config['leagues'][league_code].update(updates)
        return True
    return False

def create_backup():
    """Create a backup of the original configuration."""
    config_path = Path("penaltyblog/config/leagues.yaml")
    backup_path = Path(f"penaltyblog/config/leagues.yaml.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    with open(config_path, 'r') as src, open(backup_path, 'w') as dst:
        dst.write(src.read())
    
    print(f"✅ Created backup: {backup_path}")
    return backup_path

def save_config(config):
    """Save the updated configuration."""
    config_path = Path("penaltyblog/config/leagues.yaml")
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, indent=2)

def main():
    """Main repair function."""
    print("🔧 Starting League Endpoint Repair...")
    
    # Create backup
    backup_path = create_backup()
    
    # Load configuration
    config = load_leagues_config()
    total_leagues = len(config['leagues'])
    print(f"📋 Found {total_leagues} leagues in configuration")
    
    # Track changes
    updated_count = 0
    working_count = 0
    still_broken = []
    
    # Process each league
    for league_code, league_config in config['leagues'].items():
        print(f"\n🔍 Processing {league_code} ({league_config.get('name', 'Unknown')})...")
        
        # Skip already working leagues
        if league_code in WORKING_LEAGUES:
            print(f"   ✅ Already working - keeping current URL")
            working_count += 1
            continue
        
        # Check if we have an updated URL
        if league_code in UPDATED_URLS:
            updates = UPDATED_URLS[league_code]
            new_url = updates['url_template']
            
            # Test the new URL
            print(f"   🧪 Testing new URL: {new_url}")
            success, result = test_url(new_url)
            
            if success:
                # Update the configuration
                update_data = {
                    'url_template': new_url,
                    'source': updates['source'],
                    'last_updated': datetime.now().strftime('%Y-%m-%d'),
                    'status': 'active'
                }
                
                if 'notes' in updates:
                    update_data['notes'] = updates['notes']
                
                update_league_config(config, league_code, update_data)
                updated_count += 1
                print(f"   ✅ Updated successfully (Status: {result})")
            else:
                print(f"   ❌ New URL still failing: {result}")
                still_broken.append((league_code, result))
                
                # Mark as problematic but keep the update for future fixing
                update_data = {
                    'url_template': new_url,
                    'source': updates['source'],
                    'last_updated': datetime.now().strftime('%Y-%m-%d'),
                    'status': 'problematic',
                    'last_error': str(result)
                }
                update_league_config(config, league_code, update_data)
        else:
            print(f"   ⚠️  No updated URL available")
            still_broken.append((league_code, "No updated URL"))
            
            # Mark as needing attention
            update_data = {
                'status': 'needs_attention',
                'last_updated': datetime.now().strftime('%Y-%m-%d'),
                'notes': 'Requires manual URL update'
            }
            update_league_config(config, league_code, update_data)
        
        # Small delay to be respectful to servers
        time.sleep(0.5)
    
    # Save updated configuration
    save_config(config)
    
    # Print summary
    print("\n" + "="*70)
    print("🎯 LEAGUE REPAIR SUMMARY")
    print("="*70)
    print(f"📊 Total leagues: {total_leagues}")
    print(f"✅ Already working: {working_count}")
    print(f"🔧 Successfully updated: {updated_count}")
    print(f"❌ Still broken: {len(still_broken)}")
    
    if still_broken:
        print(f"\n❌ REMAINING ISSUES ({len(still_broken)}):")
        for league_code, error in still_broken[:10]:
            print(f"   {league_code}: {error}")
        if len(still_broken) > 10:
            print(f"   ... and {len(still_broken) - 10} more")
    
    # Calculate success rate
    success_rate = ((working_count + updated_count) / total_leagues) * 100
    print(f"\n📈 Success rate: {success_rate:.1f}%")
    
    if success_rate >= 70:
        print("🎉 Significant improvement achieved!")
    elif success_rate >= 50:
        print("👍 Good progress made!")
    else:
        print("🔄 More work needed...")
    
    print(f"\n💾 Configuration updated, backup saved as: {backup_path.name}")
    
    return 0 if success_rate >= 50 else 1

if __name__ == '__main__':
    exit(main())