#!/usr/bin/env python3
"""
Example: Data Validation and Monitoring with Penaltyblog

This example demonstrates how to use the new data validation and monitoring
features to ensure data quality and track data freshness.
"""

import pandas as pd
import penaltyblog as pb
from datetime import datetime

def main():
    print("🔍 Penaltyblog Data Validation & Monitoring Example")
    print("=" * 60)
    
    # Example 1: Basic Data Validation
    print("\n1. Basic Data Validation")
    print("-" * 30)
    
    # Create sample fixtures data
    fixtures_df = pd.DataFrame({
        'team_home': ['Arsenal', 'Chelsea', 'Liverpool', 'Man City'],
        'team_away': ['Tottenham', 'Man United', 'Newcastle', 'Brighton'],
        'goals_home': [2, 1, 3, 4],
        'goals_away': [1, 1, 1, 0],
        'date': pd.to_datetime(['2023-10-01', '2023-10-02', '2023-10-03', '2023-10-04'])
    })
    
    # Validate the data
    validation_report = pb.validate_fixtures(
        fixtures_df, 
        competition="Premier League", 
        season="2023-2024"
    )
    
    print(f"✅ Validation completed:")
    print(f"   - Errors: {len(validation_report['errors'])}")
    print(f"   - Warnings: {len(validation_report['warnings'])}")
    print(f"   - Info messages: {len(validation_report['info'])}")
    
    if validation_report['info']:
        print(f"   - Sample info: {validation_report['info'][0]}")
    
    # Example 2: Data Validation with Issues
    print("\n2. Data Validation with Issues")
    print("-" * 35)
    
    # Create problematic data
    problematic_df = pd.DataFrame({
        'team_home': ['Arsenal', 'Chelsea', '', 'Arsenal'],  # Empty team name, team plays itself
        'team_away': ['Tottenham', 'Man United', 'Liverpool', 'Arsenal'],
        'goals_home': [2, -1, 3, 15],  # Negative goals, unusually high score
        'goals_away': [1, 1, 1, 12],
        'date': pd.to_datetime(['2023-10-01', '2023-10-02', '2023-10-03', '2025-10-04'])  # Future date
    })
    
    try:
        validation_report = pb.validate_fixtures(
            problematic_df, 
            competition="Premier League", 
            season="2023-2024",
            strict_mode=False  # Don't raise exceptions for warnings
        )
        
        print(f"⚠️  Issues found:")
        for error in validation_report['errors']:
            print(f"   - ERROR: {error}")
        for warning in validation_report['warnings']:
            print(f"   - WARNING: {warning}")
    
    except Exception as e:
        print(f"❌ Validation failed: {e}")
    
    # Example 3: Cross-Source Validation
    print("\n3. Cross-Source Validation")
    print("-" * 30)
    
    # Create two data sources with slight differences
    source1_df = pd.DataFrame({
        'team_home': ['Arsenal', 'Chelsea'],
        'team_away': ['Tottenham', 'Man United'],
        'goals_home': [2, 1],
        'goals_away': [1, 1],
        'date': pd.to_datetime(['2023-10-01', '2023-10-02'])
    })
    
    source2_df = pd.DataFrame({
        'team_home': ['Arsenal', 'Chelsea'],
        'team_away': ['Tottenham', 'Man United'],
        'goals_home': [2, 1],
        'goals_away': [1, 2],  # Different result for second match
        'date': pd.to_datetime(['2023-10-01', '2023-10-02'])
    })
    
    cross_validation_report = pb.cross_validate_sources(
        source1_df, source2_df, 
        source1_name="FBRef", 
        source2_name="FootballData"
    )
    
    if 'cross_validation' in cross_validation_report:
        cv_results = cross_validation_report['cross_validation']
        print(f"🔀 Cross-validation results:")
        print(f"   - Common matches: {cv_results['common_matches']}")
        print(f"   - Goal mismatches: {cv_results['goal_mismatches']}")
        print(f"   - Mismatch rate: {cv_results['mismatch_rate']:.1%}")
    
    # Example 4: Data Freshness Monitoring
    print("\n4. Data Freshness Monitoring")
    print("-" * 32)
    
    # Record a data fetch
    pb.record_data_fetch(
        source="fbref",
        competition="Premier League", 
        season="2023-2024",
        df=fixtures_df
    )
    print("📝 Recorded data fetch for FBRef Premier League 2023-2024")
    
    # Check data freshness
    freshness = pb.check_data_freshness(
        source="fbref",
        competition="Premier League",
        season="2023-2024",
        max_age_hours=24
    )
    
    print(f"🕒 Data freshness check:")
    print(f"   - Is fresh: {freshness['is_fresh']}")
    print(f"   - Status: {freshness['status']}")
    print(f"   - Recommendation: {freshness['recommendation']}")
    if freshness['age_hours'] is not None:
        print(f"   - Age: {freshness['age_hours']:.2f} hours")
    
    # Example 5: Advanced Data Quality Validator
    print("\n5. Advanced Data Quality Validator")
    print("-" * 38)
    
    validator = pb.DataQualityValidator(strict_mode=False)
    
    # Validate fixtures data with detailed analysis
    detailed_report = validator.validate_fixtures_data(
        fixtures_df, 
        competition="Premier League", 
        season="2023-2024"
    )
    
    # Generate a human-readable summary
    summary = validator.generate_summary_report()
    print("📊 Detailed validation summary:")
    print(summary)
    
    # Example 6: Historical Data Coverage Analysis
    print("\n6. Historical Data Coverage Analysis")
    print("-" * 40)
    
    # Simulate multiple data sources
    data_sources = {
        'fbref_2023': fixtures_df.assign(source='fbref', season='2023-2024'),
        'footballdata_2023': fixtures_df.assign(source='footballdata', season='2023-2024'),
        'understat_2022': pd.DataFrame({
            'team_home': ['Arsenal', 'Chelsea'],
            'team_away': ['Liverpool', 'Man City'],
            'goals_home': [1, 2],
            'goals_away': [2, 1],
            'season': ['2022-2023', '2022-2023']
        })
    }
    
    required_seasons = ['2022-2023', '2023-2024', '2024-2025']
    
    coverage_report = validator.validate_historical_coverage(
        data_sources, 
        required_seasons=required_seasons
    )
    
    if 'coverage_analysis' in coverage_report:
        coverage = coverage_report['coverage_analysis']
        print(f"📈 Coverage analysis:")
        print(f"   - Sources analyzed: {len(coverage['sources'])}")
        if 'season_coverage' in coverage:
            season_cov = coverage['season_coverage']
            print(f"   - Season coverage: {season_cov['coverage_rate']:.1%}")
            if season_cov['missing']:
                print(f"   - Missing seasons: {', '.join(season_cov['missing'])}")
    
    print("\n" + "=" * 60)
    print("✅ Data validation and monitoring example completed!")
    print("\nKey takeaways:")
    print("- Use pb.validate_fixtures() for quick data validation")
    print("- Use pb.cross_validate_sources() to compare data sources")
    print("- Use pb.record_data_fetch() and pb.check_data_freshness() for monitoring")
    print("- Use DataQualityValidator for advanced validation features")


if __name__ == "__main__":
    main()