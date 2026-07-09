import pytest

from app.data import get_source, list_sources


def test_two_sources_preconfigured() -> None:
    assert {s.key for s in list_sources()} == {"stocks", "bonds"}


def test_every_row_matches_declared_fields() -> None:
    for src in list_sources():
        rows = src.fetch()
        assert rows, f"{src.key} returned no rows"
        for row in rows:
            assert set(row) == set(src.fields), f"{src.key} row keys != fields"


def test_get_source_unknown_raises() -> None:
    with pytest.raises(KeyError):
        get_source("crypto")
