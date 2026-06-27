#!/usr/bin/env python3
"""Fetch current Reserved List prices from Scryfall API and save to daily JSON snapshot.

Scryfall's `prices.eur` field = Cardmarket Trend (EUR)
Scryfall's `prices.usd` field = TCGPlayer Market (USD)

Rate limit: 100ms delay between requests (Scryfall asks for 50-100ms).
"""

import json
import time
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

SCRYFALL_API = "https://api.scryfall.com/cards/named"
CARDS_FILE = Path(__file__).parent / "cards.json"
DATA_DIR = Path(__file__).parent / "data"
DELAY = 0.20  # 200ms between requests — < 10 req/s (Scryfall limit)
USER_AGENT = "MTGPriceTracker/1.0 (hermes-agent; Reserved List tracker)"


def load_cards():
    with open(CARDS_FILE) as f:
        return json.load(f)


def flatten_cards(config):
    """Return flat list of {name, category, set, category_label} from grouped config."""
    flat = []
    for cat_key, cat_data in config["categories"].items():
        for card in cat_data["cards"]:
            flat.append({
                "name": card["name"],
                "category": cat_key,
                "category_label": cat_data["label"],
                "set": card["set"],
            })
    return flat


def fetch_card(name, set_code):
    """Fetch a single card from Scryfall by exact name + set. Returns dict or None."""
    params = urllib.parse.urlencode({"exact": name, "set": set_code})
    url = f"https://api.scryfall.com/cards/named?{params}"
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data
    except urllib.error.HTTPError as e:
        if e.code == 429:
            # Rate limited — Scryfall asks for 60s cooldown
            print(f"  rate-limited, cooling down 65s...", file=sys.stderr)
            time.sleep(65)
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return json.loads(resp.read().decode())
            except Exception as e2:
                print(f"  still failed: {e2}", file=sys.stderr)
                return None
        body = e.read().decode()[:200] if e.fp else ""
        print(f"  HTTP {e.code}: {body[:80]}", file=sys.stderr)
    except Exception as e:
        print(f"  error: {e}", file=sys.stderr)
    return None


def main():
    config = load_cards()
    cards = flatten_cards(config)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    records = []
    total = len(cards)

    print(f"Fetching prices for {total} Reserved List cards...")
    print(f"Scryfall delay: {DELAY*1000:.0f}ms per card (~{total*DELAY:.0f}s total)\n")

    for i, card in enumerate(cards):
        name = card["name"]
        print(f"[{i+1:2d}/{total}] {name:35s} ... ", end="", flush=True)

        card_data = fetch_card(card["name"], card["set"])
        if card_data is None:
            print("SKIPPED")
            records.append({
                "name": name,
                "category": card["category"],
                "category_label": card["category_label"],
                "set": card["set"],
                "prices": {"eur": None, "usd": None},
                "scryfall_uri": None,
                "error": "not_found",
            })
        else:
            prices = card_data.get("prices", {})
            eur = prices.get("eur")
            usd = prices.get("usd")
            print(f"EUR={eur or 'N/A'} USD={usd or 'N/A'}")

            records.append({
                "name": name,
                "category": card["category"],
                "category_label": card["category_label"],
                "set": card["set"],
                "prices": {
                    "eur": float(eur) if eur else None,
                    "usd": float(usd) if usd else None,
                },
                "scryfall_uri": card_data.get("scryfall_uri"),
                "scryfall_id": card_data.get("id"),
                "released_at": card_data.get("released_at"),
            })

        if i < total - 1:
            time.sleep(DELAY)

    # Save daily snapshot
    snapshot = {
        "date": today,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "prices": records,
    }

    DATA_DIR.mkdir(exist_ok=True)
    out_path = DATA_DIR / f"{today}.json"
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    # Summary
    with_price = sum(1 for r in records if r["prices"]["eur"] is not None)
    print(f"\n✓ Saved {with_price}/{total} cards with prices → {out_path}")

    # Top movers preview (can't detect without yesterday's data, skip for now)
    top_eur = sorted(
        [r for r in records if r["prices"]["eur"]],
        key=lambda r: r["prices"]["eur"],
        reverse=True,
    )[:5]

    print("\nTop 5 by EUR price:")
    for r in top_eur:
        print(f"  {r['name']:30s}  €{r['prices']['eur']:>10,.2f}")


if __name__ == "__main__":
    main()
