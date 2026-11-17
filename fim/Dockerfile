FROM python:3.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./fim/requirements.txt

RUN pip install --no-cache-dir -r fim/requirements.txt \
    && groupadd --gid 10001 fim \
    && useradd --uid 10001 --gid fim --no-create-home fim \
    && mkdir -p fim/data fim/logs \
    && chown fim:fim fim/data fim/logs

COPY . ./fim/

USER fim

STOPSIGNAL SIGINT

CMD ["python", "-m", "fim"]
