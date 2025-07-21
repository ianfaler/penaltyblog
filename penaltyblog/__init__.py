from . import (
    backtest,
    fpl,
    implied,
    kelly,
    matchflow,
    metrics,
    models,
    ratings,
    scrapers,
    utils,
)
from .version import __version__

# Make key utilities easily accessible
from .utils import (
    DataQualityValidator,
    validate_fixtures,
    cross_validate_sources,
    check_data_freshness,
    record_data_fetch,
)

__all__ = [
    "backtest",
    "fpl",
    "implied",
    "kelly",
    "matchflow",
    "metrics",
    "models",
    "ratings",
    "scrapers",
    "utils",
    "__version__",
    # Convenient access to key utilities
    "DataQualityValidator",
    "validate_fixtures",
    "cross_validate_sources",
    "check_data_freshness",
    "record_data_fetch",
]
