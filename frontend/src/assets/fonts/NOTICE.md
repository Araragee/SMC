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
- One variable face, 1.1 MB, carrying the whole icon set.

That last file is the obvious thing to shrink. It is not shrunk here because
self-hosting on its own is size-neutral — the browser already fetched this
same 1.1 MB from Google — whereas subsetting is a behaviour change: 16 of the
icon names in this app are bound at runtime from data, so a subset built from
the 86 names visible in the templates would silently render some of them as
blank boxes. Worth doing with a generated allow-list, not by hand.
