FROM python:3.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/publisher

RUN groupadd --gid 10001 publisher \
    && useradd --uid 10001 --gid publisher --no-create-home publisher

COPY src ./src
COPY config/config.json ./config/config.json
COPY templates ./templates
COPY helpers ./helpers

USER publisher

STOPSIGNAL SIGINT

CMD ["python", "src/main.py"]
