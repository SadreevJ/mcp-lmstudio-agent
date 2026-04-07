from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from local_ai_dev.application.briefing import BriefMeta, build_brief_markdown, load_index_json
from local_ai_dev.domain.models import ProjectRecord, Registry
from local_ai_dev.infrastructure.indexer import build_project_index
from local_ai_dev.infrastructure.mcp_config import patch_lmstudio_filesystem_plugin, write_mcp_json
from local_ai_dev.infrastructure.paths import AppPaths
from local_ai_dev.infrastructure.project_search import search_project
from local_ai_dev.infrastructure.store import RegistryStore, write_dataclass_json

logger = logging.getLogger(__name__)


class ProjectService:
    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths
        self.registry_store = RegistryStore(paths.state)

    def bootstrap(self) -> Registry:
        self.paths.workspace.mkdir(parents=True, exist_ok=True)
        self.paths.context.mkdir(parents=True, exist_ok=True)
        self.paths.projects_memory.mkdir(parents=True, exist_ok=True)
        self.paths.logs.mkdir(parents=True, exist_ok=True)
        (self.paths.memory / "sessions").mkdir(parents=True, exist_ok=True)
        self.paths.rules.mkdir(parents=True, exist_ok=True)

        registry = self.registry_store.load()
        self._sync_workspace(registry)
        if not registry.projects:
            for default in ("project1", "project2", "project3"):
                (self.paths.workspace / default).mkdir(parents=True, exist_ok=True)
                registry.projects[default] = ProjectRecord(name=default, path=self.paths.workspace / default)
            registry.active_project = "project1"
        elif registry.active_project not in registry.projects:
            registry.active_project = sorted(registry.projects.keys())[0]
        self.registry_store.save(registry)
        logger.info("Bootstrap finished. projects=%s active=%s", len(registry.projects), registry.active_project)
        self._try_sync_mcp()
        return registry

    def get_registry(self) -> Registry:
        registry = self.registry_store.load()
        self._sync_workspace(registry)
        self.registry_store.save(registry)
        return registry

    def switch_project(self, name: str) -> Registry:
        registry = self.get_registry()
        if name not in registry.projects:
            raise ValueError(f"Проект '{name}' не зарегистрирован.")
        record = registry.projects[name]
        if not record.path.exists():
            raise ValueError(f"Путь проекта '{name}' не существует: {record.path}")
        registry.active_project = name
        self.registry_store.save(registry)
        logger.info("Switched active project to '%s'.", name)
        self._try_sync_mcp()
        return registry

    def add_project(self, name: str, path: Path | None = None) -> Registry:
        registry = self.get_registry()
        target = path if path is not None else (self.paths.workspace / name)
        target.mkdir(parents=True, exist_ok=True)
        registry.projects[name] = ProjectRecord(name=name, path=target)
        if registry.active_project is None:
            registry.active_project = name
        self.registry_store.save(registry)
        self.ensure_project_memory(name)
        logger.info("Project '%s' added at %s.", name, target)
        self._try_sync_mcp()
        return registry

    def sync_mcp_config(self) -> Path:
        registry = self.get_registry()
        if registry.active_project is None:
            raise ValueError("Нет активного проекта. Укажите через switch-project или add-project.")
        rec = registry.projects.get(registry.active_project)
        if rec is None:
            raise ValueError(f"Активный проект '{registry.active_project}' не найден в реестре.")
        project_root = rec.path.resolve()
        if not project_root.is_dir():
            raise ValueError(f"Папка проекта не существует: {project_root}")
        project_name = registry.active_project
        assert project_name is not None
        self.ensure_project_memory(project_name)
        briefs_root = self.paths.context / "briefs" / project_name
        briefs_root.mkdir(parents=True, exist_ok=True)
        extra_fs = [self.paths.projects_memory / project_name, briefs_root]
        repo_root = self.paths.root.resolve()
        mcp_path = repo_root / "config" / "mcp" / "mcp.json"
        write_mcp_json(mcp_path, project_root, repo_root, extra_allowed=extra_fs)
        patch_lmstudio_filesystem_plugin(project_root, repo_root, extra_allowed=extra_fs)
        logger.info(
            "MCP: filesystem разрешено — код: %s; память/брифы: %s",
            project_root,
            extra_fs,
        )
        return mcp_path

    def _try_sync_mcp(self) -> None:
        try:
            self.sync_mcp_config()
        except Exception as exc:
            logger.warning("MCP конфиг не обновлён: %s", exc)

    def index_project(self, name: str | None = None, max_files: int = 1500) -> Path:
        registry = self.get_registry()
        active = name or registry.active_project
        if active is None:
            raise ValueError("Нет активного проекта.")
        if active not in registry.projects:
            raise ValueError(f"Проект '{active}' не найден в реестре.")
        project_path = registry.projects[active].path
        if not project_path.exists():
            raise ValueError(f"Папка проекта '{active}' удалена: {project_path}")
        self.ensure_project_memory(active)
        index = build_project_index(active, project_path, max_files=max_files)
        index_path = self.paths.projects_memory / active / "index.json"
        write_dataclass_json(index_path, index)
        self._write_summary(active, index_path)
        self._append_session_note(active, f"Индекс пересобран: {index.file_count} файлов.")
        self._append_worklog(active, f"Обновлён индекс проекта: {index.file_count} файлов.")
        logger.info("Indexed project '%s'. files=%s", active, index.file_count)
        return index_path

    def rebuild_context(self, name: str | None = None, max_files: int = 1500) -> Path:
        return self.index_project(name=name, max_files=max_files)

    def search_in_project(
        self,
        *,
        name: str | None = None,
        mode: str = "file",
        query: str = "",
        max_results: int = 50,
    ) -> tuple[str, list[dict[str, object]]]:
        registry = self.get_registry()
        active = name or registry.active_project
        if active is None:
            raise ValueError("Нет активного проекта.")
        if active not in registry.projects:
            raise ValueError(f"Проект '{active}' не найден в реестре.")
        project_path = registry.projects[active].path
        if not project_path.exists():
            raise ValueError(f"Папка проекта '{active}' удалена: {project_path}")
        results = search_project(
            root=project_path,
            mode=mode,
            query=query,
            max_results=max_results,
        )
        return active, results

    def prepare_chat_context(
        self,
        *,
        name: str | None = None,
        max_files: int = 1500,
        format_name: str = "short",
    ) -> tuple[str, Path]:
        registry = self.get_registry()
        project = name or registry.active_project
        if project is None:
            raise ValueError("Нет активного проекта.")
        if project not in registry.projects:
            raise ValueError(f"Проект '{project}' не найден в реестре.")
        record = registry.projects[project]
        workspace_root = self.paths.workspace.resolve()
        project_path = record.path.resolve()
        if project_path.parent != workspace_root:
            raise ValueError(
                f"Проект '{project}' вне workspace и недоступен для prepare-chat: {project_path}. "
                "Выберите директорию из workspace."
            )
        if project != registry.active_project:
            self.switch_project(project)
        self.index_project(name=project, max_files=max_files)
        self.sync_mcp_config()
        brief_path, _ = self.build_brief(name=project, format_name=format_name, handoff=False, write_history_copy=True)
        index_payload = load_index_json(self.paths.projects_memory / project / "index.json") or {}
        indexed_count = int(index_payload.get("file_count", 0))
        self._append_worklog(
            project,
            f"Подготовлен новый чат: active={project}, indexed_files={indexed_count}, brief={brief_path.name}, format={format_name}.",
        )
        return project, brief_path

    def build_brief(
        self,
        name: str | None = None,
        format_name: str = "short",
        handoff: bool = False,
        write_history_copy: bool = True,
    ) -> tuple[Path, BriefMeta]:
        registry = self.get_registry()
        project = name or registry.active_project
        if project is None:
            raise ValueError("Нет активного проекта.")
        if project not in registry.projects:
            raise ValueError(f"Проект '{project}' не найден в реестре.")
        self.ensure_project_memory(project)
        index_path = self.paths.projects_memory / project / "index.json"
        payload = load_index_json(index_path)
        memory_dir = self.paths.projects_memory / project
        md, meta = build_brief_markdown(
            paths=self.paths,
            project=project,
            registry_active=registry.active_project,
            index_payload=payload,
            memory_dir=memory_dir,
            format_name=format_name,
            handoff=handoff,
        )
        out_dir = self.paths.context / "briefs" / project
        out_dir.mkdir(parents=True, exist_ok=True)
        latest = out_dir / "latest.md"
        latest.write_text(md, encoding="utf-8")
        if write_history_copy:
            stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
            hist = out_dir / f"{stamp}.md"
            hist.write_text(md, encoding="utf-8")
        meta_path = out_dir / "brief-meta.json"
        meta_path.write_text(
            json.dumps(meta.to_json_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info("Brief written for '%s' -> %s", project, latest)
        return latest, meta

    def ensure_project_memory(self, name: str) -> None:
        project_dir = self.paths.projects_memory / name
        project_dir.mkdir(parents=True, exist_ok=True)
        for file_name, template in (
            ("summary.md", f"# Summary: {name}\n\nКраткое описание архитектуры и текущего состояния.\n"),
            ("decision-log.md", f"# Decision Log: {name}\n\n"),
            ("known-issues.md", f"# Known Issues: {name}\n\n"),
            ("notes.md", f"# Notes: {name}\n\n"),
            (
                "architecture.md",
                f"# Architecture: {name}\n\n"
                "Ключевые компоненты и их роли:\n"
                "- \n\n"
                "Границы слоёв (domain/application/infrastructure):\n"
                "- \n",
            ),
            (
                "run-commands.md",
                f"# Run Commands: {name}\n\n"
                "Основные команды проекта:\n"
                "- запуск: \n"
                "- тесты: \n"
                "- проверка/линт: \n",
            ),
            ("worklog.md", f"# Worklog: {name}\n\n"),
        ):
            target = project_dir / file_name
            if not target.exists():
                target.write_text(template, encoding="utf-8")

    def append_decision(self, text: str, project: str | None = None) -> Path:
        registry = self.get_registry()
        name = project or registry.active_project
        if name is None:
            raise ValueError("Нет активного проекта для decision log.")
        self.ensure_project_memory(name)
        target = self.paths.projects_memory / name / "decision-log.md"
        stamp = datetime.now(tz=timezone.utc).isoformat()
        with target.open("a", encoding="utf-8") as fh:
            fh.write(f"- {stamp} {text}\n")
        logger.info("Decision appended for project '%s'.", name)
        return target

    def _sync_workspace(self, registry: Registry) -> None:
        self.paths.workspace.mkdir(parents=True, exist_ok=True)
        live_dirs = [p for p in self.paths.workspace.iterdir() if p.is_dir()]
        for project_dir in live_dirs:
            if project_dir.name not in registry.projects:
                registry.projects[project_dir.name] = ProjectRecord(name=project_dir.name, path=project_dir)
        missing = [name for name, rec in registry.projects.items() if not rec.path.exists()]
        for name in missing:
            del registry.projects[name]

    def _write_summary(self, project: str, index_path: Path) -> None:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        ext = payload.get("extension_stats", {})
        files = list(payload.get("files") or [])
        entrypoints_count = sum(1 for item in files if item.get("is_entrypoint") is True)
        text_count = sum(1 for item in files if item.get("is_text") is True)
        summary = [
            f"# Summary: {project}",
            "",
            f"- Обновлено: {payload.get('generated_at', '<unknown>')}",
            f"- Корень проекта: `{payload.get('root', '')}`",
            f"- Проиндексировано файлов: {payload.get('file_count', 0)}",
            f"- Текстовых файлов: {text_count}",
            f"- Entrypoints: {entrypoints_count}",
            "",
            "## Распределение по расширениям",
        ]
        for key, value in sorted(ext.items(), key=lambda item: item[1], reverse=True)[:20]:
            summary.append(f"- `{key}`: {value}")
        (self.paths.projects_memory / project / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    def _append_session_note(self, project: str, text: str) -> None:
        sessions_dir = self.paths.memory / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        session_file = sessions_dir / f"{datetime.now(tz=timezone.utc):%Y-%m-%d}.md"
        with session_file.open("a", encoding="utf-8") as fh:
            fh.write(f"- [{project}] {datetime.now(tz=timezone.utc).isoformat()} {text}\n")

    def _append_worklog(self, project: str, text: str) -> None:
        worklog = self.paths.projects_memory / project / "worklog.md"
        stamp = datetime.now(tz=timezone.utc).isoformat()
        with worklog.open("a", encoding="utf-8") as fh:
            fh.write(f"- {stamp} {text}\n")
