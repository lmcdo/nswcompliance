FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pco_client.py .
COPY legislation_monitor.py .
# refresh_runbook became an import of legislation_monitor in #504 and was never
# added here, so the container died at import on every cycle — and run_loop.sh
# swallows that with `|| echo "will retry next cycle"`, so the machine stayed
# `started` and silent. Verified 2026-08-14 by running the monitor on the live
# machine: ModuleNotFoundError: No module named 'refresh_runbook'.
# tests/test_dockerfile_monitors_imports.py now fails if any local import of a
# COPYd module is not itself COPYd — mutation-checked in both directions.
COPY refresh_runbook.py .
# Weekly provenance check (scripts/provenance_check.py): traces every served rule
# with a quote to its clause in the law in force; alerts on any break.
COPY provenance_check.py .
COPY secondary_dwelling_paths.py .
COPY check_ip.py .
COPY run_loop.sh .

# Run the monitor weekly from inside the container. A one-shot script deployed as
# an always-on Fly app gets restart-looped on exit and suspended; the internal
# loop keeps the process alive. To grab the egress IP instead, override:
#   fly machine run . --command "python check_ip.py"
CMD ["sh", "run_loop.sh"]
