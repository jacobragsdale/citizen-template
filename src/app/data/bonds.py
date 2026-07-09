"""Mock 'bonds' data source: a small fixed-income portfolio snapshot.

Static, deterministic data. To use real data, replace the body of fetch() with
a real query and keep the same fields.
"""

from app.data.base import Row


class BondsSource:
    key = "bonds"
    label = "Bonds"
    description = "A small fixed-income snapshot: issuer, coupon, yield, maturity, and rating."
    fields = ["name", "issuer", "coupon_pct", "yield_pct", "maturity", "rating", "price"]

    def fetch(self) -> list[Row]:
        return [
            {
                "name": "US Treasury 2Y",
                "issuer": "US Government",
                "coupon_pct": 4.25,
                "yield_pct": 4.61,
                "maturity": "2027-06-30",
                "rating": "AAA",
                "price": 99.31,
            },
            {
                "name": "US Treasury 10Y",
                "issuer": "US Government",
                "coupon_pct": 4.00,
                "yield_pct": 4.28,
                "maturity": "2035-05-15",
                "rating": "AAA",
                "price": 97.85,
            },
            {
                "name": "US Treasury 30Y",
                "issuer": "US Government",
                "coupon_pct": 4.25,
                "yield_pct": 4.47,
                "maturity": "2055-05-15",
                "rating": "AAA",
                "price": 96.12,
            },
            {
                "name": "Apple 2031",
                "issuer": "Apple Inc.",
                "coupon_pct": 3.85,
                "yield_pct": 4.55,
                "maturity": "2031-08-04",
                "rating": "AA+",
                "price": 96.40,
            },
            {
                "name": "Microsoft 2033",
                "issuer": "Microsoft Corp.",
                "coupon_pct": 3.50,
                "yield_pct": 4.49,
                "maturity": "2033-02-12",
                "rating": "AAA",
                "price": 93.77,
            },
            {
                "name": "CA Muni GO 2034",
                "issuer": "State of California",
                "coupon_pct": 3.00,
                "yield_pct": 3.42,
                "maturity": "2034-10-01",
                "rating": "AA-",
                "price": 96.90,
            },
            {
                "name": "TIPS 2030",
                "issuer": "US Government",
                "coupon_pct": 1.75,
                "yield_pct": 2.05,
                "maturity": "2030-01-15",
                "rating": "AAA",
                "price": 98.55,
            },
            {
                "name": "HY Corp 2029",
                "issuer": "Frontier Energy",
                "coupon_pct": 7.25,
                "yield_pct": 8.10,
                "maturity": "2029-11-30",
                "rating": "BB",
                "price": 95.20,
            },
        ]


bonds = BondsSource()
