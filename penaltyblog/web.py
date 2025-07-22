from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional, List
import logging

# Import league management
try:
    from .config.leagues import load_leagues, get_league_by_code, get_default_league
    from .utils.dates import in_next_week
except ImportError:
    # Fallback for development
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from config.leagues import load_leagues, get_league_by_code, get_default_league
    from utils.dates import in_next_week

app = FastAPI(title="PenaltyBlog ⚽ Data Viewer")

CSV_DIR = Path(__file__).resolve().parent.parent / "data"

def get_current_monday():
    """Get the Monday of the current week."""
    today = datetime.now()
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)

def _find_csvs(league_code: str = None) -> List[Path]:
    """Find CSV files for specific league or all leagues."""
    csv_files = []
    
    # Look for dated directories first (new structure)
    import re
    dated_dirs = sorted([d for d in CSV_DIR.iterdir() if d.is_dir() and re.match(r'\d{4}-\d{2}-\d{2}', d.name)], reverse=True)
    
    if dated_dirs:
        # Use the most recent dated directory
        latest_dir = dated_dirs[0]
        
        if league_code:
            # Look for specific league file
            league = get_league_by_code(league_code)
            if league:
                league_filename = f"{league.country.replace(' ', '_')}_{league.name.replace(' ', '_')}.csv"
                league_filename = "".join(c for c in league_filename if c.isalnum() or c in "._-")
                league_file = latest_dir / league_filename
                if league_file.exists():
                    csv_files.append(league_file)
        else:
            # Get all CSV files in the latest directory
            for csv_file in latest_dir.glob("*.csv"):
                if csv_file.name != "combined_leagues.csv":  # Skip combined file to avoid duplicates
                    csv_files.append(csv_file)
            
            # If no individual league files, fall back to combined
            if not csv_files:
                combined_file = latest_dir / "combined_leagues.csv"
                if combined_file.exists():
                    csv_files.append(combined_file)
    
    # Fallback to old single CSV structure
    if not csv_files:
        monday = get_current_monday()
        current_week_file = CSV_DIR / f"{monday.strftime('%Y-%m-%d')}.csv"
        
        if current_week_file.exists():
            csv_files.append(current_week_file)
        else:
            # Find most recent file
            files = sorted(CSV_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
            if files:
                csv_files.extend(files[:1])  # Just the most recent
    
    return csv_files

def find_league_csv(league_code: str = None) -> Path:
    """Find CSV file for a specific league or the default/combined data."""
    csv_files = _find_csvs(league_code)
    if not csv_files:
        raise FileNotFoundError("No CSV files produced yet. Run the match scraper to generate data.")
    return csv_files[0]

def _df_to_html_table(df: pd.DataFrame) -> str:
    """Convert DataFrame to HTML table format matching existing style."""
    if df.empty:
        return "<thead><tr><th>No Data</th></tr></thead><tbody><tr><td>No fixtures found for this week</td></tr></tbody>"
    
    # Sort by date for better readability
    if 'date' in df.columns:
        df = df.sort_values('date')
    
    thead = "<thead><tr>" + "".join(f"<th>{c}</th>" for c in df.columns) + "</tr></thead>"
    rows = "<tbody>" + "".join(
        "<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>" for row in df.to_numpy()
    ) + "</tbody>"
    return thead + rows

def get_available_leagues_from_data() -> List[str]:
    """Get list of available leagues from the data directory."""
    try:
        # Look in the most recent dated directory
        dated_dirs = sorted([d for d in CSV_DIR.iterdir() if d.is_dir() and d.name.match(r'\d{4}-\d{2}-\d{2}')], reverse=True)
        
        if dated_dirs:
            latest_dir = dated_dirs[0]
            csv_files = list(latest_dir.glob("*.csv"))
            
            # Extract league codes from filenames
            available_leagues = []
            configured_leagues = load_leagues()
            
            for csv_file in csv_files:
                if csv_file.name == "combined_leagues.csv":
                    continue
                
                # Try to match filename to league
                for code, league in configured_leagues.items():
                    expected_filename = f"{league.country.replace(' ', '_')}_{league.name.replace(' ', '_')}.csv"
                    expected_filename = "".join(c for c in expected_filename if c.isalnum() or c in "._-")
                    if csv_file.name == expected_filename:
                        available_leagues.append(code)
                        break
            
            return available_leagues
    except Exception:
        pass
    
    return []

def latest_csv() -> Path:
    """Find the most recent CSV file in the data directory."""
    return find_league_csv()

@app.get("/", response_class=HTMLResponse)
def root():
    """Return a minimal HTMX-powered table pulling JSON from /data."""
    try:
        available_leagues = get_available_leagues_from_data()
        configured_leagues = load_leagues()
        
        # Create league dropdown options
        league_options = []
        league_options.append('<option value="">All Leagues (Combined)</option>')
        
        for league_code in available_leagues:
            league = configured_leagues.get(league_code)
            if league:
                league_options.append(f'<option value="{league_code}">{league.display_name}</option>')
        
        league_dropdown = ''.join(league_options)
        
    except Exception as e:
        league_dropdown = '<option value="">Error loading leagues</option>'
    
    return f"""
    <html><head>
      <script src="https://unpkg.com/htmx.org@1.9.12"></script>
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
      <title>PenaltyBlog Data</title>
      <style>
        .controls {{ margin-bottom: 1rem; display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }}
        .controls > * {{ margin: 0; }}
      </style>
    </head><body class="container">
      <h1>⚽ PenaltyBlog - Football Data Viewer</h1>
      <p><em>Real football data from proven sources: FBRef, Understat, and Football-Data.co.uk</em></p>
      
      <div class="controls">
        <label for="league-select">League:</label>
        <select id="league-select" 
                hx-get="/data" 
                hx-target="#tbl" 
                hx-trigger="change"
                hx-vals="js:{{league: document.getElementById('league-select').value}}">
          {league_dropdown}
        </select>
        
        <button hx-get="/data" hx-target="#tbl" hx-trigger="click">Refresh Data 📥</button>
        <button hx-get="/scrape" hx-target="#status" hx-trigger="click">Scrape Fresh Data 🔄</button>
        <a href="/week">This Week 📅</a>
      </div>
      
      <div id="status"></div>
      <table id="tbl" class="striped" hx-get="/data" hx-trigger="load"></table>
    </body></html>
    """

@app.get("/data", response_class=HTMLResponse)
def data_table(league: Optional[str] = Query(None, description="League code to filter by")):
    """Return HTML table rows for the latest CSV data."""
    try:
        csv_file = find_league_csv(league)
        df = pd.read_csv(csv_file)
        
        # Filter by league if specified and we have league_code column
        if league and 'league_code' in df.columns:
            df = df[df['league_code'] == league]
        
        # Limit rows for browser performance
        df = df.head(200)
        
        if df.empty:
            return "<thead><tr><th>No Data</th></tr></thead><tbody><tr><td>No matches found for the selected league</td></tr></tbody>"
        
    except Exception as exc:
        logging.error(f"Error loading data: {exc}")
        return f"<thead><tr><th>Error</th></tr></thead><tbody><tr><td>Error loading data: {str(exc)}</td></tr></tbody>"
    
    thead = "<thead><tr>" + "".join(f"<th>{c}</th>" for c in df.columns) + "</tr></thead>"
    rows = "<tbody>" + "".join(
        "<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>" for row in df.to_numpy()
    ) + "</tbody>"
    return thead + rows

@app.get("/data/json", response_class=JSONResponse)
def data_json(league: Optional[str] = Query(None, description="League code to filter by")):
    """Raw JSON endpoint (for future React/tableau use)."""
    try:
        csv_file = find_league_csv(league)
        df = pd.read_csv(csv_file)
        
        # Filter by league if specified and we have league_code column
        if league and 'league_code' in df.columns:
            df = df[df['league_code'] == league]
        
        return JSONResponse(df.to_dict(orient="records"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/scrape", response_class=HTMLResponse)
def scrape_data():
    """Manually trigger a data scrape using the unified scraper with proven data sources."""
    try:
        import subprocess
        import sys
        
        # Run the unified scraper for major leagues (FBRef, Understat, Football-Data sources)
        result = subprocess.run([
            sys.executable, "-m", "penaltyblog.scrapers.unified_scraper", 
            "--league", "ENG_PL,ESP_LL,GER_BL,ITA_SA,FRA_L1", "--verbose"
        ], capture_output=True, text=True, cwd=CSV_DIR.parent)
        
        if result.returncode == 0:
            return f"""
            <div class="success">
                <p>✅ Data scraped successfully!</p>
                <details>
                    <summary>Scrape log</summary>
                    <pre>{result.stdout}</pre>
                </details>
            </div>
            """
        else:
            return f"""
            <div class="error">
                <p>❌ Scrape failed</p>
                <details>
                    <summary>Error details</summary>
                    <pre>{result.stderr}</pre>
                </details>
            </div>
            """
    except Exception as e:
        return f'<div class="error">❌ Error: {str(e)}</div>'

@app.get("/update", response_class=HTMLResponse)
def update_schedule():
    """Legacy endpoint - redirects to scrape."""
    return """
    <div class="info">
        <p>ℹ️ This endpoint has been updated. Use the "Scrape Fresh Data" button instead.</p>
        <p>The new system scrapes live data from official league websites.</p>
    </div>
    """

@app.get("/status")
def status():
    """Get current status information."""
    try:
        csv_file = latest_csv()
        df = pd.read_csv(csv_file)
        
        available_leagues = get_available_leagues_from_data()
        
        status_info = {
            "data_file": csv_file.name,
            "total_fixtures": len(df),
            "available_leagues": len(available_leagues),
            "league_codes": available_leagues,
            "last_updated": csv_file.stat().st_mtime
        }
        
        # Add date range if date column exists
        if 'date' in df.columns and not df.empty:
            status_info["date_range"] = f"{df['date'].min()} to {df['date'].max()}"
        
        # Add league breakdown if league_code column exists
        if 'league_code' in df.columns:
            league_counts = df['league_code'].value_counts().to_dict()
            status_info["fixtures_by_league"] = league_counts
        
        return status_info
    except Exception as e:
        return {"error": str(e)}

@app.get("/leagues")
def list_leagues():
    """Get list of all configured leagues."""
    try:
        leagues = load_leagues()
        available_from_data = get_available_leagues_from_data()
        
        league_list = []
        for code, league in leagues.items():
            league_info = {
                "code": code,
                "name": league.name,
                "country": league.country,
                "display_name": league.display_name,
                "tier": league.tier,
                "has_data": code in available_from_data
            }
            league_list.append(league_info)
        
        return {
            "total_configured": len(leagues),
            "total_with_data": len(available_from_data),
            "leagues": league_list
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/week", response_class=HTMLResponse)
def this_week(league: str | None = None):
    """Show fixtures scheduled within the next 7 days."""
    try:
        # 1️⃣ Load one league if ?league=, else concat all
        dfs = []
        for csv in _find_csvs(league):       # reuse existing helper
            df = pd.read_csv(csv, parse_dates=["date"])
            # Filter to this week's fixtures
            week_fixtures = df[df["date"].dt.date.apply(in_next_week)]
            if not week_fixtures.empty:
                dfs.append(week_fixtures)
        
        if not dfs:
            return f"""
            <html><head>
              <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
              <title>This Week's Fixtures</title>
            </head><body class="container">
              <h1>📅 This Week's Fixtures</h1>
              <p><a href="/">← Back to All Data</a></p>
              <p>No fixtures found for this week.</p>
            </body></html>
            """
        
        dfw = pd.concat(dfs)
        table_html = _df_to_html_table(dfw)        # reuse existing HTML formatter
        
        return f"""
        <html><head>
          <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
          <title>This Week's Fixtures</title>
        </head><body class="container">
          <h1>📅 This Week's Fixtures</h1>
          <p><a href="/">← Back to All Data</a></p>
          <p><em>Showing fixtures from today through the next 7 days</em></p>
          <table class="striped">{table_html}</table>
        </body></html>
        """
    except Exception as exc:
        logging.error(f"Error loading week view: {exc}")
        return f"""
        <html><head>
          <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
          <title>This Week's Fixtures - Error</title>
        </head><body class="container">
          <h1>📅 This Week's Fixtures</h1>
          <p><a href="/">← Back to All Data</a></p>
          <p>Error loading fixtures: {str(exc)}</p>
        </body></html>
        """