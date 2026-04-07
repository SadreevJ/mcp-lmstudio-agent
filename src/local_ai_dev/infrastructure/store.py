from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from local_ai_dev.domain.models import ProjectRecord, Registry


class RegistryStore:
    def __init__(self, state_path: Path) -> None:
        self._state_path = state_path

    def load(self) -> Registry:
        if not self._state_path.exists():
            return Registry(active_project=None, projects={})
        raw = json.loads(self._state_path.read_text(encoding="utf-8"))
        projects = {
            name: ProjectRecord(name=name, path=Path(item["path"]), archived=item.get("archived", False))
            for name, item in raw.get("projects", {}).items()
        }
        return Registry(active_project=raw.get("active_project"), projects=projects)

    def save(self, registry: Registry) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        raw = {
            "active_project": registry.active_project,
            "projects": {
                name: {"path": str(record.path), "archived": record.archived}
                for name, record in registry.projects.items()
            },
        }
        self._state_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_dataclass_json(path: Path, data: Any) -> None:
    write_json(path, asdict(data))
