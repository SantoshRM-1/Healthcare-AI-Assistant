"""Routing vocabulary supplied by the project owner; not a diagnostic knowledge base."""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=1)
def load_taxonomy() -> list[dict[str, Any]]:
    path = Path(__file__).parents[1] / "knowledge" / "medical_taxonomy.json"
    return json.loads(path.read_text(encoding="utf-8"))["sectors"]


def match_reported_conditions(text: str) -> list[dict[str, str]]:
    """Match literal condition names for routing; never infer from lab values."""
    normalized = re.sub(r"\s+", " ", text.casefold())
    matches: list[dict[str, str]] = []
    for sector in load_taxonomy():
        for condition in sector["conditions"]:
            phrase = re.sub(r"\s+", " ", condition.casefold())
            variants = {phrase}
            if phrase.endswith("ies"):
                variants.add(phrase[:-3] + "y")
            elif phrase.endswith("s"):
                variants.add(phrase[:-1])
            found = next(
                (
                    candidate
                    for variant in variants
                    if (candidate := re.search(rf"(?<!\w){re.escape(variant)}(?!\w)", normalized))
                ),
                None,
            )
            if not found:
                continue
            lead_in = normalized[max(0, found.start() - 35) : found.start()]
            if re.search(
                r"\b(no|not|never|without|denies|negative for)\s+(?:a\s+|any\s+)?$", lead_in
            ):
                continue
            specialties = sector["specialties"]
            # Keep the project's existing stone-to-urology route specific.
            if sector["name"] == "Nephrology" and "stone" in phrase:
                specialties = ["Urologist"]
            matches.append(
                {"sector": sector["name"], "condition": condition, "specialties": specialties}
            )
    return matches
