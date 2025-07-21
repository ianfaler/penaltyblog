from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="PenaltyBlog ⚽ Data Viewer")

CSV_DIR = Path(__file__).resolve().parent.parent / "data"

def latest_csv() -> Path:
    """Find the most recent CSV file in the data directory."""
    files = sorted(CSV_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError("No CSV files produced yet.")
    return files[0]

@app.get("/", response_class=HTMLResponse)
def root():
    """Return a minimal HTMX-powered table pulling JSON from /data."""
    return """
    <html><head>
      <script src="https://unpkg.com/htmx.org@1.9.12"></script>
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
      <title>PenaltyBlog Data</title>
    </head><body class="container">
      <h1>Latest PenaltyBlog Dataset</h1>
      <button hx-get="/data" hx-target="#tbl" hx-trigger="click">Refresh 📥</button>
      <table id="tbl" class="striped"></table>
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