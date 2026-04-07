from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_ai_dev.infrastructure.paths import AppPaths

# Доля файлов с расширением относительно проиндексированного набора (эвристика стека).
_PY_SHARE_MIN = 0.08
_CPP_SHARE_MIN = 0.08


@dataclass(slots=True)
class BriefMeta:
    project: str
    registry_active: str | None
    rules_applied: list[str] = field(default_factory=list)
    index_generated_at: str | None = None
    brief_generated_at: str = ""
    stack_guess: list[str] = field(default_factory=list)
    format: str = "short"
    handoff: bool = False
    index_file_count: int = 0

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "registry_active": self.registry_active,
            "rules_applied": self.rules_applied,
            "index_generated_at": self.index_generated_at,
            "brief_generated_at": self.brief_generated_at,
            "stack_guess": self.stack_guess,
            "format": self.format,
            "handoff": self.handoff,
            "index_file_count": self.index_file_count,
        }


def _rel_from_root(root: Path, target: Path) -> str:
    try:
        return target.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return target.as_posix()


def _read_text_limited(path: Path, max_chars: int) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) <= max_chars:
        return text.strip()
    return text[:max_chars].strip() + "\n\n…(truncated)"


def _read_tail_lines(path: Path, max_lines: int) -> str:
    if not path.is_file():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines).strip()
    return "\n".join(lines[-max_lines:]).strip()


def _collect_rule_excerpts(paths: AppPaths, rule_paths: list[str], max_chars_each: int = 2000) -> str:
    excerpts: list[str] = []
    for rel in rule_paths:
        target = paths.root / rel
        if not target.is_file():
            continue
        text = _read_text_limited(target, max_chars_each)
        if not text:
            continue
        excerpts.append(f"### {rel}\n\n{text}")
    return "\n\n".join(excerpts).strip()


def load_index_json(index_path: Path) -> dict[str, Any] | None:
    if not index_path.is_file():
        return None
    try:
        return json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _stack_guess(ext_stats: dict[str, int], file_count: int) -> list[str]:
    total = sum(ext_stats.values()) or file_count or 1
    py_n = ext_stats.get(".py", 0)
    cpp_n = ext_stats.get(".cpp", 0) + ext_stats.get(".h", 0) + ext_stats.get(".hpp", 0) + ext_stats.get(".c", 0)
    web_n = ext_stats.get(".js", 0) + ext_stats.get(".ts", 0) + ext_stats.get(".tsx", 0) + ext_stats.get(".html", 0) + ext_stats.get(".css", 0)
    guess: list[str] = []
    if py_n / total >= _PY_SHARE_MIN or (py_n >= 1 and total <= 5):
        guess.append("python")
    if cpp_n / total >= _CPP_SHARE_MIN or (cpp_n >= 1 and total <= 5):
        guess.append("cpp")
    if web_n / total >= 0.08 or (web_n >= 1 and total <= 5):
        guess.append("web")
    return guess


def _entrypoint_names_from_index(files: list[dict], limit: int = 20) -> list[str]:
    picked: list[str] = []
    for item in files:
        if item.get("is_entrypoint") is True:
            path = str(item.get("path", "")).strip()
            if path:
                picked.append(path)
        if len(picked) >= limit:
            break
    return picked


def pick_rules_paths(paths: AppPaths, project: str, ext_stats: dict[str, int], file_count: int) -> tuple[list[str], list[str]]:
    """Возвращает (относительные пути от root, stack_guess)."""
    root = paths.root
    chosen: list[str] = []
    global_md = paths.rules / "global.md"
    if global_md.is_file():
        chosen.append(_rel_from_root(root, global_md))

    stack = _stack_guess(ext_stats, file_count)
    if "python" in stack:
        py_md = paths.rules / "python.md"
        if py_md.is_file():
            chosen.append(_rel_from_root(root, py_md))
    if "cpp" in stack:
        cpp_md = paths.rules / "cpp.md"
        if cpp_md.is_file():
            chosen.append(_rel_from_root(root, cpp_md))

    pr_md = paths.rules / "projects" / f"{project}.md"
    if pr_md.is_file():
        chosen.append(_rel_from_root(root, pr_md))

    if not stack and file_count == 0:
        stack = ["unknown"]

    return chosen, stack


