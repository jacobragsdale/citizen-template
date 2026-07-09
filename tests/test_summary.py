from app.data import get_source
from app.data.summary import numeric_fields, summarize


def test_numeric_fields_picks_numbers_only() -> None:
    stocks = get_source("stocks")
    assert set(numeric_fields(stocks.fetch())) == {"price", "change_pct", "volume"}


def test_summarize_reports_count_and_stats() -> None:
    text = summarize(get_source("stocks"))
    assert "10 records" in text
    assert "price:" in text
