from __future__ import annotations

from pathlib import Path

import magic


def detect_mime(file_path: Path) -> str:
    mime = magic.Magic(mime=True)
    return mime.from_file(str(file_path))
