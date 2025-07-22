#!/usr/bin/env python3
"""
Tests for reality check functionality.
"""

import subprocess
import json
import pathlib
import re
import pytest

@pytest.mark.integration
def test_reality_check_smoke():
    """Smoke test for reality check script."""
    result = subprocess.run(
        ["python", "scripts/reality_check.py"], 
        capture_output=True, 
        text=True,
        cwd="../",  # Run from project root
        timeout=300  # 5 minute timeout for scraping
    )
    
    # Check if the script ran without error
    assert result.returncode == 0, f"Reality check failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    
    # Quick sanity: JSON summary should be present
    assert re.search(r'"league":', result.stdout), "Expected JSON summary with league field not found in output"
    
    # Should contain validation summary
    assert "VALIDATION SUMMARY" in result.stdout, "Expected validation summary section not found"
    
    # Should contain either PASSED or FAILED
    assert ("Reality-check PASSED" in result.stdout or "Reality-check FAILED" in result.stdout), "Expected final status not found"

@pytest.mark.integration 
def test_reality_check_creates_output():
    """Test that reality check creates expected output files."""
    # Run reality check
    result = subprocess.run(
        ["poetry", "run", "python", "scripts/reality_check.py"], 
        capture_output=True, 
        text=True,
        timeout=300
    )
    
    # Check that data directory was created
    data_dir = pathlib.Path("data/reality_check")
    assert data_dir.exists(), "Reality check output directory not created"
    
    # Check that at least one CSV file was created
    csv_files = list(data_dir.glob("*.csv"))
    assert len(csv_files) > 0, "No CSV files created by reality check"