"""Download deliverables from the last session, avoiding locked filenames."""

from __future__ import annotations

import os
from pathlib import Path

from anthropic import Anthropic

ROOT = Path(__file__).parent
OUT = ROOT / "outputs"


def safe_path(filename: str) -> Path:
    """If outputs/<filename> is locked or exists, append '-live' before the extension."""
    candidate = OUT / filename
    if not candidate.exists():
        return candidate
    stem, ext = os.path.splitext(filename)
    return OUT / f"{stem}-live{ext}"


def main() -> None:
    session_id = (ROOT / ".last_session_id").read_text().strip()
    print(f"Session: {session_id}")
    client = Anthropic()
    files = client.beta.files.list(
        scope_id=session_id,
        betas=["managed-agents-2026-04-01"],
    )
    count = 0
    for f in files.data:
        target = safe_path(f.filename)
        print(f"  {f.filename}  ->  {target}")
        try:
            content = client.beta.files.download(f.id)
            content.write_to_file(str(target))
            count += 1
        except PermissionError as exc:
            # Fall back: write next to the locked file with a unique suffix
            target = OUT / f"{f.filename}.downloaded"
            content = client.beta.files.download(f.id)
            content.write_to_file(str(target))
            print(f"    (locked; wrote as {target.name})")
            count += 1
    print(f"\nDownloaded {count} file(s) to {OUT}/")


if __name__ == "__main__":
    main()
