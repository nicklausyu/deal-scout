#!/usr/bin/env python3
"""
Deal Scout history/dedupe helper.

Takes candidate deals the agent already found (via its own web search),
keeps only ones that are verifiably 50%+ off (real bargains, not just
"on sale"), filters out anything reported in a previous run (tracked in
history.json), and writes output.json for the email step.

Usage: python3 dedupe.py candidates.json

candidates.json shape:
{
  "date": "YYYY-MM-DD",
  "items": [
    {"title": "...", "link": "...", "original_price": 229.00, "sale_price": 160.00, "category": "general"},
    {"title": "...", "link": "...", "original_price": 39.99, "sale_price": 14.97, "category": "kayak"},
    ...
  ]
}
"category" is "general", "electronics", or a watchlist keyword (anything
else is treated as a watchlist bucket, grouped by that keyword).

Discount is always computed here from original_price/sale_price (not taken
on faith from the source) - items without both real numbers, or where the
computed discount is below MIN_DISCOUNT_PCT, are dropped rather than reported.

Stdlib only - no pip install needed.
"""
import json
import sys
from datetime import datetime, timezone

HISTORY_FILE = "history.json"
OUTPUT_FILE = "output.json"
MIN_DISCOUNT_PCT = 50  # below this, it's not a "good deal" - drop it
STEAL_THRESHOLD = 70   # elite tier, called out on its own
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

        try:
            original = float(item["original_price"])
            sale = float(item["sale_price"])
        except (KeyError, TypeError, ValueError):
            continue  # no verifiable prices - can't confirm a real discount, skip
        if original <= 0 or sale < 0 or sale >= original:
            continue  # not an actual discount

        discount_pct = round((1 - sale / original) * 100)
        if discount_pct < MIN_DISCOUNT_PCT:
            continue  # below the bar - not worth reporting

        new_history[link] = today

        entry = {
            "title": item.get("title", ""),
            "link": link,
            "original_price": original,
            "sale_price": sale,
            "discount_pct": discount_pct,
        }
        category = item.get("category") or "general"

        if discount_pct >= STEAL_THRESHOLD:
            result["steals"].append(entry)
        elif category in DIRECT_CATEGORIES:
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
