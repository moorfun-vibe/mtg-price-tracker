#!/bin/sh
set -e

echo "=== MTG Reserved List Price Tracker ==="

cd /app

# Initial fetch (non-blocking)
python3 fetch_prices.py 2>&1 || echo "Initial fetch skipped (will run on cron)"

# Start cron in background (without -f so it daemonizes)
crond -l 2

# Start nginx
echo "Starting nginx on :80..."
exec nginx -g "daemon off;"
