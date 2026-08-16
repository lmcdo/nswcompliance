#!/usr/bin/env python3
"""Push env vars to Fly.io app from local .env file."""
import subprocess
from dotenv import dotenv_values
from pathlib import Path

FLYCTL = r"C:\Users\lawre\.fly\bin\flyctl.exe"
APP = "plotdetect-legislation-monitor"

env = dotenv_values(Path(__file__).parent.parent / ".env")

pairs = {}
for key in ["DATABASE_URL", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]:
    val = env.get(key, "")
    if val:
        pairs[key] = val

if not pairs:
    print("No env vars found in .env")
    exit(1)

args = [FLYCTL, "-a", APP, "secrets", "set"]
for k, v in pairs.items():
    args.append(f"{k}={v}")

print(f"Setting {len(pairs)} env vars on {APP}...")
result = subprocess.run(args, capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print(result.stderr)
else:
    print("Done.")
