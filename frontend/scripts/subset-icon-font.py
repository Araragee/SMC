#!/usr/bin/env python3
"""Rebuild the subset of Material Symbols Outlined that this app actually uses.

The upstream font carries 4,309 icons in 1.1 MB. This app uses around 170 of
them, so almost all of that is paid for on first load and never drawn.

Run after adding or removing an icon:

    python3 -m venv /tmp/fontvenv
    /tmp/fontvenv/bin/pip install 'fonttools[woff]' brotli
    /tmp/fontvenv/bin/python scripts/subset-icon-font.py

The upstream font is downloaded rather than committed, so the repository keeps
only the subset. Nothing in the normal build depends on this script.

How the icon list is gathered
-----------------------------
Material Symbols are ligatures: the markup contains the icon's *name* as text
and the font substitutes a glyph. So the names live in the templates, but not
only as element text — 32 of them are bound at runtime from data, through
helpers like actionIcon(), fields like item.icon, and icon-left props.

Rather than trace every one of those paths, this harvests every lowercase
snake_case string literal in src/ and keeps the ones the font recognises as an
icon. A string that is not an icon name matches no ligature and is dropped; a
name we failed to collect would render as a blank box. The bias is deliberate.
"""
from __future__ import annotations

import io
import json
import re
import subprocess
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
OUT = SRC / "assets" / "fonts" / "material-symbols-outlined.woff2"
CSS_URL = (
    "https://fonts.googleapis.com/css2"
    "?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0.0.0"

LITERAL = re.compile(r"""['"]([a-z][a-z0-9_]{1,40})['"]""")
ICON_SPAN = re.compile(r"<span[^>]*material-symbols-outlined[^>]*>\s*([a-z0-9_]+)\s*</span", re.S)


def harvest_candidates() -> set[str]:
    found: set[str] = set()
    for path in [*SRC.rglob("*.vue"), *SRC.rglob("*.ts")]:
        text = path.read_text()
        found.update(LITERAL.findall(text))
        found.update(ICON_SPAN.findall(text))
    return {f for f in found if f}


def _curl(url: str) -> bytes:
    """curl rather than urllib: a bare venv often has no CA bundle wired up,
    and this script is run from a throwaway one."""
    out = subprocess.run(
        ["curl", "-fsSL", "-A", UA, url], capture_output=True, check=True
    )
    return out.stdout


def fetch_upstream() -> bytes:
    css = _curl(CSS_URL).decode()
    url = re.search(r"url\((https://[^)]+\.woff2)\)", css).group(1)
    print(f"upstream: {url}")
    return _curl(url)


def ligature_map(font: TTFont) -> dict[str, str]:
    """Icon name -> glyph, read from GSUB. The lookups are extension-wrapped."""
    rev = {glyph: code for code, glyph in font.getBestCmap().items()}
    out: dict[str, str] = {}
    for lookup in font["GSUB"].table.LookupList.Lookup:
        for st in lookup.SubTable:
            st = st.ExtSubTable if st.__class__.__name__ == "ExtensionSubst" else st
            for first, entries in (getattr(st, "ligatures", None) or {}).items():
                for lig in entries:
                    try:
                        name = "".join(chr(rev[g]) for g in [first, *lig.Component])
                    except KeyError:
                        continue
                    out[name] = lig.LigGlyph
    return out


def main() -> int:
    raw = fetch_upstream()
    font = TTFont(io.BytesIO(raw))
    ligs = ligature_map(font)
    print(f"upstream carries {len(ligs)} icons, {len(raw) / 1024:.0f} KB")

    candidates = harvest_candidates()
    used = sorted(n for n in candidates if n in ligs)
    print(f"harvested {len(candidates)} literals, {len(used)} of them are icons")
    if not used:
        print("refusing to write an empty subset", file=sys.stderr)
        return 1

    # Keep the icon glyphs, and the letters they are spelled with so the
    # ligature substitutions still have their inputs.
    keep = {ligs[n] for n in used}
    cmap = font.getBestCmap()
    keep.update(cmap[ord(ch)] for ch in set("".join(used)) if ord(ch) in cmap)

    options = subset.Options()
    # Keep every layout feature. These icons substitute under "rlig", not the
    # "liga" you would reach for — restricting the list to liga produced a
    # subset with the right glyphs, no substitutions, and every icon rendering
    # as its own name in plain text.
    options.layout_features = ["*"]
    # Without this the subsetter runs layout closure: it sees the letters we
    # kept, follows every ligature reachable from them, and pulls all 4,309
    # icons back in — a 1,016 KB "subset". We have already chosen the glyphs,
    # so rules that output anything else should be pruned, not followed.
    options.layout_closure = False
    options.flavor = "woff2"
    options.drop_tables = []            # keep fvar/gvar/STAT: FILL and wght are axes we use
    options.notdef_outline = True

    subsetter = subset.Subsetter(options=options)
    subsetter.populate(glyphs=sorted(keep))
    subsetter.subset(font)

    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    data = buf.getvalue()

    OUT.write_bytes(data)
    (OUT.parent / "icons-used.json").write_text(json.dumps(used, indent=0) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(data) / 1024:.0f} KB "
          f"({len(data) / len(raw):.1%} of upstream)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
