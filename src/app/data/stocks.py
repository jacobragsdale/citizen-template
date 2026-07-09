"""Mock 'stocks' data source: a daily snapshot of well-known company shares.

Static, deterministic data so tests and the smoke run stay reliable. To use
real data, replace the body of fetch() with a market-data query and keep the
same fields.
"""

from app.data.base import Row


class StocksSource:
    key = "stocks"
    label = "Stocks"
    description = (
        "A daily snapshot of well-known company shares: symbol, name, sector, "
        "price, day change (change_pct), and trading volume."
    )
    fields = ["symbol", "name", "sector", "price", "change_pct", "volume"]

    def fetch(self) -> list[Row]:
        return [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "sector": "Technology",
                "price": 214.29,
                "change_pct": 0.84,
                "volume": 48_213_000,
            },
            {
                "symbol": "MSFT",
                "name": "Microsoft Corp.",
                "sector": "Technology",
                "price": 458.11,
                "change_pct": 1.12,
                "volume": 21_004_500,
            },
            {
                "symbol": "GOOGL",
                "name": "Alphabet Inc.",
                "sector": "Communication",
                "price": 182.66,
                "change_pct": -0.35,
                "volume": 27_890_100,
            },
            {
                "symbol": "AMZN",
                "name": "Amazon.com Inc.",
                "sector": "Consumer",
                "price": 198.42,
                "change_pct": 0.51,
                "volume": 33_120_800,
            },
            {
                "symbol": "NVDA",
                "name": "NVIDIA Corp.",
                "sector": "Technology",
                "price": 126.57,
                "change_pct": 2.43,
                "volume": 214_559_000,
            },
            {
                "symbol": "TSLA",
                "name": "Tesla Inc.",
                "sector": "Consumer",
                "price": 251.88,
                "change_pct": -1.67,
                "volume": 98_770_400,
            },
            {
                "symbol": "JPM",
                "name": "JPMorgan Chase",
                "sector": "Financials",
                "price": 205.34,
                "change_pct": 0.22,
                "volume": 8_442_300,
            },
            {
                "symbol": "XOM",
                "name": "Exxon Mobil",
                "sector": "Energy",
                "price": 113.09,
                "change_pct": -0.48,
                "volume": 14_998_200,
            },
            {
                "symbol": "JNJ",
                "name": "Johnson & Johnson",
                "sector": "Healthcare",
                "price": 148.72,
                "change_pct": 0.09,
                "volume": 6_331_900,
            },
            {
                "symbol": "WMT",
                "name": "Walmart Inc.",
                "sector": "Consumer",
                "price": 70.15,
                "change_pct": 0.63,
                "volume": 17_205_600,
            },
        ]


stocks = StocksSource()
