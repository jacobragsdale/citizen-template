"""The data-source interface every source implements.

The app talks to data ONLY through this shape, so mock and real sources are
interchangeable. To move a source to real data later, replace its `fetch()`
with a real query or HTTP call and keep `key`, `label`, `fields`, and the
return shape (a list of flat dict rows) identical — nothing else in the app
needs to change.
"""

from typing import Protocol, runtime_checkable

# One record. Flat mapping of field name -> value (str/number/etc.).
Row = dict[str, object]


@runtime_checkable
class DataSource(Protocol):
    key: str  # stable id used in code/state, e.g. "stocks"
    label: str  # friendly name shown to the user, e.g. "Stocks"
    description: str  # one plain-language sentence about the data
    fields: list[str]  # column names, in display order

    def fetch(self) -> list[Row]:
        """Return the current records. Mock sources return baked data."""
        ...


def as_float(row: Row, key: str) -> float:
    """Read a numeric field from a row as a float.

    Row values are typed `object` (a row can hold strings or numbers), so plain
    `float(row["price"])` fails the basedpyright gate. Use this to narrow safely:

        from app.data import as_float
        total = sum(as_float(r, "price") for r in rows)
    """
    value = row[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"row field {key!r} is not numeric: {value!r}")
    return float(value)
