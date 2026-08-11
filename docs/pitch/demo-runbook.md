# Demo runbook — three-minute live proof

**Who this is for.** Lawrence, on his laptop, in front of one prospective buyer. **What it does.** Plants a defect in a tiny Python file, watches the file's own check go red, restores the file, and proves the restore is byte-identical. **Why it matters.** It shows — not tells — the one technique the reliability campaign was built on: **before I trust a check, I break the code underneath it and confirm the check goes red. A check that stays green when the code is broken is not a check.**

The demo replaces the diagram I can't build. If you have three minutes, you can run it. If they say "run it again on our code," the same harness runs on any Python file with an identifier you can name.

------------------------------------------------------------------------

## Dependencies (verified before the meeting)

- **Python 3.9+** (`python3 --version`). Uses stdlib only — no `pip install`.
- **The file `scripts/falsifiability.py`** from `github.com/lmcdo/nswcompliance`. I bring this pre-staged on the laptop; nothing is fetched during the demo.
- **A shell that supports heredocs** (`bash`, `zsh`, `sh`). Any laptop.

If any of the three is missing, stop and fix it *before* the meeting. Do not demo something you haven't run cold that morning.

------------------------------------------------------------------------

## Setup (once, morning of the meeting — 30 seconds)

    mkdir -p ~/demo && cd ~/demo
    cp ~/code/nswcompliance/scripts/falsifiability.py .

The `~/code/nswcompliance` path is where you clone the repo — adjust to yours. The scratch directory keeps the demo away from anything else on the laptop.

------------------------------------------------------------------------

## The demo (three commands, live, ~90 seconds)

### 1. Write the five-line file we're going to break

    cat > add.py <<'EOF'
    def add(a, b):
        return a + b


    assert add(2, 3) == 5
    EOF

Read it out loud: "One function. One check. The check runs at import — if `add` is wrong, the file exits non-zero."

### 2. Write the driver that plants → checks → restores

    cat > demo.py <<'EOF'
    """Plant a bug, watch a check catch it, restore the file byte-for-byte."""
    import subprocess, sys, hashlib
    from falsifiability import planted

    FILE = "add.py"

    def sha(): return hashlib.sha256(open(FILE, "rb").read()).hexdigest()

    def run():
        r = subprocess.run([sys.executable, FILE], capture_output=True, text=True)
        return r.returncode

    def show(label):
        print(f"  {label:<20} sha256={sha()[:12]}  check rc={run()}")

    print("BEFORE")
    show("baseline")

    print("\nPLANTING 'a + b' -> 'a - b'  (a silent-wrong-math bug)")
    before_sha = sha()
    with planted(FILE, "a + b", "a - b"):
        show("planted")

    print("\nAFTER (finally: block restored the file)")
    show("restored")

    print(f"\nbytes identical to baseline?  {sha() == before_sha}")
    EOF

Read out loud: "Three lines that matter. `with planted(...)` swaps `a + b` for `a - b`. Inside the block I re-run the check. On exit — even on a crash — the `finally` inside `planted` writes the original bytes back and re-hashes to prove it worked."

### 3. Run it

    python3 demo.py

**Expected output — this is what I got when I ran it while writing this runbook (sha256 will differ on their machine, everything else is exact):**

    BEFORE
      baseline             sha256=a1ea58c8278f  check rc=0

    PLANTING 'a + b' -> 'a - b'  (a silent-wrong-math bug)
      planted              sha256=60efe1c2df77  check rc=1

    AFTER (finally: block restored the file)
      restored             sha256=a1ea58c8278f  check rc=0

    bytes identical to baseline?  True

Point at the three rows and say the sentence out loud:

> "Baseline: the check passed. I planted a defect — different hash, and the check went red. I restored the file — same hash as baseline, and the check passed again. That last line is the one that matters: **byte-identical**. The proof I ran did not leave anything behind."

### 4. (Optional, if they ask "what if the restore fails?") — 20 seconds

    python3 falsifiability.py --check

**Expected:**

    FALSIFIABILITY: clean -- no planted defects left on disk.

Say: "Every plant writes a sidecar file before it edits anything. If a run dies mid-plant — kill -9, laptop lid, whatever — the sidecar survives. This CLI walks the tree looking for one; the same call runs in our pre-push git hook, so a planted defect physically cannot ship."

------------------------------------------------------------------------

## What can go wrong live, and what to do

| Symptom | Cause | Fix on the spot |
|----|----|----|
| `ModuleNotFoundError: No module named 'falsifiability'` | You cd'd out of `~/demo`, or forgot the `cp`. | `cd ~/demo && ls falsifiability.py`. If missing, `cp ~/code/nswcompliance/scripts/falsifiability.py .` |
| `planted check : rc=0` (should be 1) | Something odd about their Python — assertions disabled, `PYTHONOPTIMIZE` set. | Bail out: "let me not fake this, my machine at home just showed it going red — happy to send you the recording." Never talk past a demo that didn't do what you said. |
| A `PlantDidNotTake` traceback | The anchor string didn't match — someone edited `add.py` between steps. | Re-run step 1 (`cat > add.py ...`), then step 3 again. |
| Sidecar left behind (`add.py.falsifiability-bak`) | The demo crashed inside the `with` block. | `python3 falsifiability.py --recover` — this is the recovery the harness exists for; run it and show them the sidecar guard in action. |

**One rule.** If the demo doesn't do what the runbook says it will, **stop and say so.** "That didn't do what I told you it would" is the sentence that keeps the rest of the pitch honest. Never explain away a live failure — buyers can smell it and the whole meeting is over.

------------------------------------------------------------------------

## What the demo does not claim

- It doesn't say the technique is novel. Mutation-testing tooling exists. What's novel is the **rule** I run it under: no reliability finding leaves the repo without a planted defect that would have caught it.
- It doesn't say I wrote every line of `falsifiability.py`. Claude wrote most of it. I designed the two rules it enforces (plant must take, restore must complete), decided a warning was not enough (fail closed, not open), and decided the sidecar had to survive `SIGKILL` — that's why the pre-push guard in `.githooks/pre-push` is a shell search for `*.falsifiability-bak`, not a Python import that could itself be broken.
- It doesn't say every check on my repo works this way. Only the reliability findings that made it into the last twenty-nine PRs (#835–#906) use this discipline. For older code the honest answer is "I don't know whether the tests would go red — that's what I'd census on day one of an engagement."

------------------------------------------------------------------------

## Verification note

This runbook was executed end-to-end on 2026-08-09 in a scratch directory on the machine that wrote it. The captured output above is real; the sha256 values will differ on your laptop because the file's line endings may differ, but every other line will match byte-for-byte, and `bytes identical to baseline? True` is the only assertion that has to survive the transplant.
