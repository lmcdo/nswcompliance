# Council words — the standard every served rule is judged against

This file is the fixed brief given to the AI reviewer, and the standard a person can hold us to.
It changes only by pull request. Decided by the user on 2026-10-12.

## What the app is for
Give a user the council's (or the State's) actual planning controls that apply to their property,
deterministically: the control itself, in the authority's own words, with exactly where it is printed.
The app formulates numbers from those words; the words are the receipt.

## The rule shown must be one of three states
| State | Meaning | Who decides |
|---|---|---|
| `exact` | the whole quote is printed word for word in the plan in force, on the cited page | a program (word-for-word match) |
| `recovered` | the program re-copied the authority's own text at that spot, from the label before it to the next label | a program (copy + word-for-word match) |
| `unconfirmed` | neither: show the heading, "We couldn't confirm the council's wording", the link and the reason. Its numbers are never used in a calculation | a program, or the AI reviewer's refusal |

Only a program can make a rule `exact` or `recovered`. The AI reviewer can only refuse.

## What the AI reviewer must refuse (send back for re-copy, or mark `unconfirmed` / `not_a_control`)
1. **Not a control** — a page header or footer, a contents line, a figure caption or map label, the
   council's address or contact details, a document title, page furniture.
2. **Not usable** — a fragment cut off mid-sentence; a heading with no control under it; a whole section
   or chapter stored as one "rule" (several separate controls run together).
3. **Not this rule** — the quote is about a different topic, area, zone or development type from the
   heading or label it is filed under.
4. **Not checkable** — a number we show or compute with that does not appear inside the quote, or a
   quote whose meaning depends on a table or figure that is not included.
5. **Not the authority's words** — paraphrase, summary or invented wording presented as a quote.

Background and explanatory text (objectives, introductions, character statements) is the authority's own
text and may be shown, labelled as such; it is not refused, only marked `not_a_control` when it is
filed as a control.

## What the AI reviewer must never do
- mark anything `exact` or `recovered`, or write or edit a quote;
- interpret the law or decide whether a control applies to a property;
- accept a quote because it "looks right" — only the word-for-word program check proves a quote.

## How the reviewer itself is checked
It is run on a fixed known-right and known-wrong set before any batch. Its refusal rate on known-right
rules and its pass rate on known-wrong rules are recorded with every run; a run that refuses good rules
or passes bad ones is not used.
