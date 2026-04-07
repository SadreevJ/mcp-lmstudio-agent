from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass(slots=True)
class ProjectRecord:
    name: str
    path: Path
    archived: bool = False


@dataclass(slots=True)
class Registry:
    active_project: str | None = None
    projects: Dict[str, ProjectRecord] = field(default_factory=dict)


@dataclass(slots=True)
class ProjectIndex:
    project: str
    generated_at: str
    root: str
    file_count: int
    extension_stats: Dict[str, int]
    files: List[dict]
