<!-- prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md) -->
# Writing your own preset

A preset is a TOML file with a `terms` array:

```toml
description = "Words our legal review flags in customer copy"
terms = [
    "guaranteed",
    "guaranteed returns",   # phrases work; whitespace matches any run of spaces
    "risk-free",            # hyphens work
    "pre-vetted",
]
```

Use it via config:

```toml
preset = "path/to/our-preset.toml"
```

or one-off on the command line:

```bash
prose-gate --preset path/to/our-preset.toml
```

## Matching rules to know

- Matching is case-insensitive and word-boundary anchored. `guaranteed`
  matches `Guaranteed` but not `guaranteed_by` (underscore joins the
  token) and not `guarantees` (different word).
- **Add inflections explicitly.** If you want `guarantee`, `guarantees`
  and `guaranteed`, list all three. The bundled presets carry common
  forms; copy their style.
- Longer terms win: with both `guaranteed` and `guaranteed returns` in the
  list, a sentence containing the phrase reports the phrase.
- A preset supplies the base list; per-project `extra_terms` in
  `.prose-gate.toml` are appended, so teams can share a preset and still
  add domain words like `flood-proof`.

## Choosing terms

Start from real incidents: sentences your legal/compliance review has
actually rewritten. A short list of words that genuinely recur beats a
long speculative one — every term costs review attention when it fires,
and a noisy gate gets disabled.
