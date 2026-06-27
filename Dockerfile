FROM nginx:alpine

# Static dashboard
COPY index.html /usr/share/nginx/html/
COPY cards.json /usr/share/nginx/html/

# Price data snapshots
COPY data/ /usr/share/nginx/html/data/

# Health check
COPY health_check.txt /usr/share/nginx/html/health

EXPOSE 80
