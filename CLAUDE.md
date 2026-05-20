# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This repository is the storage + viewer for an **English Corner archive**. It does not generate content itself — content is produced by Claude in *other* conversations (anywhere on this machine) and harvested into this repo by a global Stop hook. The repo's job is two things:

1. Persist daily `**English Corner:**` excerpts as Markdown.
2. Serve them as a static site (deployable to GitHub Pages).

There is no build system, no package manager, no tests, and no backend.

## Common Commands

Local preview (the site fetches `src/*.md` and `src/index.json`, so opening `index.html` via `file://` will not work):

```bash
python -m http.server 3000
# or
npx serve .
```

Manually run the Stop hook script (rarely needed — it's normally invoked by Claude Code automatically). It reads a JSON payload on stdin containing `session_id`:

```bash
echo '{"session_id":"<session-id>"}' | python .claude/save_english_corner.py
```

## Architecture

The data flow has three pieces that live in **three different places**, and the project only owns the middle one:

```
[user's global ~/.claude/CLAUDE.md]   ──► defines the "English Corner" rule that makes Claude
                                          append a **English Corner:** block to every response

[user's global ~/.claude/settings.json] ──► Stop hook runs .claude/save_english_corner.py
                                            after every Claude Code session ends

[this repo / src/]                     ──► English_YYYYMMDD.md (append-only per day)
                                            index.json (date list, regenerated each run)
                                          index.html reads both via fetch
```

Implications when editing:

- **`.claude/save_english_corner.py` is gitignored** (see `.gitignore`). Treat it as a personal-machine script, but it is the only thing that writes to `src/`. Path constants inside it (`OUTPUT_DIR`) are derived relative to the script, so the repo must live where the user's global `settings.json` hook command expects it.
- The script reads from `~/.claude/projects/*/<session_id>.jsonl` (Claude Code's own transcript store) and greps for `**English Corner:**` blocks in assistant `text` content blocks. Changing the heading wording would break extraction in both the global `CLAUDE.md` rule *and* the regex in `save_english_corner.py` simultaneously.
- Daily files are **append-only** within a day: each new session adds a `---` separator and a `> Session: <hash8> · HH:MM:SS` header, then concatenates that session's corners. Do not assume one file == one session.
- `src/index.json` is regenerated from a glob of `English_*.md` filenames on every run — it is not authoritative; the `.md` files are. Hand-editing `index.json` will be overwritten the next time the hook fires.
- `index.html` is a single self-contained file: vanilla JS, no bundler, uses `marked` from a CDN and Google Fonts. Light/dark theme is persisted in `localStorage` under `ec-theme`. The mobile layout kicks in at `max-width: 768px`.

## Conventions Specific to This Repo

- Dates in filenames and `index.json` are `YYYYMMDD` (no separators). The frontend slices the string directly (`y = dateStr.slice(0,4)` etc.), so this format is load-bearing.
- The `**English Corner:**` literal — including the asterisks and trailing colon — is the extraction anchor. Don't rename it.
- Commit messages in this repo's history follow Conventional Commits (`docs:`, `feat:`, `fix:`, …) and do **not** include `Co-Authored-By` trailers. Match that style.
