from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppPaths:
    root: Path
    workspace: Path
    data: Path
    context: Path
    memory: Path
    rules: Path
    state: Path
    projects_memory: Path
    logs: Path


def detect_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_paths() -> AppPaths:
    root = detect_root()
    data = root / "data"
    context = data / "context"
    memory = data / "memory"
    return AppPaths(
        root=root,
        workspace=root / "workspace",
        data=data,
        context=context,
        memory=memory,
        rules=root / "rules",
        state=context / "registry.json",
        projects_memory=memory / "projects",
        logs=data / "logs",
    )
