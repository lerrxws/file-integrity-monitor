FROM nginx:1.30-alpine

COPY public/ /usr/share/nginx/html/

# Seed data initializes fresh shared volumes without replacing existing files.
COPY --chown=10001:10001 public/ /opt/website/public/

RUN mkdir -p /opt/website/.staging \
    && chown 10001:10001 /opt/website /opt/website/.staging
