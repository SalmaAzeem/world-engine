FROM python:3.11-slim-bookworm

WORKDIR /app
RUN apt-get update && \
    for i in 1 2 3 4 5; do apt-get install -y --download-only build-essential autoconf automake libtool pkg-config python3-dev && break || sleep 5; done && \
    apt-get install -y build-essential autoconf automake libtool pkg-config python3-dev && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

COPY certs /app/certs

COPY code /app/code

WORKDIR /app/code

CMD ["python", "engine.py"]
