# MCP SERVER CONFIGURATION STATUS

**CLAUDE: READ THIS FILE FIRST BEFORE TOUCHING ANY MCP CONFIGS**

## Current Working Servers
- ✅ **QGIS**: Working correctly
  - Command: `python`
  - Args: `["-m", "mcp_qgis"]`

## OSM/Geocoding Server - FAILED ATTEMPTS

### What Has Been Tried (DO NOT REPEAT):
1. ❌ `osm-mcp-server` with uvx - **DOES NOT EXIST as Python package**
2. ❌ `geocode-mcp` with uvx - **Failed to load**
3. ❌ Various --python flags with uvx - **Wrong approach**
4. ❌ Tried 10+ times with restarts - **All failed**

### Root Cause Analysis:
- **Problem**: Most OSM MCP servers are either:
  - Go binaries (not Python, can't use uvx)
  - Require complex setup (PostgreSQL, etc.)
  - Don't exist on PyPI despite documentation

### WORKING SOLUTIONS (Choose One):

#### Solution 1: Use Python geocoding directly (NO MCP)
```bash
pip install geopy nominatim
```
- Pro: Guaranteed to work, no MCP complexity
- Con: Not integrated with Claude Code MCP system

#### Solution 2: Download Go binary
- Download: https://github.com/NERVsystems/osmmcp/releases
- Get Windows .exe file
- Config:
```json
"osm": {
  "command": "C:/path/to/osmmcp.exe",
  "args": [],
  "env": {}
}
```

#### Solution 3: Give up on MCP geocoding
- Just use external APIs in scripts
- Use Planning Portal API (already working in project)

## Current Status: AWAITING USER DECISION

**USER: Which solution do you want to try?**
1. Install geopy/nominatim directly (no MCP)
2. Download the Go binary
3. Just use existing APIs in scripts

## Configuration File Location
`.claude/mcp.json`

---

## ✅ SOLUTION THAT WORKED (2025-10-24)

**Package: geocode-mcp**
- Type: Python package (works with uvx)
- Installation test: `uvx geocode-mcp --version` ✅ SUCCESS (37 packages installed)
- Configuration:
```json
"geocode-mcp": {
  "command": "uvx",
  "args": ["geocode-mcp"],
  "env": {}
}
```

**Method used to fix config file:**
- Bash cat with heredoc (Edit/Write tools were bugged)
- Command: `cat > .claude/mcp.json << 'EOF' ... EOF`

**Next action: Restart Claude Code**

---

## ✅ LinkedIn MCP Server (2025-11-18)

**Server: linkedin-mcp-server**
- Type: Docker container
- Image: `stickerdaniel/linkedin-mcp-server:latest`
- Requirements: Docker Desktop must be running
- GitHub: https://github.com/stickerdaniel/linkedin-mcp-server
- Configuration:
```json
"linkedin": {
  "command": "docker",
  "args": ["run", "--rm", "-i", "-e", "LINKEDIN_COOKIE", "stickerdaniel/linkedin-mcp-server:latest"],
  "env": {
    "LINKEDIN_COOKIE": "li_at=YOUR_COOKIE_VALUE"
  }
}
```

**CRITICAL:** Cookie value goes in `env` object, NOT in args array

**Cookie expires every 30 days** - update in `.claude/mcp.json` when expired

**Next action: Restart Claude Code**

**Configuration Error Fixed (2025-11-18):**
- ❌ WRONG: Cookie value hardcoded in args array with `-e LINKEDIN_COOKIE=li_at=...`
- ✅ CORRECT: Just `-e LINKEDIN_COOKIE` in args, actual value in env object

---

## ✅ Supabase MCP Server (2025-11-28)

**Server: Official Supabase MCP**
- Type: HTTP endpoint (not command-line)
- URL: `https://mcp.supabase.com/mcp`
- GitHub: https://github.com/supabase-community/supabase-mcp
- Docs: https://supabase.com/docs/guides/getting-started/mcp
- Configuration:
```json
"supabase": {
  "type": "http",
  "url": "https://mcp.supabase.com/mcp?project_ref=llzdrxywpziewrzudwhj"
}
```

**Features:**
- Query database tables
- Run SQL queries
- Manage schema and migrations
- View logs and configurations

**Authentication:** Uses OAuth - Claude Code will prompt for Supabase login on first use

**Next action: Restart Claude Code**

