#!/usr/bin/env python3
"""
Daily Schedule Update Script
===========================

This script runs daily to update the football schedule with current week's fixtures.
It ensures that:
1. The schedule always shows the current week
2. Dates roll forward daily
3. Old data is archived
"""

import os
import sys
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def get_current_monday():
    """Get the Monday of the current week."""
    today = datetime.now()
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)

def get_week_dates(start_date):
    """Get all dates for a week starting from start_date."""
    return [start_date + timedelta(days=i) for i in range(7)]

def archive_old_data():
    """Archive old CSV files to prevent confusion."""
    data_dir = Path("data")
    archive_dir = data_dir / "archive"
    archive_dir.mkdir(exist_ok=True)
    
    today = datetime.now().date()
    
    for csv_file in data_dir.glob("*.csv"):
        try:
            # Parse date from filename (format: YYYY-MM-DD.csv)
            file_date_str = csv_file.stem
            file_date = datetime.strptime(file_date_str, "%Y-%m-%d").date()
            
            # Archive files older than 7 days
            if (today - file_date).days > 7:
                archive_path = archive_dir / csv_file.name
                shutil.move(str(csv_file), str(archive_path))
                print(f"📦 Archived old file: {csv_file.name}")
        except ValueError:
            # Skip files that don't match date format
            continue

def generate_realistic_match(home_team, away_team, match_date):
    """Generate realistic match data with predictions."""
    # Team strength ratings (simplified)
    team_strengths = {
        'Manchester City': 0.85, 'Arsenal': 0.82, 'Liverpool': 0.80,
        'Chelsea': 0.75, 'Newcastle': 0.72, 'Manchester United': 0.70,
        'Tottenham': 0.68, 'Brighton': 0.65, 'Aston Villa': 0.63,
        'West Ham': 0.60, 'Crystal Palace': 0.58, 'Brentford': 0.55,
        'Fulham': 0.53, 'Wolves': 0.50, 'Everton': 0.48,
        'Nottingham Forest': 0.45, 'Luton': 0.42, 'Burnley': 0.40,
        'Sheffield United': 0.38, 'Southampton': 0.35
    }
    
    home_strength = team_strengths.get(home_team, 0.50)
    away_strength = team_strengths.get(away_team, 0.50)
    
    # Home advantage
    home_strength += 0.1
    
    # Generate expected goals
    base_goals = 1.3  # Average goals per team per match
    xg_home = base_goals * home_strength * (2 - away_strength)
    xg_away = base_goals * away_strength * (2 - home_strength)
    
    # Add some randomness
    xg_home = max(0.1, xg_home + np.random.normal(0, 0.3))
    xg_away = max(0.1, xg_away + np.random.normal(0, 0.3))
    
    # Generate actual goals (Poisson-like distribution)
    goals_home = max(0, int(np.random.poisson(xg_home)))
    goals_away = max(0, int(np.random.poisson(xg_away)))
    
    # Calculate win probabilities based on expected goals
    home_win_prob = 1 / (1 + np.exp(-(xg_home - xg_away) * 0.5)) * 0.5 + 0.25
    away_win_prob = 1 / (1 + np.exp(-(xg_away - xg_home) * 0.5)) * 0.5 + 0.25
    draw_prob = max(0.1, 1 - home_win_prob - away_win_prob)
    
    # Ensure all probabilities are positive
    home_win_prob = max(0.1, home_win_prob)
    away_win_prob = max(0.1, away_win_prob)
    draw_prob = max(0.1, draw_prob)
    
    # Normalize probabilities
    total_prob = home_win_prob + draw_prob + away_win_prob
    home_win_prob /= total_prob
    draw_prob /= total_prob
    away_win_prob /= total_prob
    
    return {
        'date': match_date.strftime('%Y-%m-%d'),
        'team_home': home_team,
        'team_away': away_team,
        'goals_home': goals_home,
        'goals_away': goals_away,
        'xg_home': round(xg_home, 2),
        'xg_away': round(xg_away, 2),
        'home_win_prob': round(home_win_prob, 3),
        'draw_prob': round(draw_prob, 3),
        'away_win_prob': round(away_win_prob, 3)
    }

def generate_current_week_schedule():
    """Generate schedule for the current week."""
    teams = [
        'Manchester City', 'Arsenal', 'Liverpool', 'Chelsea', 'Newcastle',
        'Manchester United', 'Tottenham', 'Brighton', 'Aston Villa', 'West Ham',
        'Crystal Palace', 'Brentford', 'Fulham', 'Wolves', 'Everton',
        'Nottingham Forest', 'Southampton', 'Bournemouth', 'Burnley', 'Luton'
    ]
    
    monday = get_current_monday()
    week_dates = get_week_dates(monday)
    
    matches = []
    used_teams = set()
    
    # Generate 2-3 matches per day
    for i, match_date in enumerate(week_dates):
        matches_today = np.random.randint(2, 4)
        
        for _ in range(matches_today):
            # Pick random teams that haven't played this week
            available_teams = [t for t in teams if t not in used_teams]
            if len(available_teams) < 2:
                # Reset if we run out of teams
                used_teams.clear()
                available_teams = teams.copy()
            
            home_team = np.random.choice(available_teams)
            available_teams.remove(home_team)
            away_team = np.random.choice(available_teams)
            
            used_teams.add(home_team)
            used_teams.add(away_team)
            
            match = generate_realistic_match(home_team, away_team, match_date)
            matches.append(match)
    
    return matches

def update_schedule():
    """Main function to update the schedule."""
    print("🔄 Running daily schedule update...")
    
    # Archive old files
    archive_old_data()
    
    # Generate new schedule
    matches = generate_current_week_schedule()
    
    # Save to CSV with current Monday's date
    monday = get_current_monday()
    filename = f"data/{monday.strftime('%Y-%m-%d')}.csv"
    
    df = pd.DataFrame(matches)
    df.to_csv(filename, index=False)
    
    print(f"✅ Updated schedule saved to: {filename}")
    print(f"📅 Week of: {monday.strftime('%Y-%m-%d')} to {(monday + timedelta(days=6)).strftime('%Y-%m-%d')}")
    print(f"🏈 Generated {len(matches)} fixtures")
    
    # Display sample
    print("\n📋 Sample fixtures:")
    sample_df = df.head(5)[['date', 'team_home', 'team_away', 'home_win_prob', 'draw_prob', 'away_win_prob']]
    print(sample_df.to_string(index=False))
    
    return filename

if __name__ == "__main__":
    update_schedule()