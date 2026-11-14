FROM python:3.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/fim

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 fim \
    && useradd --uid 10001 --gid fim --no-create-home fim \
    && mkdir -p data logs \
    && chown fim:fim data logs

COPY src ./src
COPY config/config.json ./config/config.json
COPY helpers ./helpers

USER fim

STOPSIGNAL SIGINT

CMD ["python", "src/main.py"]
