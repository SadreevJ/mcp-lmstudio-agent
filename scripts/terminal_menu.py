from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "run_cli.py"


def run_cli(args: list[str]) -> int:
    print(f">>> python scripts\\run_cli.py {' '.join(args)}")
    completed = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.returncode


def ensure_bootstrap() -> None:
    registry = ROOT / "data" / "context" / "registry.json"
    if registry.is_file():
        return
    print("Реестр не найден. Выполняю bootstrap...")
    run_cli(["bootstrap"])


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
    print()


def pause() -> None:
    input("Нажмите Enter для продолжения...")


def prepare_project() -> None:
    projects = load_project_names()
    if projects:
        print(f"Доступные проекты: {', '.join(projects)}")
    project = input("Выберите директорию проекта: ").strip()
    if not project:
        print("Имя проекта пустое. Отмена.")
        return
    print(f"Текущая готовность для '{project}': {readiness_line(project)}")
    run_cli(["prepare-chat", "--project", project])
    print()
    print("Готово. Дальше в LM Studio:")
    print("1) Откройте новый чат")
    print("2) Подключите MCP: config\\mcp\\mcp.json")
    print(f"3) Начните работу по проекту '{project}'")


def search_project() -> None:
    project = input("Проект (Enter = активный): ").strip()
    mode = input("Режим [file/text/todo/entrypoints/defs] (Enter = file): ").strip().lower() or "file"
    query = ""
    if mode in {"file", "text", "defs"}:
        query = input("Запрос (можно пусто для file/defs): ").strip()
    args = ["search-project", "--mode", mode, "--max-results", "30"]
    if project:
        args += ["--project", project]
    if query:
        args += ["--query", query]
    run_cli(args)


def load_project_names() -> list[str]:
    registry = ROOT / "data" / "context" / "registry.json"
    if not registry.is_file():
        return []
    try:
        payload = json.loads(registry.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return sorted((payload.get("projects") or {}).keys())


def load_active_project() -> str:
    registry = ROOT / "data" / "context" / "registry.json"
    if not registry.is_file():
        return ""
    try:
        payload = json.loads(registry.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""
    active = payload.get("active_project")
    return str(active) if active else ""


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


def wizard_two_projects() -> None:
    projects = load_project_names()
    if projects:
        print(f"Доступные проекты: {', '.join(projects)}")
    first = input("Проект для первого чата (например: test2): ").strip()
    second = input("Проект для второго чата (например: test1): ").strip()
    if not first or not second:
        print("Нужно указать оба проекта. Отмена.")
        return
    print()
    print(f"Готовность '{first}': {readiness_line(first)}")
    print(f"Готовность '{second}': {readiness_line(second)}")
    print()
    print(f"Шаг 1/2: подготавливаю '{first}'...")
    if run_cli(["prepare-chat", "--project", first]) != 0:
        print("Не удалось подготовить первый проект.")
        return
    print()
    print("Откройте LM Studio -> новый чат -> подключите MCP -> начните работу.")
    input("Нажмите Enter после завершения шага в LM Studio...")
    print()
    print(f"Шаг 2/2: подготавливаю '{second}'...")
    if run_cli(["prepare-chat", "--project", second]) != 0:
        print("Не удалось подготовить второй проект.")
        return
    print()
    print("Готово. Теперь откройте второй новый чат в LM Studio для второго проекта.")


def show_guide() -> None:
    print("Быстрый сценарий для двух проектов:")
    print()
    print("A) Первый чат (например: test2):")
    print("   - Нажмите [3] Подготовить проект к чату")
    print("   - Введите: test2")
    print("   - В LM Studio откройте новый чат и подключите MCP")
    print()
    print("B) Второй чат (например: test1):")
    print("   - Снова нажмите [3], введите: test1")
    print("   - В LM Studio откройте НОВЫЙ чат для test1")


def menu() -> None:
    print("[1] Проверка статуса")
    print("[2] Bootstrap (только при первом запуске)")
    print("[3] Подготовить проект к новому чату (prepare-chat)")
    print("[4] Поиск по проекту (search-project)")
    print("[5] Показать проекты")
    print("[6] Подсказка по переключению test1/test2")
    print("[7] Мастер: подготовить два проекта подряд")
    print("[0] Выход")
    print()


def main() -> int:
    ensure_bootstrap()
    while True:
        title()
        menu()
        choice = input("Выберите пункт меню: ").strip()
        if choice == "1":
            run_cli(["status"])
            pause()
        elif choice == "2":
            run_cli(["bootstrap"])
            pause()
        elif choice == "3":
            prepare_project()
            pause()
        elif choice == "4":
            search_project()
            pause()
        elif choice == "5":
            run_cli(["list-projects"])
            pause()
        elif choice == "6":
            show_guide()
            pause()
        elif choice == "7":
            wizard_two_projects()
            pause()
        elif choice == "0":
            print("Выход.")
            return 0
        else:
            print("Неизвестный пункт. Повторите ввод.")
            pause()


if __name__ == "__main__":
    raise SystemExit(main())
