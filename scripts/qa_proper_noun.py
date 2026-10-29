#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA Check 3 — proper-noun English annotation (deterministic, idempotent).

Scans the CHINESE segment (before the standalone `===EN===` line) of each
given article markdown file. For every entry in data/glossary.json (cn -> en),
if the Chinese word appears and its FIRST occurrence is NOT already followed by
an English gloss, insert `（en）` right after the word's first occurrence.

Idempotent rules:
  * Skip a term if its first occurrence is immediately followed by `（`/`(` —
    the author already provided a disambiguation (even if Chinese-only, to
    avoid producing `（A）（B）` double parentheses).
  * Skip a term if its first occurrence is immediately followed (after an
    optional single space) by a Latin word — i.e. citation style such as
    `联合早报 Lianhe Zaobao` already carries English inline.
  * Protect existing parenthetical spans and inserted spans so shorter
    glossary substrings (e.g. 印尼 inside 印度尼西亚) are not double-annotated.

Usage:
  python3 qa_proper_noun.py            # dry run, prints planned diffs
  python3 qa_proper_noun.py --apply    # writes changes back to the .md files
"""
import json
import re
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LATIN = re.compile(r"[A-Za-z]")
PAREN = re.compile(r"[（(][^（）()]*[）)]")

# Longer Chinese proper nouns that contain a glossary term as a prefix. We must
# NOT fragment these by inserting a gloss inside them (e.g. 北京 -> 北京（Beijing）
# 语言大学出版社 would break the publisher name). Matches that fall inside any of
# these compounds are skipped.
COMPOUND_PROTECT = [
    "北京语言大学出版社",
    "北京语言大学",
    # Suffix containment: the glossary term is a *tail* of a longer proper noun
    # and must NOT be fragmented. e.g. 马尼拉 inside 大马尼拉 (Metro Manila).
    "大马尼拉",
    # Prefix containment: city name followed by a facility modifier; the city is
    # only glossed when it stands alone, not inside "吉隆坡机场" etc.
    "吉隆坡机场",
    "吉隆坡国际机场",
]


def split_segments(text):
    """Return (zh_segment, en_segment) split on a standalone `===EN===` line."""
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if ln.strip() == "===EN===":
            # zh = everything before the delimiter; en = everything after it
            # (the delimiter line itself is excluded so rejoin never duplicates it)
            return "\n".join(lines[:i]), "\n".join(lines[i + 1:])
    return text, ""


def line_contains(idx, zh, needle):
    """Return True if the line containing position idx contains needle
    (used to skip the `*话题参考：*` / `*Topic reference:*` citation line,
    whose source names are already bilingual and must not be re-glossed)."""
    ls = zh.rfind("\n", 0, idx) + 1
    le = zh.find("\n", idx)
    if le == -1:
        le = len(zh)
    return needle in zh[ls:le]


def annotate_zh(zh, glossary):
    entries = sorted(glossary.items(), key=lambda kv: len(kv[0]), reverse=True)
    # Protected spans (original coordinates): existing parentheticals.
    protected = [(m.start(), m.end()) for m in PAREN.finditer(zh)]
    insertions = []  # (pos, cn, en)

    for cn, en in entries:
        idx = zh.find(cn)
        while idx != -1:
            overlap = any(
                p0 <= idx < p1
                or p0 < idx + len(cn) <= p1
                or (idx <= p0 and idx + len(cn) >= p1)
                for p0, p1 in protected
            )
            # Skip occurrences inside the topic-reference citation line.
            if not overlap and line_contains(idx, zh, "话题参考"):
                overlap = True
            # Skip a match that is part of a longer compound proper noun, whether
            # the glossary term is a *prefix* (e.g. 北京 inside 北京语言大学出版社)
            # or a *suffix* (e.g. 马尼拉 inside 大马尼拉). Fragmenting these would
            # corrupt the compound's reading. When matched, advance to the next
            # occurrence instead of abandoning the term entirely.
            _skip = False
            for comp in COMPOUND_PROTECT:
                if cn not in comp:
                    continue
                cpos = comp.index(cn)
                start = idx - cpos
                if start >= 0 and zh[start:start + len(comp)] == comp:
                    _skip = True
                    break
            if overlap or _skip:
                idx = zh.find(cn, idx + 1)
                continue
            break
        if idx == -1:
            continue
        after = zh[idx + len(cn):]
        # Already carries an English gloss, possibly separated from the term by a
        # closing quote/bracket such as 》 or " (e.g. 《日经亚洲》(Nikkei Asia)).
        # Skip so we stay idempotent and never produce double parentheses.
        if re.match(r"[^A-Za-z（）()]{0,12}[（(][^（）()]*[A-Za-z][^（）()]*[）)]", after):
            continue
        nxt = after[0] if after else ""
        # Already annotated with a parenthesis right after?
        if nxt in ("（", "("):
            # protect the whole paren span
            close = after.find("）")
            close2 = after.find(")")
            ends = [c for c in (close, close2) if c != -1]
            cend = (min(ends) + 1) if ends else 0
            protected.append((idx, idx + len(cn) + cend))
            continue
        # Citation style: optional space then a Latin word?
        m = re.match(r"\s*[A-Za-z]", after)
        if m:
            continue
        insertions.append((idx, cn, en))

    insertions.sort(reverse=True)  # apply right-to-left to avoid drift
    out = zh
    applied = []
    for pos, cn, en in insertions:
        ins = pos + len(cn)
        # If the term is immediately followed by a CJK closing bracket
        # (》 or 」), place the gloss AFTER it so it is not trapped inside
        # a book-title span, e.g. 《日经亚洲》（Nikkei Asia） rather than
        # 《日经亚洲（Nikkei Asia）》.
        if ins < len(out) and out[ins] in ("》", "」"):
            ins += 1
        out = out[:ins] + f"（{en}）" + out[ins:]
        applied.append((cn, en, pos))
    return out, applied


def main():
    apply = "--apply" in sys.argv
    with open(os.path.join(ROOT, "data", "glossary.json"), encoding="utf-8") as f:
        glossary = json.load(f)

    slugs = sys.argv[1:] if not apply else [a for a in sys.argv[1:] if a != "--apply"]
    if not slugs:
        slugs = [
            "malaysia-opposition-pn-deregistered-2026",
            "malaysia-foreigners-scams-arrests-2026",
            "indonesia-stocks-msci-standalone-downgrade-2026",
            "qimen-ancha-tea-nanyang-revival-2026",
        ]

    total_changes = 0
    for slug in slugs:
        path = os.path.join(ROOT, "articles", f"{slug}.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        zh, en = split_segments(text)
        new_zh, applied = annotate_zh(zh, glossary)
        if not applied:
            print(f"[{slug}] no changes")
            continue
        total_changes += len(applied)
        print(f"[{slug}] {len(applied)} insertion(s):")
        for cn, en_, pos in applied:
            snippet = zh[max(0, pos - 8):pos + len(cn) + 12]
            print(f"   + {cn} -> （{en_}）  around: …{snippet}…")
        if apply:
            new_text = new_zh + "\n===EN===\n" + en if en else new_zh
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_text)
            print(f"   -> written")
    print(f"\nTOTAL insertions across files: {total_changes}")
    if not apply:
        print("(dry run — pass --apply to write)")


if __name__ == "__main__":
    main()
