#!/usr/bin/env python3
"""
Stop hook: Extract "English Corner" sections from session transcript
and append to a dated markdown file under english-class/src/.
Runs globally across all Claude projects.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path


OUTPUT_DIR = Path("D:/my/sideProject/english-class/src")


def find_transcript(session_id: str) -> Path | None:
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return None
    for transcript in projects_dir.glob(f"*/{session_id}.jsonl"):
        return transcript
    return None


def extract_corners(transcript_path: Path) -> list[str]:
    corners = []
    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("type") != "assistant":
                continue

            content = entry.get("message", {}).get("content", [])
            if not isinstance(content, list):
                continue

            for block in content:
                if not isinstance(block, dict) or block.get("type") != "text":
                    continue
                text = block.get("text", "")
                if "**English Corner:**" not in text:
                    continue
                match = re.search(r"\*\*English Corner:\*\*([\s\S]+)$", text)
                if match:
                    corners.append(f"**English Corner:**{match.group(1)}".strip())

    return corners


def save_corners(corners: list[str], session_id: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"English_{date_str}.md"

    is_new = not output_file.exists()
    timestamp = now.strftime("%H:%M:%S")

    with open(output_file, "a", encoding="utf-8") as f:
        if is_new:
            f.write(f"# English Corner — {now.strftime('%Y-%m-%d')}\n\n")
        else:
            f.write("\n---\n\n")

        f.write(f"> Session: `{session_id[:8]}` · {timestamp}\n\n")
        f.write("\n\n---\n\n".join(corners))
        f.write("\n")

    update_index()


def update_index() -> None:
    dates = sorted(
        [f.stem.replace("English_", "") for f in OUTPUT_DIR.glob("English_*.md")],
        reverse=True,
    )
    index_file = OUTPUT_DIR / "index.json"
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump({"dates": dates}, f, ensure_ascii=False, indent=2)


def main():
    try:
        hook_data = json.loads(sys.stdin.read())
        session_id = hook_data.get("session_id", "")
    except Exception:
        sys.exit(0)

    if not session_id:
        sys.exit(0)

    transcript = find_transcript(session_id)
    if not transcript:
        sys.exit(0)

    corners = extract_corners(transcript)
    if not corners:
        sys.exit(0)

    save_corners(corners, session_id)


if __name__ == "__main__":
    main()
