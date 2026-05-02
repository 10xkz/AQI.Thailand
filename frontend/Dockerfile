# ── Frontend container: Nginx serving static files + API proxy ───────────────
FROM nginx:1.27-alpine

LABEL maintainer="pm25-monitor"
LABEL description="Thailand PM2.5 frontend — Nginx static server + reverse proxy to FastAPI backend"

# Remove the default Nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/pm25.conf

# Copy the static frontend
COPY index.html /usr/share/nginx/html/index.html

# Nginx listens on port 80
EXPOSE 80

# Healthcheck via the Nginx stub_status or a simple curl
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
