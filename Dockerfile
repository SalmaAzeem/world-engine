FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y build-essential autoconf automake libtool pkg-config python3-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

COPY certs /app/certs

COPY code /app/code

WORKDIR /app/code

CMD ["python", "engine.py"]
