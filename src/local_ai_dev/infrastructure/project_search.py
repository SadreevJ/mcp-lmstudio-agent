from __future__ import annotations

from pathlib import Path
from typing import Any

from local_ai_dev.infrastructure.indexer import ENTRYPOINT_FILES, SKIP_DIRS, TEXT_EXTENSIONS


def search_project(
    *,
    root: Path,
    mode: str,
    query: str = "",
    max_results: int = 50,
) -> list[dict[str, Any]]:
    if max_results <= 0:
        return []

    normalized_mode = mode.strip().lower()
    normalized_query = query.strip()

    if normalized_mode == "entrypoints":
        return _search_entrypoints(root=root, max_results=max_results)
    if normalized_mode == "file":
        return _search_file_names(root=root, query=normalized_query, max_results=max_results)
    if normalized_mode == "todo":
        return _search_by_line_pattern(root=root, patterns=("TODO", "FIXME"), max_results=max_results)
    if normalized_mode == "text":
        if not normalized_query:
            return []
        return _search_text(root=root, query=normalized_query, max_results=max_results)
    if normalized_mode == "defs":
        return _search_defs(root=root, query=normalized_query, max_results=max_results)
    return []


def _iter_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            out.append(path)
    return out


def _is_text(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def _rel(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _search_entrypoints(*, root: Path, max_results: int) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for path in _iter_files(root):
        rel = _rel(root, path)
        if path.name in ENTRYPOINT_FILES or rel.endswith("/main.py") or rel.endswith("/__main__.py"):
            found.append({"path": rel, "kind": "entrypoint"})
            if len(found) >= max_results:
                break
    return found


def _search_file_names(*, root: Path, query: str, max_results: int) -> list[dict[str, Any]]:
    needle = query.lower()
    found: list[dict[str, Any]] = []
    for path in _iter_files(root):
        rel = _rel(root, path)
        if not needle or needle in path.name.lower() or needle in rel.lower():
            found.append({"path": rel, "kind": "file"})
            if len(found) >= max_results:
                break
    return found


def _search_text(*, root: Path, query: str, max_results: int) -> list[dict[str, Any]]:
    needle = query.lower()
    found: list[dict[str, Any]] = []
    for path in _iter_files(root):
        if not _is_text(path):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, start=1):
            if needle in line.lower():
                found.append({"path": _rel(root, path), "line": i, "text": line.strip(), "kind": "text"})
                if len(found) >= max_results:
                    return found
    return found


def _search_by_line_pattern(*, root: Path, patterns: tuple[str, ...], max_results: int) -> list[dict[str, Any]]:
    upper_patterns = tuple(p.upper() for p in patterns)
    found: list[dict[str, Any]] = []
    for path in _iter_files(root):
        if not _is_text(path):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, start=1):
            hay = line.upper()
            if any(p in hay for p in upper_patterns):
                found.append({"path": _rel(root, path), "line": i, "text": line.strip(), "kind": "todo"})
                if len(found) >= max_results:
                    return found
    return found


def _search_defs(*, root: Path, query: str, max_results: int) -> list[dict[str, Any]]:
    needle = query.lower()
    found: list[dict[str, Any]] = []
    markers = ("def ", "class ", "function ", "const ", "let ", "var ")
    allowed_ext = {".py", ".js", ".ts", ".tsx", ".cpp", ".c", ".h", ".hpp"}
    for path in _iter_files(root):
        if path.suffix.lower() not in allowed_ext:
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not any(stripped.startswith(m) for m in markers):
                continue
            if needle and needle not in stripped.lower():
                continue
            found.append({"path": _rel(root, path), "line": i, "text": stripped, "kind": "definition"})
            if len(found) >= max_results:
                return found
    return found
