#!/usr/bin/env python3
"""
Reality Check Script - FIXED VERSION
===================================

Validates that we're producing real, current-week data and predictions.
- Scrapes fresh fixtures for all leagues
- Runs model predictions
- Validates date windows and probability consistency
- NO DEMO DATA GENERATION IN PRODUCTION
- Outputs validation report

CRITICAL FIXES:
- Removed demo data generation completely
- Fails explicitly when no real data available
- Enhanced temporal validation
"""

import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from penaltyblog.utils.dates import in_next_week, START, END
from penaltyblog.pipeline import run_pipeline

def validate_no_future_completed_results(df: pd.DataFrame, league_name: str) -> list:
    """
    Critical validation: ensure no completed results exist for future dates.
    This is the primary indicator of demo/fake data.
    """
    errors = []
    
    if df.empty:
        return errors
    
    # Check for date columns
    date_col = None
    if 'date' in df.columns:
        date_col = 'date'
    elif 'datetime' in df.columns:
        date_col = 'datetime'
    
    if not date_col:
        return errors
    
    # Parse dates
    df['parsed_date'] = pd.to_datetime(df[date_col], errors='coerce')
    current_date = datetime.now().date()
    
    # Find future dates
    future_mask = df['parsed_date'].dt.date > current_date
    
    # Check for completed results (both goals_home and goals_away are present)
    if 'goals_home' in df.columns and 'goals_away' in df.columns:
        completed_mask = df['goals_home'].notna() & df['goals_away'].notna()
        future_completed = future_mask & completed_mask
        
        if future_completed.any():
            count = future_completed.sum()
            errors.append(f"{league_name}: CRITICAL - {count} completed results for future dates (DEMO DATA DETECTED)")
            
            # Log specific examples
            examples = df[future_completed][['parsed_date', 'goals_home', 'goals_away']].head(3)
            for _, row in examples.iterrows():
                errors.append(f"  Example: {row['parsed_date'].date()} - Goals: {row['goals_home']}-{row['goals_away']}")
    
    return errors

def main():
    print("🔍 REALITY CHECK: Starting validation pipeline...")
    
    # 1️⃣ Run fresh scrape & model for ALL leagues
    print("📡 Running fresh scrape and model for all leagues...")
    try:
        run_pipeline(all_leagues=True, output_dir="data/reality_check")
        print("✅ Pipeline completed successfully")
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        sys.exit(1)

    errors, summary = [], []
    data_dir = Path("data/reality_check")
    
    if not data_dir.exists():
        print("❌ Reality-check FAILED: No output directory found")
        sys.exit(1)
    
    csv_files = list(data_dir.glob("*.csv"))
    if not csv_files:
        print("❌ CRITICAL FAILURE: No CSV files found")
        print("❌ This indicates complete scraper failure")
        print("❌ During off-season, scrapers should still return historical data")
        print("❌ Refusing to generate demo data")
        sys.exit(1)
    
    print(f"📊 Analyzing {len(csv_files)} league files...")
    
    for csv in csv_files:
        try:
            df = pd.read_csv(csv)
            league = csv.stem
            
            if df.empty:
                errors.append(f"{league}: EMPTY CSV")
                continue

            # 2️⃣ CRITICAL: Check for demo data indicators
            demo_errors = validate_no_future_completed_results(df, league)
            errors.extend(demo_errors)

            # 3️⃣ Date window check
            bad_dates = []
            if "date" in df.columns:
                bad_dates = df[~df["date"].apply(lambda s: in_next_week(pd.to_datetime(s).date()) if pd.notna(s) else False)]
            elif "datetime" in df.columns:
                bad_dates = df[~df["datetime"].apply(lambda s: in_next_week(pd.to_datetime(s).date()) if pd.notna(s) else False)]
            
            if len(bad_dates) > 0:
                errors.append(f"{league}: {len(bad_dates)} rows outside next 7 days")

            # 4️⃣ Probability sanity check
            bad_prob = []
            if {"prob_home", "prob_draw", "prob_away"}.issubset(df.columns):
                prob_cols = ["prob_home", "prob_draw", "prob_away"]
                # Check rows where all probabilities are present
                prob_rows = df[prob_cols].dropna()
                if not prob_rows.empty:
                    prob_sums = prob_rows.sum(axis=1)
                    bad_prob = prob_rows[(prob_sums.sub(1).abs() > 1e-4)]
                    if not bad_prob.empty:
                        errors.append(f"{league}: {len(bad_prob)} rows prob≠1")

            summary.append({
                "league": league,
                "rows": len(df),
                "bad_dates": len(bad_dates),
                "prob_errors": len(bad_prob) if len(bad_prob) > 0 else 0,
                "demo_data_detected": len(demo_errors) > 0
            })
            
        except Exception as e:
            errors.append(f"{league}: Error processing file - {e}")
            summary.append({
                "league": league,
                "rows": 0,
                "bad_dates": "error",
                "prob_errors": "error",
                "demo_data_detected": True  # Assume worst case
            })

    # 5️⃣ Output results
    print("\n📋 VALIDATION SUMMARY:")
    print(json.dumps(summary, indent=2))
    
    # Check for demo data detection
    demo_detected = any(s.get('demo_data_detected', False) for s in summary)
    
    if demo_detected:
        print("\n🚨 CRITICAL: DEMO DATA DETECTED!")
        print("🚨 Found completed results for future dates")
        print("🚨 This indicates fake/demo data generation is active")
        print("🚨 Production system should NEVER generate fake data")
        
    if errors:
        print("\n❌ Reality-check FAILED:")
        for error in errors:
            print(f"  • {error}")
        
        if demo_detected:
            print("\n💀 SYSTEM INTEGRITY COMPROMISED - DEMO DATA IN PRODUCTION")
            sys.exit(2)  # Special exit code for demo data detection
        else:
            sys.exit(1)
    
    print(f"\n✅ Reality-check PASSED for fixtures {START} → {END}")
    print(f"📈 Validated {len(summary)} leagues with {sum(s['rows'] for s in summary if isinstance(s['rows'], int))} total fixtures")
    print("✅ No demo data detected - using real sources only")

if __name__ == "__main__":
    main()