"""Preconfigured data sources.

Ready to use out of the box — no connection setup. Currently two mock sources:
`stocks` and `bonds`. Use them like:

    from app.data import get_source, list_sources

    for src in list_sources():        # catalog for menus
        print(src.key, src.label)

    rows = get_source("stocks").fetch()   # the records
"""

from app.data.base import DataSource, Row
from app.data.bonds import bonds
from app.data.stocks import stocks

__all__ = ["DataSource", "Row", "get_source", "list_sources"]

_SOURCES: dict[str, DataSource] = {stocks.key: stocks, bonds.key: bonds}


def list_sources() -> list[DataSource]:
    """All preconfigured sources, for building a menu the user picks from."""
    return list(_SOURCES.values())


def get_source(key: str) -> DataSource:
    """Look up one source by key (e.g. 'stocks'). Raises KeyError if unknown."""
    try:
        return _SOURCES[key]
    except KeyError:
        raise KeyError(f"unknown data source {key!r}; available: {sorted(_SOURCES)}") from None
