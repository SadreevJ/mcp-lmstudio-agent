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
    ".js",
    ".ts",
    ".tsx",
    ".css",
    ".html",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".bat",
    ".sh",
    ".cmake",
}

ENTRYPOINT_FILES = {
    "README",
    "README.md",
    "README.txt",
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "CMakeLists.txt",
    ".env.example",
    "Dockerfile",
    "Makefile",
    "main.py",
    "app.py",
    "__main__.py",
    "index.html",
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
        stat = path.stat()
        rel_text = str(rel).replace("\\", "/")
        is_text = _is_text_file(path)
        meta = {
            "path": rel_text,
            "name": path.name,
            "extension": ext,
            "size": stat.st_size,
            "mtime_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "is_text": is_text,
            "is_entrypoint": _is_entrypoint(rel_text, path.name),
            "importance": _importance_label(rel_text, path.name),
            "priority_score": _priority_score(rel_text, path.name, ext),
        }
        if is_text:
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


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def _is_entrypoint(rel_path: str, file_name: str) -> bool:
    root_name = file_name
    if root_name in ENTRYPOINT_FILES:
        return True
    normalized = rel_path.lower()
    return normalized.endswith("/main.py") or normalized.endswith("/__main__.py")


def _importance_label(rel_path: str, file_name: str) -> str:
    if _is_entrypoint(rel_path, file_name):
        return "high"
    parts = Path(rel_path).parts
    if any(part in {"src", "app", "cmd"} for part in parts):
        return "medium"
    return "low"


def _priority_score(rel_path: str, file_name: str, extension: str) -> int:
    score = 100
    lower_name = file_name.lower()
    lower_path = rel_path.lower()
    if _is_entrypoint(rel_path, file_name):
        score -= 80
    if extension in {".py", ".js", ".ts", ".tsx", ".cpp", ".c", ".go", ".rs"}:
        score -= 15
    if "/src/" in f"/{lower_path}" or lower_path.startswith("src/"):
        score -= 10
    if lower_name.startswith("test_") or "/tests/" in f"/{lower_path}":
        score += 15
    return max(score, 0)
