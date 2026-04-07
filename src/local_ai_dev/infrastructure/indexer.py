from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from local_ai_dev.domain.models import ProjectIndex

SKIP_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    ".venv",
    "node_modules",
    "build",
    "dist",
}

TEXT_EXTENSIONS = {
    ".py",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".txt",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".bat",
    ".sh",
    ".cmake",
}


def build_project_index(project: str, root: Path, max_files: int = 1500) -> ProjectIndex:
    files = []
    ext_counter: Counter[str] = Counter()
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        ext = path.suffix.lower() or "<no_ext>"
        ext_counter[ext] += 1
        meta = {
            "path": str(rel).replace("\\", "/"),
            "size": path.stat().st_size,
            "mtime_utc": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
        }
        if path.suffix.lower() in TEXT_EXTENSIONS:
            meta["preview"] = _safe_preview(path)
        files.append(meta)
        if len(files) >= max_files:
            break
    return ProjectIndex(
        project=project,
        generated_at=datetime.now(tz=timezone.utc).isoformat(),
        root=str(root),
        file_count=len(files),
        extension_stats=dict(ext_counter),
        files=files,
    )


def _safe_preview(path: Path, max_lines: int = 20, max_chars: int = 4000) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lines = content.splitlines()[:max_lines]
    text = "\n".join(lines)
    return text[:max_chars]
