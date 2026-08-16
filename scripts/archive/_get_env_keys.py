#!/usr/bin/env python3
from dotenv import dotenv_values
from pathlib import Path
env = dotenv_values(Path(__file__).parent.parent / ".env")
for k in ["DATABASE_URL", "SUPABASE_DB_URL", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]:
    v = env.get(k, "")
    if v:
        print(f"{k}={v[:30]}... (len={len(v)})")
    else:
        print(f"{k}=(not set)")
