FROM python:3.12

WORKDIR /app

COPY requirements.txt .

ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip && \
    if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

COPY . .

# Optional defaults suitable for ws behind proxies
ENV PROXY_HEADERS=true \
    FORWARDED_ALLOW_IPS=* \
    WS_PING_INTERVAL=20 \
    WS_PING_TIMEOUT=20

EXPOSE 8000

CMD ["python", "run.py"]
