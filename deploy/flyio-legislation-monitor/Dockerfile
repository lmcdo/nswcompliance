FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pco_client.py .
COPY legislation_monitor.py .
COPY check_ip.py .
COPY run_loop.sh .

# Run the monitor weekly from inside the container. A one-shot script deployed as
# an always-on Fly app gets restart-looped on exit and suspended; the internal
# loop keeps the process alive. To grab the egress IP instead, override:
#   fly machine run . --command "python check_ip.py"
CMD ["sh", "run_loop.sh"]
