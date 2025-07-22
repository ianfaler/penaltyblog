"""Configuration package for penaltyblog league definitions."""

from .leagues import load_leagues, get_league_by_code

__all__ = ["load_leagues", "get_league_by_code"]