FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY code /app/code

WORKDIR /app/code

CMD ["python", "engine.py"]
