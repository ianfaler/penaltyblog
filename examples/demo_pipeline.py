#!/usr/bin/env python3
"""
Penaltyblog Demo Pipeline
========================

This script demonstrates the core functionality of penaltyblog:
1. Data scraping from multiple sources
2. Model fitting and prediction
3. Implied probability calculation
4. Rating system computation
5. Metrics evaluation

Usage:
    python -m examples.demo_pipeline
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
    """Main demo pipeline."""
    print("=" * 60)
    print("🏈 PENALTYBLOG DEMO PIPELINE")
    print("=" * 60)

    # Create output directory
    output_dir = Path(__file__).parent / "demo_output"
    output_dir.mkdir(exist_ok=True)

    print(f"📁 Output directory: {output_dir.absolute()}")
    print()

    # Step 1: Data Scraping
    print("🔄 STEP 1: Data Scraping")
    print("-" * 30)

    try:
        # Use a reliable recent season for Premier League
        print("📡 Scraping Premier League 2023-2024 fixtures...")
        scraper = pb.scrapers.FootballData("ENG Premier League", "2023-2024")

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
            print("⚠️  Not enough completed matches, using all available data")
            completed_matches = df

        # Save scraped data
        output_file = output_dir / "scraped_fixtures.csv"
        completed_matches.to_csv(output_file, index=False)
        print(f"💾 Saved scraped data to: {output_file}")

    except Exception as e:
        print(f"❌ Error in data scraping: {e}")
        print("❌ Cannot proceed without real data. Please check your internet connection or try a different season.")
        return

    print()

    # Step 2: Model Training and Prediction
    print("🤖 STEP 2: Model Training & Prediction")
    print("-" * 40)

    try:
        # Prepare data for modeling
        print("🔧 Preparing data for modeling...")
        model_data = prepare_model_data(completed_matches)

        if len(model_data) < 5:
            print("⚠️  Not enough data for reliable modeling")
            return

        # Split data for training and prediction
        train_size = int(len(model_data) * 0.8)
        train_data = model_data.iloc[:train_size]
        test_data = model_data.iloc[train_size:]

        print(f"📊 Training data: {len(train_data)} matches")
        print(f"📊 Test data: {len(test_data)} matches")

        # Initialize and fit Poisson model
        print("🏗️  Training Poisson Goals Model...")
        model = pb.models.PoissonGoalsModel(
            goals_home=train_data["goals_home"].values,
            goals_away=train_data["goals_away"].values,
            teams_home=train_data["team_home"].values,
            teams_away=train_data["team_away"].values,
        )

        # Fit the model
        model.fit()
        print("✅ Model training completed")

        # Make predictions on test data
        print("🔮 Making predictions...")
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

        print(f"✅ Generated predictions for {len(results_df)} matches")

        # Save predictions
        pred_file = output_dir / "model_predictions.csv"
        results_df.to_csv(pred_file, index=False)
        print(f"💾 Saved predictions to: {pred_file}")

    except Exception as e:
        print(f"❌ Error in modeling: {e}")
        print("❌ Cannot proceed without proper model training.")
        return

    print()

    # Step 3: Implied Probabilities
    print("💰 STEP 3: Implied Probabilities")
    print("-" * 35)

    try:
        # Generate example odds
        print("🎲 Calculating implied probabilities...")

        # Use model predictions as "odds" for demonstration
        if "pred_home_win" in results_df.columns:
            # Convert probabilities to odds format
            odds_data = []
            for _, row in results_df.head(10).iterrows():
                # Convert probabilities to decimal odds (adding margin)
                margin = 0.05  # 5% bookmaker margin
                home_odds = (1 + margin) / row["pred_home_win"]
                draw_odds = (1 + margin) / row["pred_draw"]
                away_odds = (1 + margin) / row["pred_away_win"]

                odds_data.append(
                    {
                        "match": f"{row['team_home']} vs {row['team_away']}",
                        "home_odds": home_odds,
                        "draw_odds": draw_odds,
                        "away_odds": away_odds,
                    }
                )

            # Calculate implied probabilities using different methods
            implied_results = []
            for odds in odds_data:
                # Basic implied probability
                basic_home = 1 / odds["home_odds"]
                basic_draw = 1 / odds["draw_odds"]
                basic_away = 1 / odds["away_odds"]

                # Normalize using multiplicative method
                total = basic_home + basic_draw + basic_away
                norm_home = basic_home / total
                norm_draw = basic_draw / total
                norm_away = basic_away / total

                implied_results.append(
                    {
                        "match": odds["match"],
                        "implied_home": norm_home,
                        "implied_draw": norm_draw,
                        "implied_away": norm_away,
                        "total_prob": norm_home + norm_draw + norm_away,
                    }
                )

            implied_df = pd.DataFrame(implied_results)
            print(f"✅ Calculated implied probabilities for {len(implied_df)} matches")
            print(f"   Average probability sum: {implied_df['total_prob'].mean():.6f}")

            # Save implied probabilities
            implied_file = output_dir / "implied_probabilities.csv"
            implied_df.to_csv(implied_file, index=False)
            print(f"💾 Saved implied probabilities to: {implied_file}")

    except Exception as e:
        print(f"❌ Error in implied probability calculation: {e}")

    print()

    # Step 4: Team Ratings
    print("⭐ STEP 4: Team Ratings")
    print("-" * 25)

    try:
        print("📊 Calculating Elo ratings...")

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
        print(f"✅ Calculated ratings for {len(ratings_df)} teams")
        print(
            f"   Top team: {ratings_df.iloc[0]['team']} ({ratings_df.iloc[0]['rating']:.1f})"
        )
        print(
            f"   Rating range: {ratings_df['rating'].min():.1f} - {ratings_df['rating'].max():.1f}"
        )

        # Save ratings
        ratings_file = output_dir / "team_ratings.csv"
        ratings_df.to_csv(ratings_file, index=False)
        print(f"💾 Saved ratings to: {ratings_file}")

    except Exception as e:
        print(f"❌ Error in ratings calculation: {e}")

    print()

    # Step 5: Performance Metrics
    print("📈 STEP 5: Performance Metrics")
    print("-" * 30)

    try:
        if "pred_home_win" in results_df.columns and len(results_df) > 0:
            print("🎯 Calculating prediction metrics...")

            # Prepare actual results
            actual_results = []
            predicted_probs = []

            for _, row in results_df.iterrows():
                if pd.notna(row["goals_home"]) and pd.notna(row["goals_away"]):
                    home_goals = int(row["goals_home"])
                    away_goals = int(row["goals_away"])

                    # Convert to outcome vector [home_win, draw, away_win]
                    if home_goals > away_goals:
                        actual = [1, 0, 0]  # Home win
                    elif home_goals < away_goals:
                        actual = [0, 0, 1]  # Away win
                    else:
                        actual = [0, 1, 0]  # Draw

                    actual_results.append(actual)
                    predicted_probs.append(
                        [row["pred_home_win"], row["pred_draw"], row["pred_away_win"]]
                    )

            if len(actual_results) > 0:
                actual_array = np.array(actual_results)
                pred_array = np.array(predicted_probs)

                # Calculate Brier Score
                brier_scores = []
                for i in range(len(actual_results)):
                    brier = pb.metrics.multiclass_brier_score(
                        actual_array[i], pred_array[i]
                    )
                    brier_scores.append(brier)

                avg_brier = np.mean(brier_scores)
                print(f"✅ Average Brier Score: {avg_brier:.4f}")
                print(f"   Lower is better (perfect = 0.0, random = 0.5)")

                # Calculate prediction accuracy
                predicted_outcomes = np.argmax(pred_array, axis=1)
                actual_outcomes = np.argmax(actual_array, axis=1)
                accuracy = np.mean(predicted_outcomes == actual_outcomes)
                print(f"✅ Prediction Accuracy: {accuracy:.1%}")

                # Save metrics
                metrics_data = {
                    "metric": ["brier_score", "accuracy", "num_predictions"],
                    "value": [avg_brier, accuracy, len(actual_results)],
                }
                metrics_df = pd.DataFrame(metrics_data)
                metrics_file = output_dir / "performance_metrics.csv"
                metrics_df.to_csv(metrics_file, index=False)
                print(f"💾 Saved metrics to: {metrics_file}")

    except Exception as e:
        print(f"❌ Error in metrics calculation: {e}")

    print()

    # Final Summary
    print("📋 DEMO PIPELINE SUMMARY")
    print("=" * 60)

    output_files = list(output_dir.glob("*.csv"))
    if output_files:
        print("✅ Generated output files:")
        for file in sorted(output_files):
            size_kb = file.stat().st_size / 1024
            print(f"   📄 {file.name} ({size_kb:.1f} KB)")
    else:
        print("⚠️  No output files generated")

    print()
    print("🎉 Demo pipeline completed successfully!")
    print(f"🔍 Check the output directory: {output_dir.absolute()}")
    print()
    print("📚 Next steps:")
    print("   • Explore the generated CSV files")
    print("   • Check the documentation: https://penaltyblog.readthedocs.io/")
    print("   • Run 'pytest test/' to verify everything works")
    print("=" * 60)





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
