#!/usr/bin/env python3
"""
Main entry point for running the PenaltyBlog web interface.

Usage:
    python -m penaltyblog.web
    
or:
    python -m penaltyblog

"""
import sys
import uvicorn

def main():
    """Main entry point for the web interface."""
    # Check if the user wants to run the web interface
    if len(sys.argv) > 1 and sys.argv[1] == "web":
        # Remove 'web' from args and run uvicorn
        sys.argv.pop(1)
        uvicorn.run("penaltyblog.web:app", host="127.0.0.1", port=8000, reload=True)
    else:
        print("PenaltyBlog CLI")
        print("Usage:")
        print("  python -m penaltyblog web    # Start web interface")
        print("  make serve                   # Alternative way to start web interface")

if __name__ == "__main__":
    main()