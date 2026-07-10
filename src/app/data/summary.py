"""Dependency-free helpers for presenting a data source.

Stdlib only, so jobs (and tests) can use them without pulling in UI packages.
The Streamlit view helper for UI apps lives in the UI template, not here.
"""

from app.data.base import DataSource, Row


def numeric_fields(rows: list[Row]) -> list[str]:
    """Field names whose values are numbers (based on the first row)."""
    if not rows:
        return []
    return [
        key
        for key, value in rows[0].items()
        if isinstance(value, int | float) and not isinstance(value, bool)
    ]


def summarize(source: DataSource) -> str:
    """A plain-text summary: record count plus min/max/avg per numeric field."""
    rows = source.fetch()
    lines = [f"{source.label}: {len(rows)} records"]
    for field in numeric_fields(rows):
        values: list[float] = []
        for row in rows:
            value = row[field]
            if isinstance(value, int | float):
                values.append(float(value))
        if values:
            avg = sum(values) / len(values)
            lines.append(f"  {field}: min={min(values):.2f} max={max(values):.2f} avg={avg:.2f}")
    return "\n".join(lines)
