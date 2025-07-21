from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="PenaltyBlog ⚽ Data Viewer")

CSV_DIR = Path(__file__).resolve().parent.parent / "data"

def get_current_monday():
    """Get the Monday of the current week."""
    today = datetime.now()
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)

def current_week_csv() -> Path:
    """Find the CSV file for the current week."""
    monday = get_current_monday()
    current_week_file = CSV_DIR / f"{monday.strftime('%Y-%m-%d')}.csv"
    
    # If current week file exists, use it
    if current_week_file.exists():
        return current_week_file
    
    # Otherwise, fall back to most recent file
    files = sorted(CSV_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError("No CSV files produced yet. Run daily_update.py to generate current week's schedule.")
    return files[0]

def latest_csv() -> Path:
    """Find the most recent CSV file in the data directory."""
    return current_week_csv()

@app.get("/", response_class=HTMLResponse)
def root():
    """Return a minimal HTMX-powered table pulling JSON from /data."""
    monday = get_current_monday()
    week_end = monday + timedelta(days=6)
    
    return f"""
    <html><head>
      <script src="https://unpkg.com/htmx.org@1.9.12"></script>
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
      <title>PenaltyBlog Data</title>
    </head><body class="container">
      <h1>⚽ PenaltyBlog - Current Week Predictions</h1>
      <p><strong>Week of:</strong> {monday.strftime('%B %d, %Y')} - {week_end.strftime('%B %d, %Y')}</p>
      <p><em>Data updates daily to show current week's fixtures and predictions</em></p>
      
      <div>
        <button hx-get="/data" hx-target="#tbl" hx-trigger="click">Refresh Data 📥</button>
        <button hx-get="/update" hx-target="#status" hx-trigger="click">Generate New Schedule 🔄</button>
      </div>
      
      <div id="status"></div>
      <table id="tbl" class="striped" hx-get="/data" hx-trigger="load, every 30s"></table>
    </body></html>
    """

@app.get("/data", response_class=HTMLResponse)
def data_table():
    """Return HTML table rows for the latest CSV data."""
    try:
        df = pd.read_csv(latest_csv()).head(200)  # limit rows for browser
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    
    thead = "<thead><tr>" + "".join(f"<th>{c}</th>" for c in df.columns) + "</tr></thead>"
    rows = "<tbody>" + "".join(
        "<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>" for row in df.to_numpy()
    ) + "</tbody>"
    return thead + rows

@app.get("/data/json", response_class=JSONResponse)
def data_json():
    """Raw JSON endpoint (for future React/tableau use)."""
    df = pd.read_csv(latest_csv())
    return JSONResponse(df.to_dict(orient="records"))

@app.get("/update", response_class=HTMLResponse)
def update_schedule():
    """Manually trigger a schedule update."""
    try:
        import subprocess
        import sys
        
        # Run the daily update script
        result = subprocess.run([sys.executable, "daily_update.py"], 
                              capture_output=True, text=True, cwd=CSV_DIR.parent)
        
        if result.returncode == 0:
            return f"""
            <div class="success">
                <p>✅ Schedule updated successfully!</p>
                <details>
                    <summary>Update log</summary>
                    <pre>{result.stdout}</pre>
                </details>
            </div>
            """
        else:
            return f"""
            <div class="error">
                <p>❌ Update failed</p>
                <details>
                    <summary>Error details</summary>
                    <pre>{result.stderr}</pre>
                </details>
            </div>
            """
    except Exception as e:
        return f'<div class="error">❌ Error: {str(e)}</div>'

@app.get("/status")
def status():
    """Get current status information."""
    try:
        csv_file = current_week_csv()
        df = pd.read_csv(csv_file)
        
        monday = get_current_monday()
        week_end = monday + timedelta(days=6)
        
        return {
            "current_week": f"{monday.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}",
            "data_file": csv_file.name,
            "fixture_count": len(df),
            "date_range": f"{df['date'].min()} to {df['date'].max()}",
            "last_updated": csv_file.stat().st_mtime
        }
    except Exception as e:
        return {"error": str(e)}