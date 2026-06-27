FROM nginx:alpine

# Copy static dashboard
COPY index.html /usr/share/nginx/html/
COPY cards.json /usr/share/nginx/html/

# Health check
COPY health_check.txt /usr/share/nginx/html/health

# Nginx config — serve data/ as static files
RUN mkdir -p /usr/share/nginx/html/data
COPY data/.gitkeep /usr/share/nginx/html/data/

EXPOSE 80
