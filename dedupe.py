#!/usr/bin/env python3
"""
Deal Scout history/dedupe helper.

Takes candidate deals the agent already found (via its own web search),
filters out anything reported in a previous run (tracked in history.json),
tags steep discounts, and writes output.json for the email step.

Usage: python3 dedupe.py candidates.json

candidates.json shape:
{
  "date": "YYYY-MM-DD",
  "items": [
    {"title": "...", "link": "...", "discount_pct": 72, "category": "general"},
    {"title": "...", "link": "...", "discount_pct": null, "category": "kayak"},
    ...
  ]
}
"category" is "general", "electronics", or a watchlist keyword (anything
else is treated as a watchlist bucket, grouped by that keyword).

Stdlib only - no pip install needed.
"""
import json
import sys
from datetime import datetime, timezone

HISTORY_FILE = "history.json"
OUTPUT_FILE = "output.json"
STEAL_THRESHOLD = 70
MAX_HISTORY_ENTRIES = 5000
DIRECT_CATEGORIES = {"general", "electronics"}


def load_history():
    try:
        with open(HISTORY_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2, sort_keys=True)


def main():
    if len(sys.argv) != 2:
        print("usage: dedupe.py candidates.json", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        candidates = json.load(f)

    history = load_history()
    new_history = dict(history)
    today = candidates.get("date") or datetime.now(timezone.utc).date().isoformat()

    result = {"date": today, "steals": [], "watchlist": {}, "electronics": [], "general": []}

    for item in candidates.get("items", []):
        link = (item.get("link") or "").strip()
        if not link or link in history:
            continue
        new_history[link] = today

        entry = {
            "title": item.get("title", ""),
            "link": link,
            "discount_pct": item.get("discount_pct"),
        }
        category = item.get("category") or "general"

        if entry["discount_pct"] is not None and entry["discount_pct"] >= STEAL_THRESHOLD:
            result["steals"].append(entry)

        if category in DIRECT_CATEGORIES:
            result[category].append(entry)
        else:
            result["watchlist"].setdefault(category, []).append(entry)

    if len(new_history) > MAX_HISTORY_ENTRIES:
        new_history = dict(
            sorted(new_history.items(), key=lambda kv: kv[1])[-MAX_HISTORY_ENTRIES:]
        )

    save_history(new_history)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
