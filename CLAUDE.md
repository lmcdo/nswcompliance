### 🚨 CRITICAL: Primary Directive (READ FIRST)
- **MANDATORY**: Always read `CLAUDE_PRIMARY_DIRECTIVE.md` at the start of EVERY session
- **EXECUTION RULE**: One PRP per session - NO EXCEPTIONS
- **MAIN REFERENCE**: `documentation/prps/PRP-A_MICRO_PIPELINE_IMPLEMENTATION.md`
- **SESSION CONTROL**: Run `./prp_checkpoints/session_control.sh` to check next PRP

### 🔄 Project Awareness & Context  
- **Always read `PLANNING.md`** at the start of a new conversation to understand the project's architecture, goals, style, and constraints.
- **Check `TASK.md`** before starting a new task. If the task isn't listed, add it with a brief description and today's date.
- **Use consistent naming conventions, file structure, and architecture patterns** as described in `PLANNING.md`.
- **Use venv_linux** (the virtual environment) whenever executing Python commands.

### 🧱 Code Structure & Modularity
- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- **Organize code into clearly separated modules**:
  - `regulatory-engine/` - RAG-Anything processing
  - `compliance/` - Compliance checking logic
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use python_dotenv and load_env()** for environment variables.

### 🧪 Testing & Reliability
- **Always create Pytest unit tests for new features**
- **Tests should live in a `/tests` folder** mirroring the main app structure.
  - Include at least:
    - 1 test for expected use
    - 1 edge case
    - 1 failure case

### ✅ Task Completion
- **Mark completed tasks in `TASK.md`** immediately after finishing them.
- Add new sub-tasks or TODOs discovered during development to `TASK.md` under "Discovered During Work".

### 📎 Style & Conventions
- **Use Python** for regulatory processing, TypeScript for Next.js integration
- **Follow PEP8**, use type hints, and format with `black`.
- **Use `pydantic` for data validation**.
- **Deterministic processing only** - NO AI interpretation of regulations
- Write **docstrings for every function** using the Google style

### 📚 Documentation & Explainability
- **Update `README.md`** when new features are added
- **Comment non-obvious code** and ensure everything is understandable
- When writing complex logic, **add an inline `# Reason:` comment**

### 🧠 AI Behavior Rules
- **Never assume missing context. Ask questions if uncertain.**
- **Never hallucinate libraries or functions** – only use known, verified Python packages.
- **Always confirm file paths and module names** exist before referencing them
- **Never delete or overwrite existing code** unless explicitly instructed
- **Never interpret regulations** - only extract and apply exact clauses
- **Never claim AI is interpreting regulations** - only retrieving exact clauses
- **Only use constraints that map to existing data fields** in the app