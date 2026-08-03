<!-- prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md) -->
# Lifting this directory into its own public repository

This directory is a self-contained package staged inside the product
repo. Publishing it means moving the *files*, never the git history —
the public repo starts from a fresh `git init`, so no product history,
paths or commit messages leak.

**Delete this file in the public repo.** It's the extraction manual, not
part of the product.

## Steps

```bash
# 1. Copy the directory out (files only, no .git)
cp -r oss/prose-gate ~/dev/prose-gate && cd ~/dev/prose-gate

# 2. Strip the internal hook-guard comments (they reference the private repo)
grep -rl "prior-art-checked" . | xargs sed -i '/prior-art-checked/d'
rm EXTRACTION.md

# 3. Fresh history
git init -b main
git add -A
git commit -m "prose-gate v0.1.0: diff-aware linter for assurance language"

# 4. Sanity: install + test + dogfood
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
prose-gate --full docs/why.md   # must exit 0

# 5. Create the PUBLIC GitHub repo and push
#    (github.com/new — no connection to the product repo)
git remote add origin git@github.com:<OWNER>/prose-gate.git
git push -u origin main
git tag v0.1.0 && git push origin v0.1.0
```

## Before announcing

- [ ] Check the name is free on PyPI (`pip index versions prose-gate`);
      if taken, rename package + CLI in `pyproject.toml`, `src/`, docs.
- [ ] Replace `OWNER` in `pyproject.toml` and `README.md` with your
      GitHub username.
- [ ] Confirm CI is green on the public repo (tests + dogfood jobs).
- [ ] Optional: publish to PyPI (`pip install build twine; python -m
      build; twine upload dist/*`) so `pip install prose-gate` works.
- [ ] Optional: submit the pre-commit hook to the pre-commit.com hooks
      index; list the Action on the GitHub Marketplace.
- [ ] Point the product repo's push gate at the public package (one real
      production user from day one — say so in the README honestly).

## Clean-room checklist (already applied, verify before push)

- [ ] No internal product names, pipeline names, table names or paths.
- [ ] No real regulatory data, coordinates or council names in fixtures —
      all test text is invented.
- [ ] No file copied from the product repo — this package was written
      fresh against the *pattern*, not the code.
