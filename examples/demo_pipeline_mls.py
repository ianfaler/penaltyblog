#!/usr/bin/env python3
"""
Penaltyblog MLS Demo Pipeline
============================

This script demonstrates the core functionality of penaltyblog using MLS data:
1. Data scraping from MLS sources
2. Model fitting and prediction
3. Implied probability calculation
4. Rating system computation
5. Metrics evaluation

Usage:
    python examples/demo_pipeline_mls.py
"""

import os
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import penaltyblog as pb

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")


def main():
    """Main MLS demo pipeline."""
    print("=" * 60)
    print("⚽ PENALTYBLOG MLS DEMO PIPELINE")
    print("=" * 60)

    # Create output directory
    output_dir = Path(__file__).parent / "demo_output_mls"
    output_dir.mkdir(exist_ok=True)

    print(f"📁 Output directory: {output_dir.absolute()}")
    print()

    # Step 1: Data Scraping
    print("🔄 STEP 1: MLS Data Scraping")
    print("-" * 30)

    try:
        # Try FBRef for MLS data first
        print("📡 Attempting to scrape MLS 2024 fixtures from FBRef...")
        scraper = pb.scrapers.FBRef("USA Major League Soccer", "2024")

        # Get fixtures data
        df = scraper.get_fixtures()
        print(f"✅ Successfully scraped {len(df)} fixtures")
        print(
            f"   Date range: {df['datetime'].min().date()} to {df['datetime'].max().date()}"
        )
        print(
            f"   Teams: {df['team_home'].nunique() + df['team_away'].nunique() - len(set(df['team_home']) & set(df['team_away']))} unique teams"
        )

        # Filter to completed matches only
        completed_matches = df.dropna(subset=["goals_home", "goals_away"])
        print(f"   Completed matches: {len(completed_matches)}")

        if len(completed_matches) < 10:
            print("⚠️  Not enough completed matches from FBRef, trying alternative approach...")
            # Fall back to generating sample MLS data if scraping fails
            completed_matches = generate_sample_mls_data()
            print(f"   Using sample MLS data: {len(completed_matches)} matches")

        # Save scraped data
        output_file = output_dir / "mls_fixtures.csv"
        completed_matches.to_csv(output_file, index=False)
        print(f"💾 Saved MLS data to: {output_file}")

    except Exception as e:
        print(f"❌ Error in MLS data scraping: {e}")
        print("📊 Generating sample MLS data for demonstration...")
        completed_matches = generate_sample_mls_data()
        
        # Save sample data
        output_file = output_dir / "mls_fixtures.csv"
        completed_matches.to_csv(output_file, index=False)
        print(f"💾 Saved sample MLS data to: {output_file}")

    print()

    # Step 2: Model Training and Prediction
    print("🤖 STEP 2: MLS Model Training & Prediction")
    print("-" * 45)

    try:
        # Prepare data for modeling
        print("🔧 Preparing MLS data for modeling...")
        model_data = prepare_model_data(completed_matches)

        if len(model_data) < 5:
            print("⚠️  Not enough data for reliable modeling")
            return

        # Split data for training and prediction
        train_size = int(len(model_data) * 0.8)
        train_data = model_data.iloc[:train_size]
        test_data = model_data.iloc[train_size:]

        print(f"📊 Training data: {len(train_data)} MLS matches")
        print(f"📊 Test data: {len(test_data)} MLS matches")

        # Initialize and fit Poisson model
        print("🏗️  Training Poisson Goals Model on MLS data...")
        model = pb.models.PoissonGoalsModel(
            goals_home=train_data["goals_home"].values,
            goals_away=train_data["goals_away"].values,
            teams_home=train_data["team_home"].values,
            teams_away=train_data["team_away"].values,
        )

        # Fit the model
        model.fit()
        print("✅ MLS model training completed")

        # Make predictions on test data
        print("🔮 Making MLS predictions...")
        match_probs = []
        for _, row in test_data.iterrows():
            pred_grid = model.predict(row["team_home"], row["team_away"])
            home_win = pred_grid.home_win
            draw = pred_grid.draw
            away_win = pred_grid.away_win
            match_probs.append(
                {"home_win": home_win, "draw": draw, "away_win": away_win}
            )

        # Create results dataframe
        results_df = test_data.copy()
        results_df["pred_home_win"] = [p["home_win"] for p in match_probs]
        results_df["pred_draw"] = [p["draw"] for p in match_probs]
        results_df["pred_away_win"] = [p["away_win"] for p in match_probs]

        print(f"✅ Generated MLS predictions for {len(results_df)} matches")

        # Save predictions
        pred_file = output_dir / "mls_predictions.csv"
        results_df.to_csv(pred_file, index=False)
        print(f"💾 Saved MLS predictions to: {pred_file}")

    except Exception as e:
        print(f"❌ Error in MLS modeling: {e}")
        print("❌ Cannot proceed without proper model training.")
        return

    print()

    # Step 3: MLS Team Ratings
    print("⭐ STEP 3: MLS Team Ratings")
    print("-" * 30)

    try:
        print("📊 Calculating Elo ratings for MLS teams...")

        # Initialize Elo rating system
        elo_system = pb.ratings.Elo()

        # Calculate ratings for all completed matches
        ratings_history = []
        for _, match in completed_matches.iterrows():
            if pd.notna(match["goals_home"]) and pd.notna(match["goals_away"]):
                home_team = match["team_home"]
                away_team = match["team_away"]
                home_goals = int(match["goals_home"])
                away_goals = int(match["goals_away"])

                # Determine result (0=away win, 1=draw, 2=home win)
                if home_goals > away_goals:
                    result = 2  # Home win
                elif home_goals < away_goals:
                    result = 0  # Away win
                else:
                    result = 1  # Draw

                # Update ratings
                elo_system.update_ratings(home_team, away_team, result)

                ratings_history.append(
                    {
                        "date": match["datetime"],
                        "home_team": home_team,
                        "away_team": away_team,
                        "result": result,
                        "home_rating": elo_system.get_team_rating(home_team),
                        "away_rating": elo_system.get_team_rating(away_team),
                    }
                )

        # Get final ratings
        final_ratings = []
        for team in set(
            completed_matches["team_home"].tolist()
            + completed_matches["team_away"].tolist()
        ):
            if pd.notna(team):
                rating = elo_system.get_team_rating(team)
                final_ratings.append({"team": team, "rating": rating})

        ratings_df = pd.DataFrame(final_ratings).sort_values("rating", ascending=False)
        print(f"✅ Calculated ratings for {len(ratings_df)} MLS teams")
        print(
            f"   Top MLS team: {ratings_df.iloc[0]['team']} ({ratings_df.iloc[0]['rating']:.1f})"
        )
        print(
            f"   Rating range: {ratings_df['rating'].min():.1f} - {ratings_df['rating'].max():.1f}"
        )

        # Save ratings
        ratings_file = output_dir / "mls_team_ratings.csv"
        ratings_df.to_csv(ratings_file, index=False)
        print(f"💾 Saved MLS ratings to: {ratings_file}")

    except Exception as e:
        print(f"❌ Error in MLS ratings calculation: {e}")

    print()

    # Final Summary
    print("📋 MLS DEMO PIPELINE SUMMARY")
    print("=" * 60)

    output_files = list(output_dir.glob("*.csv"))
    if output_files:
        print("✅ Generated MLS output files:")
        for file in sorted(output_files):
            size_kb = file.stat().st_size / 1024
            print(f"   📄 {file.name} ({size_kb:.1f} KB)")
    else:
        print("⚠️  No output files generated")

    print()
    print("🎉 MLS demo pipeline completed successfully!")
    print(f"🔍 Check the MLS output directory: {output_dir.absolute()}")
    print()
    print("📚 Next steps:")
    print("   • Explore the generated MLS CSV files")
    print("   • Compare with Premier League results")
    print("   • Try different MLS seasons or teams")
    print("=" * 60)


