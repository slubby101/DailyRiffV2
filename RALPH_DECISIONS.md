# RALPH decisions log

Cross-iteration memory for the AFK Ralph loop. One terse entry per iteration.
**Append new entries at the bottom of this file.**

GitHub issue state already tells Ralph *what* was done. This file captures the
*why* — non-obvious tradeoffs, dependency choices, environment quirks, and
follow-up hooks — so later iterations don't re-litigate decisions that past-Ralph
already thought through.

## Format

```
### <YYYY-MM-DD HH:MM UTC> / iteration #<N> of PRD #<PRD> / closed #<sub-issue>
- **Decision:** <one or two lines; what was chosen and why, especially non-obvious tradeoffs>
- **Blocker:** <one line if hit and worked around, otherwise omit>
- **Next:** <one line pointer to a follow-up if this work unblocks something specific>
```

Keep it terse. One to three bullets, single lines. This file is Ralph's working
memory, not a changelog — the PR descriptions and commit messages are the
changelog.

## Rules for Ralph

- Read this file at the start of every iteration before picking a sub-issue.
- Append a new entry **after** closing the sub-issue but **before** emitting any
  `<promise>` sentinel, as part of the same git commit as the sub-issue work.
- Never rewrite past entries. Append-only.
- If this file is missing, create it with the header above and add the first
  entry.

---

## Entries

<!-- Ralph appends new entries below this marker. Newest at the bottom. -->
