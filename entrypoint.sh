#!/bin/sh
echo "MTG Price Tracker starting..."
cd /app
python3 fetch_prices.py 2>&1 || echo "fetch skipped"
echo "Starting nginx..."
exec nginx -g "daemon off;"
