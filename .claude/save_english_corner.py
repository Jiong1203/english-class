#!/usr/bin/env python3
"""
Stop hook: Extract "English Corner" sections from session transcript
and append to a dated markdown file under english-class/src/.
Runs globally across all Claude projects.

Hook fires after every assistant turn, so this script only persists the
*latest* English Corner block on each invocation, keyed by the assistant
message's UUID — preventing the previous behavior of re-appending every
prior corner on each fire.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "src"
STATE_FILE = Path(__file__).resolve().parent / "save_state.json"


def find_transcript(session_id: str) -> Path | None:
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return None
    for transcript in projects_dir.glob(f"*/{session_id}.jsonl"):
        return transcript
    return None


def extract_latest_corner(transcript_path: Path) -> tuple[str, str] | None:
    """Return (uuid, corner_text) for the most recent assistant message that
    contains an English Corner block, or None.

    Stop hook fires after every assistant turn, so the latest English Corner
    in the transcript at hook-fire time is the one that just got generated.
    """
    latest: tuple[str, str] | None = None
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
                if not match:
                    continue
                uuid = entry.get("uuid", "")
                latest = (uuid, f"**English Corner:**{match.group(1)}".strip())

    return latest


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict) -> None:
    try:
        STATE_FILE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


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
    rebuild_entries()


def rebuild_entries() -> None:
    """Regenerate src/entries.json so the flashcard UI sees new cards.

    Imported lazily and stdout-silenced so a parser bug or stray print
    never blocks/contaminates the Stop hook.
    """
    import contextlib
    import io
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import build_entries  # noqa: WPS433 (intentional lazy import)
        with contextlib.redirect_stdout(io.StringIO()):
            build_entries.main()
    except Exception:
        pass


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

    result = extract_latest_corner(transcript)
    if not result:
        sys.exit(0)

    uuid, corner = result

    state = load_state()
    if state.get(session_id) == uuid:
        sys.exit(0)

    save_corners([corner], session_id)
    state[session_id] = uuid
    save_state(state)


if __name__ == "__main__":
    main()
