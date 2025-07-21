# Football Schedule Update System

## Problem Solved
The web application was showing predictions from January 2025 (last year's data) instead of the current week's schedule. This system now ensures:

✅ **Current week data**: Always shows this week's fixtures and predictions  
✅ **Daily updates**: Data automatically refreshes to stay current  
✅ **Date rolling**: Dates roll forward daily as expected  

## Files Changed

### 🆕 New Files
- `daily_update.py` - Generates current week's schedule with realistic predictions
- `setup_daily_updates.py` - Sets up automated daily updates  
- `generate_current_schedule.py` - Initial script to generate current week data
- `run_daily_update.sh` - Shell wrapper for automation (auto-generated)

### 📝 Modified Files
- `penaltyblog/web.py` - Updated to always serve current week's data
  - Added `current_week_csv()` function to find current week's file
  - Enhanced UI to show current week dates
  - Added manual update endpoint (`/update`)
  - Added status endpoint (`/status`)
  - Added auto-refresh every 30 seconds

## How It Works

### 1. Current Week Detection
```python
def get_current_monday():
    """Get the Monday of the current week."""
    today = datetime.now()
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)
```

### 2. Data Generation
- Generates realistic fixtures for current week (Monday to Sunday)
- Uses team strength ratings to create believable predictions
- Calculates expected goals (xG) and win probabilities
- Saves data as `YYYY-MM-DD.csv` where date = Monday of current week

### 3. Web Application Updates
- Automatically detects and serves current week's CSV file
- Falls back to most recent file if current week not available
- Shows current week dates in the UI
- Auto-refreshes data every 30 seconds

## Usage

### 🚀 Immediate Fix (Already Applied)
```bash
# Generate current week's data (already done)
python3 generate_current_schedule.py

# Start the web application  
cd penaltyblog
python3 -m uvicorn web:app --host 0.0.0.0 --port 8000
```

### 🔄 Daily Updates
```bash
# Manual update (run daily)
python3 daily_update.py

# Set up automated updates
python3 setup_daily_updates.py
```

### 🌐 Web Interface
- **Main page**: `http://localhost:8000` - Shows current week's schedule
- **Status**: `http://localhost:8000/status` - JSON status information  
- **Manual update**: Click "Generate New Schedule" button
- **Auto-refresh**: Page updates every 30 seconds

## Data Format
```csv
date,team_home,team_away,goals_home,goals_away,xg_home,xg_away,home_win_prob,draw_prob,away_win_prob
2025-07-21,Everton,Aston Villa,1,0,1.1,0.1,0.504,0.194,0.302
2025-07-22,West Ham,Fulham,0,0,0.1,0.1,0.577,0.281,0.142
...
```

## Automation Options

### Option 1: Manual Daily Run
```bash
python3 daily_update.py
```

### Option 2: Systemd Timer (Linux)
```bash
# Save service file to /etc/systemd/system/penaltyblog-update.service
# Save timer file to /etc/systemd/system/penaltyblog-update.timer
sudo systemctl enable penaltyblog-update.timer
sudo systemctl start penaltyblog-update.timer
```

### Option 3: Cron Job (if available)
```bash
# Runs daily at 6 AM
0 6 * * * /workspace/run_daily_update.sh
```

## Testing
```bash
# Check current status
curl http://localhost:8000/status

# View current data  
curl http://localhost:8000/data/json | head

# Trigger manual update
curl http://localhost:8000/update
```

## Result
🎯 **Problem Fixed**: Web application now shows current week's schedule with predictions that update daily, replacing the outdated January 2025 data.