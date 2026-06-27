FROM nginx:alpine

# Install python for price fetcher
RUN apk add --no-cache python3 py3-pip curl

# Nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# App: static dashboard + data
COPY index.html /app/
COPY cards.json /app/
COPY fetch_prices.py /app/

# Data directory (served by nginx)
RUN mkdir -p /app/data && chmod 755 /app/data

# Cron for daily price fetch
RUN echo "0 9 * * * cd /app && python3 fetch_prices.py" > /etc/crontabs/root
# Also run once on startup after a short delay
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