def _priority_paths_from_index(files: list[dict], limit: int) -> list[str]:
    scored: list[tuple[int, str]] = []
    for item in files:
        path_value = str(item.get("path", "")).strip()
        if not path_value:
            continue
        if "priority_score" in item:
            raw_score = item.get("priority_score")
            try:
                score = int(raw_score)
            except (TypeError, ValueError):
                score = 100
        else:
            base = Path(path_value).name.lower()
            score = 100
            if base in {"main.py", "app.py", "__main__.py", "cmakelists.txt", "readme.md", "pyproject.toml"}:
                score = 0
            elif base.endswith(".py"):
                score = 10
        scored.append((score, path_value))
    scored.sort(key=lambda x: (x[0], x[1]))
    return [path for _, path in scored[:limit]]


def _top_level_dirs_from_index(files: list[dict], limit: int = 8) -> list[str]:
    dirs: list[str] = []
    seen: set[str] = set()
    for item in files:
        path_value = str(item.get("path", "")).strip()
        if not path_value or "/" not in path_value:
            continue
        top = path_value.split("/", 1)[0]
        if top and top not in seen:
            seen.add(top)
            dirs.append(top)
        if len(dirs) >= limit:
            break
    return dirs


def build_brief_markdown(
    *,
    paths: AppPaths,
    project: str,
    registry_active: str | None,
    index_payload: dict[str, Any] | None,
    memory_dir: Path,
    format_name: str,
    handoff: bool,
) -> tuple[str, BriefMeta]:
    root = paths.root
    ext_stats: dict[str, int] = {}
    index_generated_at: str | None = None
    idx_files: list[dict] = []
    file_count = 0
    if index_payload:
        raw_stats = index_payload.get("extension_stats") or {}
        ext_stats = {str(k).lower(): int(v) for k, v in raw_stats.items()}
        index_generated_at = index_payload.get("generated_at")
        idx_files = list(index_payload.get("files") or [])
        file_count = int(index_payload.get("file_count") or len(idx_files))
    entrypoints = _entrypoint_names_from_index(idx_files, limit=20)

    rules_paths, stack = pick_rules_paths(paths, project, ext_stats, file_count)

    now = datetime.now(tz=timezone.utc).isoformat()
    meta = BriefMeta(
        project=project,
        registry_active=registry_active,
        rules_applied=rules_paths,
        index_generated_at=index_generated_at,
        brief_generated_at=now,
        stack_guess=stack,
        format="handoff" if handoff else format_name,
        handoff=handoff,
        index_file_count=file_count,
    )

    lines: list[str] = []

    def add_section(title: str, body: str) -> None:
        if not body.strip():
            return
        lines.append(f"## {title}\n")
        lines.append(body.strip())
        lines.append("")

    workspace_path = paths.workspace / project
    ws_rel = _rel_from_root(root, workspace_path)

    if handoff:
        lines.append(f"# Handoff: `{project}`\n")
        lines.append(f"- Репозиторий системы (корень): `{_rel_from_root(root, root)}`")
        lines.append(f"- Рабочая папка проекта (workspace): `{ws_rel}`")
        lines.append(f"- Активный проект в registry: `{registry_active}`")
        lines.append(f"- Индекс: сгенерирован `{index_generated_at or '—'}`; файлов в индексе: {file_count}")
        if index_generated_at is None or file_count == 0:
            lines.append("- Действие: при изменениях в коде выполните `index-project` / `rebuild-context`.")
        lines.append("")
        add_section(
            "Последние решения (decision-log)",
            _read_tail_lines(memory_dir / "decision-log.md", 25),
        )
        add_section(
            "Заметки (хвост)",
            _read_tail_lines(memory_dir / "notes.md", 25),
        )
        add_section(
            "Известные проблемы",
            _read_tail_lines(memory_dir / "known-issues.md", 40),
        )
        add_section(
            "Summary (фрагмент)",
            _read_text_limited(memory_dir / "summary.md", 6000),
        )
        pri = _priority_paths_from_index(idx_files, 20)
        if pri:
            lines.append("## Ключевые пути (по индексу)\n")
            for p in pri:
                lines.append(f"- `{p}`")
            lines.append("")
        lines.append("## Не ломать / осторожно\n")
        lines.append("- Учитывайте существующую архитектуру и `known-issues`; новые зависимости — явно.")
        lines.append("")
    else:
        lines.append(f"# Session brief: `{project}`\n")
        lines.append(f"- Workspace: `{ws_rel}`")
        lines.append(f"- Активный проект в registry: `{registry_active}`")
        lines.append(f"- Индекс: `{index_generated_at or 'нет'}`; файлов: {file_count}")
        if index_generated_at is None or file_count == 0:
            lines.append("- Перед работой: `python scripts/run_cli.py index-project` (или `--project " + project + "`).")
        lines.append(f"- Эвристика стека: `{', '.join(stack)}`")
        lines.append("")
        lines.append("## Стартовый чеклист\n")
        lines.append("- Убедитесь, что MCP подключён в LM Studio к `config/mcp/mcp.json`.")
        lines.append("- Для нового чата используйте свежий `latest.md` из `data/context/briefs/<project>/`.")
        lines.append("- При изменениях в дереве проекта запустите `rebuild-context`.")
        lines.append("")

        if entrypoints:
            lines.append("## Entrypoints (from index)\n")
            for p in entrypoints[:8]:
                lines.append(f"- `{p}`")
            lines.append("")
        top_dirs = _top_level_dirs_from_index(idx_files, limit=8)
        if top_dirs:
            lines.append("## Ключевые директории\n")
            for d in top_dirs:
                lines.append(f"- `{d}/`")
            lines.append("")

        add_section("Summary", _read_text_limited(memory_dir / "summary.md", 4500 if format_name == "short" else 12000))

        short_tail = 8 if format_name == "short" else 20
        add_section("Known issues", _read_tail_lines(memory_dir / "known-issues.md", 12 if format_name == "short" else 35))

        add_section(
            "Recent decisions",
            _read_tail_lines(memory_dir / "decision-log.md", short_tail if format_name == "short" else 35),
        )
        add_section("Worklog (tail)", _read_tail_lines(memory_dir / "worklog.md", 10 if format_name == "short" else 35))

        if format_name == "full":
            add_section("Notes (tail)", _read_tail_lines(memory_dir / "notes.md", 30))
            add_section("Architecture", _read_text_limited(memory_dir / "architecture.md", 4000))
            add_section("Run commands", _read_text_limited(memory_dir / "run-commands.md", 3000))
            lines.append("## Контракт выполнения\n")
            lines.append("- Не писать «сделано», пока нет подтверждённых tool-результатов.")
            lines.append("- Если правка не применена инструментами, явно указать «не применено».")
            lines.append("- Работать только в scope активного проекта и его memory/brief.")
            lines.append("- Пустой (`null/empty`) shell-вывод считать непрошедшей верификацией.")
            lines.append("")

        lines.append("## Applicable rules (paths)\n")
        for rp in rules_paths:
            lines.append(f"- `{rp}` (через MCP от корня репозитория или абсолютный путь)")
        lines.append("")
        if format_name == "full":
            rules_text = _collect_rule_excerpts(paths, rules_paths, max_chars_each=2000)
            add_section("Applicable rules (excerpt)", rules_text)

        pr_file = paths.rules / "projects" / f"{project}.md"
        if format_name == "full" and pr_file.is_file():
            add_section(
                f"Project rules `{_rel_from_root(root, pr_file)}` (excerpt)",
                _read_text_limited(pr_file, 8000),
            )

        n_top = 12 if format_name == "short" else 35
        pri = _priority_paths_from_index(idx_files, n_top)
        if pri:
            lines.append("## Files to open first (from index)\n")
            for p in pri:
                lines.append(f"- `{p}`")
            lines.append("")

        lines.append("## Expectations for the model\n")
        lines.append("- Работать в контексте этого проекта и путей выше; не выдумывать файлы.")
        lines.append("- При больших изменениях в дереве — предложить пересобрать индекс (`rebuild-context`).")
        lines.append("")

    return "\n".join(lines).strip() + "\n", meta
