"""League registry management for penaltyblog."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class League:
    """Represents a football league configuration."""
    code: str
    name: str
    country: str
    tier: int
    season_id: str
    url_template: str

    @property
    def display_name(self) -> str:
        """Return a human-readable display name for the league."""
        return f"{self.country} {self.name}"

    def get_url(self) -> str:
        """Get the formatted URL for this league's data source."""
        return self.url_template.format(season_id=self.season_id)

def load_leagues() -> Dict[str, League]:
    """Load all leagues from the YAML configuration file."""
    config_file = Path(__file__).parent / "leagues.yaml"
    
    if not config_file.exists():
        raise FileNotFoundError(f"League configuration file not found: {config_file}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    leagues = {}
    for code, config in data['leagues'].items():
        leagues[code] = League(
            code=code,
            name=config['name'],
            country=config['country'],
            tier=config['tier'],
            season_id=config['season_id'],
            url_template=config['url_template']
        )
    
    return leagues

def get_league_by_code(league_code: str) -> Optional[League]:
    """Get a specific league by its code."""
    leagues = load_leagues()
    return leagues.get(league_code)

def get_leagues_by_tier(tier: int) -> Dict[str, League]:
    """Get all leagues of a specific tier."""
    leagues = load_leagues()
    return {code: league for code, league in leagues.items() if league.tier == tier}

def get_leagues_by_country(country: str) -> Dict[str, League]:
    """Get all leagues from a specific country."""
    leagues = load_leagues()
    return {code: league for code, league in leagues.items() if league.country.lower() == country.lower()}

def list_league_codes() -> list[str]:
    """Get a list of all available league codes."""
    leagues = load_leagues()
    return list(leagues.keys())

def get_default_league() -> League:
    """Get the default league (Premier League for backward compatibility)."""
    return get_league_by_code("ENG_PL")