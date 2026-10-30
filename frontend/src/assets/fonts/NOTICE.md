# Bundled fonts

Served from this repository rather than fonts.googleapis.com. The runtime
fetch sent every visitor's IP to a third party — this app serves a school's
pupils, many of them minors — and made first paint depend on a network we do
not control.

Files are the exact `.woff2` payloads Google serves, with the unicode-range
splits preserved, so a browser still downloads only the subsets it needs.

## Plus Jakarta Sans

- Upstream: https://fonts.google.com/specimen/Plus+Jakarta+Sans (v12)
- Licence: SIL Open Font License 1.1 — https://openfontlicense.org
- Eight faces: normal and italic, each split latin / latin-ext / vietnamese /
  cyrillic-ext. A Latin-only page loads roughly 30 KB of this.

## Material Symbols Outlined

- Upstream: https://fonts.google.com/icons (v382)
- Licence: Apache License 2.0 — https://www.apache.org/licenses/LICENSE-2.0
- Subset to the icons this app uses: 36 KB, down from 1,112 KB.

The committed file is a subset, not the upstream font. Regenerate it with
`scripts/subset-icon-font.py` after adding or removing an icon; that script
downloads the upstream font, so only the subset lives here.
`icons-used.json` lists the names it was built for.

The names are collected by harvesting every lowercase snake_case string
literal in `src/` and keeping those the font recognises. That is wider than
it needs to be on purpose: 32 icons here are bound at runtime from data —
through helpers like `actionIcon()`, fields like `item.icon`, and `icon-left`
props — so tracing only the element text would have missed them, and a missed
name renders as a blank box.

Verify against the font binary, not a browser: a machine with Material
Symbols installed system-wide renders missing icons perfectly from the local
copy, so a gap is invisible locally and broken for everyone else. The script's
own output reports how many of the wanted names it retained.