def generate_sample_mls_data():
    """Generate sample MLS data if scraping fails."""
    print("🏗️  Generating sample MLS 2024 data...")
    
    # Real MLS teams for 2024
    mls_teams = [
        "Inter Miami CF", "LA Galaxy", "Los Angeles FC", "Seattle Sounders FC",
        "Portland Timbers", "Austin FC", "Real Salt Lake", "Colorado Rapids",
        "Vancouver Whitecaps FC", "San Jose Earthquakes", "Houston Dynamo FC",
        "FC Dallas", "Sporting Kansas City", "Minnesota United FC", "Chicago Fire FC",
        "Atlanta United FC", "Orlando City SC", "Charlotte FC", "CF Montréal",
        "Toronto FC", "New York City FC", "New York Red Bulls", "Philadelphia Union",
        "New England Revolution", "Columbus Crew", "FC Cincinnati", "Nashville SC",
        "D.C. United", "St. Louis City SC"
    ]
    
    # Generate sample matches
    matches = []
    np.random.seed(42)  # For reproducible results
    
    # Generate matches for different months
    for month in range(3, 11):  # March to October (MLS season)
        for _ in range(20):  # 20 matches per month
            home_team = np.random.choice(mls_teams)
            away_team = np.random.choice([t for t in mls_teams if t != home_team])
            
            # Generate realistic MLS scores
            home_goals = np.random.poisson(1.3)  # MLS average around 1.3 goals per team
            away_goals = np.random.poisson(1.1)  # Slightly lower for away teams
            
            match_date = pd.Timestamp(f"2024-{month:02d}-{np.random.randint(1, 29):02d}")
            
            matches.append({
                "datetime": match_date,
                "team_home": home_team,
                "team_away": away_team,
                "goals_home": home_goals,
                "goals_away": away_goals,
                "competition": "USA Major League Soccer",
                "season": "2024"
            })
    
    return pd.DataFrame(matches)


def prepare_model_data(df):
    """Prepare data for model training."""
    model_df = df.copy()

    # Ensure we have the required columns
    required_cols = ["team_home", "team_away", "goals_home", "goals_away", "datetime"]

    for col in required_cols:
        if col not in model_df.columns:
            if col in ["goals_home", "goals_away"]:
                # Use alternative column names if available
                alt_names = {
                    "goals_home": ["fthg", "home_goals", "FTHG"],
                    "goals_away": ["ftag", "away_goals", "FTAG"],
                }
                for alt_name in alt_names.get(col, []):
                    if alt_name in model_df.columns:
                        model_df[col] = model_df[alt_name]
                        break
                else:
                    # Column not found and no alternative - this indicates a data issue
                    raise ValueError(f"Required column '{col}' not found in scraped data")

    # Filter to completed matches
    model_df = model_df.dropna(subset=["goals_home", "goals_away"])

    # Ensure goals are integers
    model_df["goals_home"] = model_df["goals_home"].astype(int)
    model_df["goals_away"] = model_df["goals_away"].astype(int)

    return model_df


if __name__ == "__main__":
    main()