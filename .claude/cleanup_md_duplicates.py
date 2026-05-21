#!/usr/bin/env python3
"""
One-shot cleanup for legacy duplicate English Corner blocks in src/English_*.md.

Background: prior to the UUID-keyed Stop hook, every hook fire re-appended the
entire transcript's corners to the daily file. This script normalizes those
files by SHA1-deduping bodies and rewriting in canonical form, preserving the
session header (`> Session: <hash> · HH:MM:SS`) from each body's *first*
occurrence.

Safe to re-run: idempotent. Run from anywhere; paths are derived from
the script's location.
"""

import hashlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
CORNER_MARKER = "**English Corner:**"
SESSION_RE = re.compile(r"> Session: `[^`]+` · [\d:]+")


def parse_file(text: str, fallback_date: str) -> tuple[str, list[tuple[str, str]]]:
    """Return (date_header_line, [(session_header, body), ...])."""
    header_match = re.match(r"(# English Corner — [\d-]+)", text)
    if header_match:
        date_header = header_match.group(1)
    else:
        d = fallback_date
        date_header = f"# English Corner — {d[:4]}-{d[4:6]}-{d[6:]}"

    parts = text.split(CORNER_MARKER)
    entries: list[tuple[str, str]] = []
    last_session_header: str = ""

    for i, part in enumerate(parts):
        if i == 0:
            matches = list(SESSION_RE.finditer(part))
            if matches:
                last_session_header = matches[-1].group(0)
            continue

        cut = len(part)
        for sep in ("\n---\n", "\n> Session:"):
            idx = part.find(sep)
            if idx != -1 and idx < cut:
                cut = idx

        body = part[:cut].strip()
        if body:
            entries.append((last_session_header, body))

        remaining = part[cut:]
        matches = list(SESSION_RE.finditer(remaining))
        if matches:
            last_session_header = matches[-1].group(0)

    return date_header, entries


def dedup(entries: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for header, body in entries:
        digest = hashlib.sha1(body.encode("utf-8")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        unique.append((header, body))
    return unique


def reformat(date_header: str, entries: list[tuple[str, str]]) -> str:
    out: list[str] = [date_header, ""]
    for i, (header, body) in enumerate(entries):
        if i > 0:
            out.append("---")
            out.append("")
        if header:
            out.append(header)
            out.append("")
        out.append(CORNER_MARKER)
        out.append("")
        out.append(body)
        out.append("")
    return "\n".join(out)


def main(dry_run: bool = False) -> None:
    total_before = 0
    total_after = 0
    bytes_before = 0
    bytes_after = 0
    touched = 0

    for path in sorted(SRC.glob("English_*.md")):
        original = path.read_text(encoding="utf-8")
        fallback = path.stem.replace("English_", "")
        date_header, entries = parse_file(original, fallback)
        unique = dedup(entries)

        before_n, after_n = len(entries), len(unique)
        before_b, after_b = len(original.encode("utf-8")), 0

        total_before += before_n
        bytes_before += before_b

        if after_n == before_n:
            after_b = before_b
            total_after += after_n
            bytes_after += after_b
            print(f"{path.name}: {before_n} entries · {before_b // 1024} KB · skip (no dupes)")
            continue

        new_text = reformat(date_header, unique)
        after_b = len(new_text.encode("utf-8"))
        total_after += after_n
        bytes_after += after_b
        touched += 1

        if dry_run:
            print(f"{path.name}: {before_n} → {after_n} entries · {before_b // 1024} → {after_b // 1024} KB · DRY-RUN")
        else:
            path.write_text(new_text, encoding="utf-8")
            print(f"{path.name}: {before_n} → {after_n} entries · {before_b // 1024} → {after_b // 1024} KB")

    print()
    print(f"Files touched: {touched}")
    print(f"Entries:  {total_before} → {total_after}  ({total_before - total_after} dupes removed)")
    print(f"Size:     {bytes_before // 1024} KB → {bytes_after // 1024} KB  ({(bytes_before - bytes_after) // 1024} KB saved)")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
