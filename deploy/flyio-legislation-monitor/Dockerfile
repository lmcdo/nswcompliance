FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pco_client.py .
COPY legislation_monitor.py .

COPY check_ip.py .

# Default: run legislation monitor in auto mode
CMD ["python", "legislation_monitor.py"]
