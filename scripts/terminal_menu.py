from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "run_cli.py"


def run_cli(args: list[str], *, show_output: bool = False) -> subprocess.CompletedProcess[str]:
    print(f">>> python scripts\\run_cli.py {' '.join(args)}")
    completed = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if show_output:
        out = (completed.stdout or "").strip()
        err = (completed.stderr or "").strip()
        if out:
            print(out)
        if err:
            print(err)
    return completed


def has_any_output(result: subprocess.CompletedProcess[str]) -> bool:
    return bool((result.stdout or "").strip() or (result.stderr or "").strip())


def ensure_bootstrap() -> None:
    registry = ROOT / "data" / "context" / "registry.json"
    if registry.is_file():
        return
    print("Реестр не найден. Выполняю bootstrap...")
    run_cli(["bootstrap"], show_output=True)


def clear_screen() -> None:
    print("\n" * 2)


def title() -> None:
    clear_screen()
    print("===============================================")
    print(" xUdav: терминальный режим")
    print("===============================================")
    print(f"Корень: {ROOT}")
    active = load_active_project()
    if active:
        print(f"Активный проект: {active}")
        print(f"Готовность: {readiness_line(active)}")
        if not is_workspace_project(active):
            print("Требуется действие: активный проект вне workspace. Выберите директорию через пункт 3.")
    print()


def pause() -> None:
    input("Нажмите Enter для продолжения...")


def prepare_project() -> None:
    projects = list_workspace_projects()
    if projects:
        print(f"Доступные проекты: {', '.join(projects)}")
    project = input("Выберите директорию проекта из workspace: ").strip()
    if not project:
        print("Имя проекта пустое. Отмена.")
        return
    if project not in projects:
        print(f"Директория '{project}' не найдена в workspace. Отмена.")
        return
    print(f"Текущая готовность для '{project}': {readiness_line(project)}")
    result = run_cli(["prepare-chat", "--project", project], show_output=False)
    if result.returncode != 0:
        print("Требуется действие: подготовка проекта завершилась ошибкой.")
        err = (result.stderr or "").strip() or (result.stdout or "").strip()
        if err:
            print(err.splitlines()[-1])
        return
    if not has_any_output(result):
        print("Требуется действие: пустой вывод shell, верификация не подтверждена.")
        return
    summary = prepared_facts(project)
    if summary["brief_exists"] != "true":
        print("Требуется действие: brief не найден после prepare-chat.")
        return
    if summary["active_project"] != project:
        print("Требуется действие: активный проект после prepare-chat не совпадает с выбранным.")
        return
    print("OK: проект подготовлен.")
    print(f"- active_project: {summary['active_project']}")
    print(f"- index_file_count: {summary['index_file_count']}")
    print(f"- brief: {summary['brief_path']}")
    print()
    print("Готово. Дальше в LM Studio:")
    print("1) Откройте новый чат")
    print("2) Подключите MCP: config\\mcp\\mcp.json")
    print(f"3) Начните работу по проекту '{project}'")


def load_registry_payload() -> dict:
    registry = ROOT / "data" / "context" / "registry.json"
    if not registry.is_file():
        return {}
    try:
        return json.loads(registry.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def list_workspace_projects() -> list[str]:
    workspace_root = ROOT / "workspace"
    if not workspace_root.is_dir():
        return []
    names = [p.name for p in workspace_root.iterdir() if p.is_dir()]
    names.sort()
    return names


def load_active_project() -> str:
    payload = load_registry_payload()
    active = payload.get("active_project")
    return str(active) if active else ""


def is_workspace_project(project: str) -> bool:
    return project in list_workspace_projects()


def readiness_line(project: str) -> str:
    memory = ROOT / "data" / "memory" / "projects" / project
    index_ok = (memory / "index.json").is_file()
    brief_ok = (ROOT / "data" / "context" / "briefs" / project / "latest.md").is_file()
    mcp_ok = (ROOT / "config" / "mcp" / "mcp.json").is_file()
    status = [
        f"index={'ok' if index_ok else 'нет'}",
        f"brief={'ok' if brief_ok else 'нет'}",
        f"mcp={'ok' if mcp_ok else 'нет'}",
    ]
    return ", ".join(status)


def prepared_facts(project: str) -> dict[str, str]:
    active = load_active_project() or "<none>"
    memory = ROOT / "data" / "memory" / "projects" / project
    index_count = "0"
    index_path = memory / "index.json"
    if index_path.is_file():
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            index_count = str(payload.get("file_count", 0))
        except (json.JSONDecodeError, OSError):
            index_count = "unknown"
    brief_path = ROOT / "data" / "context" / "briefs" / project / "latest.md"
    return {
        "active_project": active,
        "index_file_count": index_count,
        "brief_path": str(brief_path),
        "brief_exists": "true" if brief_path.is_file() else "false",
    }


def menu() -> None:
    print("[1] Проверка статуса")
    print("[2] Bootstrap (только при первом запуске)")
    print("[3] Выбрать директорию (workspace) и подготовить чат")
    print("[0] Выход")
    print()


def main() -> int:
    ensure_bootstrap()
    while True:
        title()
        menu()
        choice = input("Выберите пункт меню: ").strip()
        if choice == "1":
            result = run_cli(["status"], show_output=True)
            if result.returncode == 0 and has_any_output(result):
                print("OK")
            else:
                print("Требуется действие")
            pause()
        elif choice == "2":
            result = run_cli(["bootstrap"], show_output=True)
            if result.returncode == 0 and has_any_output(result):
                print("OK")
            else:
                print("Требуется действие")
            pause()
        elif choice == "3":
            prepare_project()
            pause()
        elif choice == "0":
            print("Выход.")
            return 0
        else:
            print("Неизвестный пункт. Повторите ввод.")
            pause()


if __name__ == "__main__":
    raise SystemExit(main())
