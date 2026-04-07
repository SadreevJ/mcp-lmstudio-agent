from __future__ import annotations

import argparse
import logging
import os
import sys

from local_ai_dev.application.services import ProjectService
from local_ai_dev.infrastructure.env import load_env_file
from local_ai_dev.infrastructure.lmstudio import check_lmstudio
from local_ai_dev.infrastructure.paths import get_paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="local-ai-dev", description="Offline local AI dev system CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("bootstrap", help="Create baseline directories and registry.")
    sub.add_parser("sync-mcp", help="Write config/mcp/mcp.json for the active project (filesystem + shell scope).")
    sub.add_parser("list-projects", help="List registered projects.")

    add_project = sub.add_parser("add-project", help="Add project to registry.")
    add_project.add_argument("name")
    add_project.add_argument("--path", default=None, help="Absolute or relative path to project directory.")

    switch = sub.add_parser("switch-project", help="Switch active project.")
    switch.add_argument("name")

    status = sub.add_parser("status", help="Show system status.")
    status.add_argument("--skip-lmstudio", action="store_true")

    index = sub.add_parser("index-project", help="Build file index for active or chosen project.")
    index.add_argument("--project", default=None)
    index.add_argument("--max-files", type=int, default=1500)

    rebuild = sub.add_parser("rebuild-context", help="Rebuild context for active or chosen project.")
    rebuild.add_argument("--project", default=None)
    rebuild.add_argument("--max-files", type=int, default=1500)

    log_decision = sub.add_parser("log-decision", help="Append decision to decision log.")
    log_decision.add_argument("text")
    log_decision.add_argument("--project", default=None)

    brief = sub.add_parser("brief", help="Build session brief for a new chat (data/context/briefs/…).")
    brief.add_argument("--project", default=None, help="Project name; default: active from registry.")
    brief.add_argument("--format", choices=["short", "full"], default="short")
    brief.add_argument("--handoff", action="store_true", help="Engineering handoff template instead of session brief.")
    brief.add_argument("--no-history", action="store_true", help="Do not write timestamped copy of the brief.")

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=os.getenv("LOCAL_AI_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    paths = get_paths()
    load_env_file(paths.root / ".env")
    service = ProjectService(paths)
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "bootstrap":
            registry = service.bootstrap()
            _print_registry(registry, "Bootstrap completed")
            return 0
        if args.command == "sync-mcp":
            path = service.sync_mcp_config()
            print(f"MCP: корень файлов и shell = активный проект. Записано: {path}")
            print("В LM Studio переподключите MCP к этому файлу или откройте новый чат.")
            return 0
        if args.command == "list-projects":
            registry = service.get_registry()
            _print_registry(registry, "Projects")
            return 0
        if args.command == "add-project":
            new_path = None if args.path is None else (paths.root / args.path).resolve()
            registry = service.add_project(args.name, new_path)
            print(f"Project '{args.name}' added.")
            _print_registry(registry, "Projects")
            return 0
        if args.command == "switch-project":
            registry = service.switch_project(args.name)
            print(f"Active project: {registry.active_project}")
            print("MCP обновлён под эту папку (см. config/mcp/mcp.json). Переподключите MCP в LM Studio.")
            return 0
        if args.command == "index-project":
            path = service.index_project(name=args.project, max_files=args.max_files)
            print(f"Index written: {path}")
            return 0
        if args.command == "rebuild-context":
            path = service.rebuild_context(name=args.project, max_files=args.max_files)
            print(f"Context rebuilt: {path}")
            return 0
        if args.command == "log-decision":
            path = service.append_decision(args.text, project=args.project)
            print(f"Decision appended: {path}")
            return 0
        if args.command == "brief":
            path, meta = service.build_brief(
                name=args.project,
                format_name=args.format,
                handoff=args.handoff,
                write_history_copy=not args.no_history,
            )
            print(path.resolve())
            print(f"format={meta.format} rules={','.join(meta.rules_applied) or '(none)'}")
            return 0
        if args.command == "status":
            registry = service.get_registry()
            print("System status")
            print(f"- root: {paths.root}")
            print(f"- workspace: {paths.workspace}")
            print(f"- projects registered: {len(registry.projects)}")
            print(f"- active project: {registry.active_project}")
            if not args.skip_lmstudio:
                base_url = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234")
                api_key = os.getenv("LMSTUDIO_API_KEY")
                status = check_lmstudio(base_url=base_url, api_key=api_key)
                print(f"- lmstudio: {'ok' if status.reachable else 'down'}")
                print(f"- lmstudio message: {status.message}")
                if status.models:
                    print("- lmstudio models:")
                    for model in status.models:
                        print(f"  - {model}")
            return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


def _print_registry(registry, title: str) -> None:
    print(title)
    print(f"- active: {registry.active_project}")
    if not registry.projects:
        print("- no projects")
        return
    for name, record in sorted(registry.projects.items()):
        marker = "*" if name == registry.active_project else " "
        print(f"{marker} {name}: {record.path}")


if __name__ == "__main__":
    raise SystemExit(main())
