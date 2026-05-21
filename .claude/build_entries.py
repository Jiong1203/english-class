#!/usr/bin/env python3
"""
Batch-parse src/English_*.md into src/entries.json for the flashcard mode.

One **English Corner:** block == one flashcard. Body is hashed for dedup
(same block written on multiple days collapses to a single entry, keyed by
earliest occurrence). Front is heuristically extracted; body keeps the
full markdown so the review UI can render it as-is.
"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
OUT = SRC / "entries.json"

CORNER_MARKER = "**English Corner:**"

FRONT_PREFIXES = (
    "你的中文訊息",
    "你的中文",
    "你的英文",
    "你的描述",
    "你的寫法",
    "你的指令",
    "你的原句",
    "你寫的",
    "你說",
    "剛才你說",
)


def split_blocks(text: str, date: str) -> list[tuple[str, str]]:
    """Return [(date, body)] for each English Corner block in a daily file.

    Note: cut is found in the un-stripped slice. Pre-stripping would remove
    the trailing newline of a "\\n---\\n" separator, hiding it from .find()
    and leaving a "\\n\\n---" remnant inside the body — that was a latent bug
    that inflated entries.json with phantom hash variants.
    """
    parts = text.split(CORNER_MARKER)
    blocks = []
    # parts[0] is the file header before the first marker — discard it.
    for raw in parts[1:]:
        cut = len(raw)
        for sep in ("\n---\n", "\n> Session:"):
            idx = raw.find(sep)
            if idx != -1 and idx < cut:
                cut = idx
        body = raw[:cut].strip()
        if body:
            blocks.append((date, body))
    return blocks


def extract_front(body: str) -> str:
    """Pull a short prompt line from the block to show on the card front."""
    lines = [l.strip() for l in body.splitlines() if l.strip()]

    for line in lines:
        clean = line.lstrip("*_ -#>").strip()
        for prefix in FRONT_PREFIXES:
            if clean.startswith(prefix):
                return _truncate(clean, 140)

    # Fallback: first quoted English snippet
    m = re.search(r'\*"([^"]{4,160})"\*', body)
    if m:
        return f'"{m.group(1)}"'
    m = re.search(r'"([^"]{4,160})"', body)
    if m:
        return f'"{m.group(1)}"'

    # Last resort: first content line
    for line in lines:
        if line.startswith("|") or line.startswith(">"):
            continue
        return _truncate(line.lstrip("*_ -#>").strip(), 140)
    return "(empty)"


def _truncate(s: str, n: int) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def infer_tags(body: str) -> list[str]:
    tags = []
    low = body.lower()
    if "完全正確" in body or "沒有需要修正" in body or "natural" in low:
        tags.append("praise")
    if "文法" in body or "grammar" in low or "tense" in low or "被動" in body:
        tags.append("grammar")
    if "詞彙" in body or "vocab" in low or "vocabulary" in low:
        tags.append("vocab")
    if "nuance" in low:
        tags.append("nuance")
    if "|" in body and "---" in body:
        tags.append("comparison")
    if not tags:
        tags.append("note")
    return tags


def main() -> None:
    entries: dict[str, dict] = {}

    for path in sorted(SRC.glob("English_*.md")):
        date = path.stem.replace("English_", "")
        text = path.read_text(encoding="utf-8")
        for d, body in split_blocks(text, date):
            digest = hashlib.sha1(body.encode("utf-8")).hexdigest()[:12]
            if digest in entries:
                # Keep earliest date — files are processed in sorted order,
                # so the existing record already has the earliest date.
                continue
            entries[digest] = {
                "id": digest,
                "date": d,
                "front": extract_front(body),
                "body": body,
                "tags": infer_tags(body),
            }

    payload = {
        "entries": sorted(
            entries.values(),
            key=lambda e: (e["date"], e["id"]),
            reverse=True,
        )
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(payload['entries'])} entries to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
