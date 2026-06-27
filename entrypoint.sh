#!/bin/sh
set -e

echo "=== MTG Reserved List Price Tracker ==="
echo "Starting initial price fetch..."

cd /app

# Initial fetch (fail gracefully)
python3 fetch_prices.py || echo "Initial fetch failed, will retry on cron"

# Start cron daemon (background)
crond -f -l 2 &

# Start nginx (foreground)
echo "Starting nginx..."
exec nginx -g "daemon off;"
