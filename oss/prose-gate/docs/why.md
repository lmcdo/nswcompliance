<!-- prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md) -->
# Why prose-gate exists

*This file is linted in CI by prose-gate itself, with the `assurance`
preset. Every flagged word below carries a visible pragma; everything else
had to be written without them.*

## Copy is a legal surface

A product that presents analysis of regulated subject matter — a flood
layer on a map, a projected return, a planning constraint — lives one
sentence away from giving professional advice. The data can be presented
with careful sourcing, and the interface copy around it can still make a
promise the company never meant to sign:

> "This site is safe to build on." <!-- prose-gate: allow(safe) -->

The words that do the damage are ordinary ones:
`guaranteed`, `verified`, `compliant`, `recommended`. <!-- prose-gate: allow -->
Each converts a statement *about data* into a statement *about the
world*, and in most jurisdictions the second kind carries liability the
first kind does not (misleading-conduct provisions in consumer law,
negligent misstatement at common law).

Engineers have type checkers for function signatures and schema contracts
for APIs. The text shipped to users deserves a gate of the same kind:
deterministic, boring, and always on.

## Why diff-aware matters

Every team that tries to adopt a copy rule in a mature codebase meets the
same wall: the first run flags a thousand historical lines, the cleanup
becomes a project, the project never starts, the rule dies.

prose-gate scans only lines *added* since the base branch. The day it is
installed, nothing old is flagged — but every sentence written from that
day forward is held to the rule. The backlog becomes a separate, optional
audit (`--full`), not the price of entry.

## Why deterministic, in the age of generated text

More and more interface copy is drafted by language models. Generated
text is fluent, plausible and tonally drifty — it reaches for warm,
assuring words precisely because they are the most statistically likely
ones. Human review attention, meanwhile, drops as volume rises.

That combination is exactly the argument for a gate with no judgment in
it. A word-boundary regex has no off days, no context window and no
desire to be helpful. Systems that generate text at scale need at least
one layer between them and the user that cannot be persuaded.

## Why the pragma leaves a trail

Real exemptions exist. Quoting a source document verbatim is the obvious
one — if a regulation says a design
"must be certified", the quotation keeps the word. <!-- prose-gate: allow(certified) -->

An inline pragma (`prose-gate: allow(term)`) makes the exemption part of
the diff: a reviewer sees the waiver next to the sentence it waives, and
`--format json` counts the waivers so the number is watchable over time.
A suppression you can't see or count is just a hole; one you can see and
count is a policy.

## Where it came from

prose-gate was extracted from the internal toolchain of a production
planning-data product, where a stricter variant of the `assurance` preset
has gated every push since early 2026. The extraction is a clean rewrite:
generic naming, configurable term lists, synthetic fixtures — and the
lessons kept intact.
