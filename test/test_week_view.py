from fastapi.testclient import TestClient
from penaltyblog.web import app

def test_week_view():
    client = TestClient(app)
    r = client.get("/week")
    assert r.status_code == 200
    assert "<table" in r.text or "No fixtures" in r.text

def test_week_view_with_league():
    """Test week view with league parameter."""
    client = TestClient(app)
    r = client.get("/week?league=ENG_PL")
    assert r.status_code == 200
    # Should either have table or no fixtures message
    assert "<table" in r.text or "No fixtures" in r.text

def test_week_view_html_structure():
    """Test that week view returns proper HTML structure."""
    client = TestClient(app)
    r = client.get("/week")
    assert r.status_code == 200
    assert "<html>" in r.text
    assert "This Week's Fixtures" in r.text
    assert "← Back to All Data" in r.text