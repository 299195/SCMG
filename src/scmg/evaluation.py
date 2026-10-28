"""Small, framework-neutral helpers for summarizing evaluation rows."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize attempted, valid, write-positive, and reuse-positive rows.

    Reuse rate is conditional on a positive write. Errors remain visible in the
    attempted count and are excluded only from the valid denominator.
    """

    valid = [row for row in rows if not row.get("error")]
    writes = [row for row in valid if row.get("write_positive")]
    reuses = [row for row in writes if row.get("reuse_positive")]
    by_category: dict[str, dict[str, int]] = defaultdict(
        lambda: {"attempted": 0, "valid": 0, "write_positive": 0, "reuse_positive": 0}
    )
    for row in rows:
        bucket = by_category[str(row.get("category", "unknown"))]
        bucket["attempted"] += 1
        if row.get("error"):
            continue
        bucket["valid"] += 1
        bucket["write_positive"] += int(bool(row.get("write_positive")))
        bucket["reuse_positive"] += int(
            bool(row.get("write_positive") and row.get("reuse_positive"))
        )

    categories = {}
    for name, counts in sorted(by_category.items()):
        categories[name] = {
            **counts,
            "write_rate": rate(counts["write_positive"], counts["valid"]),
            "conditional_reuse_rate": rate(
                counts["reuse_positive"], counts["write_positive"]
            ),
        }
    return {
        "attempted": len(rows),
        "valid": len(valid),
        "errors": len(rows) - len(valid),
        "write_positive": len(writes),
        "reuse_positive": len(reuses),
        "write_rate": rate(len(writes), len(valid)),
        "conditional_reuse_rate": rate(len(reuses), len(writes)),
        "by_category": categories,
    }
