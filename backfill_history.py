#!/usr/bin/env python3
"""Backfill historical prices from MTGGoldfish for Reserved List cards.

Fixes:
- Browser-grade User-Agent (Cloudflare)
- urllib auto-follows 301 redirects (old URL → new URL)
- Robust chart data extraction from embedded JS
- Progress with ETA
"""

import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CARDS_FILE = Path(__file__).parent / "cards.json"
HISTORY_DIR = Path(__file__).parent / "data" / "history"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
DELAY = 1.5  # seconds between requests


def load_goldfish_urls():
    with open(CARDS_FILE) as f:
        config = json.load(f)
    return config.get("goldfish_urls", {})


def extract_chart_data(html):
    """Extract paper price history from MTGGoldfish HTML.

    Pattern: var d = [[Date.UTC(2012, 1, 1), 123.45], [Date.UTC(2012, 1, 2), 124.56], ...];
    """
    # Find all var d = [[...]] blocks
    matches = list(re.finditer(r'var\s+d\s*=\s*\[', html))
    if not matches:
        return None

    results = []
    for match in matches:
        # Extract the full array
        start = match.end() - 1  # include opening [
        depth = 0
        end = start
        for i in range(start, len(html)):
            if html[i] == '[':
                depth += 1
            elif html[i] == ']':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        if end <= start:
            continue

        array_str = html[start:end]

        # Parse [[Date.UTC(y,m,d), price], ...]
        points = re.findall(
            r'\[Date\.UTC\((\d{4}),\s*(\d{1,2}),\s*(\d{1,2})\)\s*,\s*([\d.]+)\]',
            array_str,
        )
        if points and len(points) > 30:  # must have substantial data
            series = []
            for y, m, d, price in points:
                ts = datetime(int(y), int(m) + 1, int(d), tzinfo=timezone.utc).timestamp() * 1000
                series.append([ts, float(price)])
            results.append(series)

    # Return the longest series (usually paper prices)
    if results:
        return max(results, key=len)
    return None


def ms_to_date(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def fetch_history(card_name, url):
    """Fetch MTGGoldfish page and extract price history."""
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })

    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            final_url = resp.geturl()
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ✗ HTTP error: {e}")
        return None

    data = extract_chart_data(html)

    if not data:
        print(f"  ⚠ No chart data (HTML: {len(html)} bytes)")
        return None

    return {
        "name": card_name,
        "source": "mtggoldfish",
        "source_url": final_url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "points": len(data),
        "first_date": ms_to_date(data[0][0]),
        "last_date": ms_to_date(data[-1][0]),
        "series": data,
    }


def main():
    urls = load_goldfish_urls()
    if not urls:
        print("No goldfish_urls found in cards.json.")
        return

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    total = len(urls)
    print(f"MTGGoldfish historical scraper — {total} cards")
    print(f"Delay: {DELAY}s (~{total*DELAY/60:.0f} min total)\n")

    success = 0
    for i, (card_name, url) in enumerate(urls.items()):
        safe_name = card_name.replace("/", "_").replace(" ", "_")
        print(f"[{i+1:2d}/{total}] {card_name:35s} ", end="", flush=True)

        result = fetch_history(card_name, url)

        if result:
            out_path = HISTORY_DIR / f"{safe_name}.json"
            with open(out_path, "w") as f:
                json.dump(result, f, indent=2)
            print(f"✓ {result['points']:>5d} pts  {result['first_date']} → {result['last_date']}")
            success += 1
        else:
            print("✗")

        if i < total - 1:
            time.sleep(DELAY)

    print(f"\n{'='*60}")
    print(f"Done: {success}/{total} cards with historical data")
    print(f"Data saved to: {HISTORY_DIR}")
    print(f"Dashboard: http://localhost:8080")


if __name__ == "__main__":
    main()
