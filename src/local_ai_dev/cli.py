from __future__ import annotations

import argparse
import logging
import os
import sys

from local_ai_dev.domain.models import CompletionContract, ExecutionGuardState
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

    search = sub.add_parser("search-project", help="Search in active or chosen project.")
    search.add_argument("--project", default=None)
    search.add_argument("--mode", choices=["file", "text", "todo", "entrypoints", "defs"], default="file")
    search.add_argument("--query", default="")
    search.add_argument("--max-results", type=int, default=30)

    log_decision = sub.add_parser("log-decision", help="Append decision to decision log.")
    log_decision.add_argument("text")
    log_decision.add_argument("--project", default=None)

    brief = sub.add_parser("brief", help="Build session brief for a new chat (data/context/briefs/…).")
    brief.add_argument("--project", default=None, help="Project name; default: active from registry.")
    brief.add_argument("--format", choices=["short", "full"], default="short")
    brief.add_argument("--handoff", action="store_true", help="Engineering handoff template instead of session brief.")
    brief.add_argument("--no-history", action="store_true", help="Do not write timestamped copy of the brief.")

    prepare = sub.add_parser(
        "prepare-chat",
        help="Switch project (optional), index, sync-mcp and build brief in one command.",
    )
    prepare.add_argument("--project", default=None)
    prepare.add_argument("--max-files", type=int, default=1500)
    prepare.add_argument("--format", choices=["short", "full"], default="short")

    finalize = sub.add_parser(
        "finalize-task",
        help="Finalize task status against a completion contract.",
    )
    finalize.add_argument("--project", default=None)
    finalize.add_argument("--requested-status", default="completed")
    finalize.add_argument("--expect-file", action="append", default=[])
    finalize.add_argument(
        "--expect-contains",
        action="append",
        default=[],
        help="Format: relative/path::text",
    )
    finalize.add_argument("--shell-exit-code", type=int, default=None)
    finalize.add_argument(
        "--shell-cwd",
        default=None,
        help="Reported shell working directory (for environment_mismatch vs project root).",
    )
    finalize.add_argument(
        "--shell-target-path",
        default=None,
        help="Absolute path the shell used (e.g. from error); compared to first --expect-file.",
    )
    finalize.add_argument("--step-index", type=int, default=1)
    finalize.add_argument("--max-steps", type=int, default=20)
    finalize.add_argument("--action-fingerprint", default="")
    finalize.add_argument("--previous-action-fingerprint", default="")
    finalize.add_argument("--repeated-fingerprint-count", type=int, default=0)
    finalize.add_argument("--max-repeated-fingerprint", type=int, default=2)
    finalize.add_argument("--no-progress-steps", type=int, default=0)
    finalize.add_argument("--max-no-progress-steps", type=int, default=3)

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
        if args.command == "search-project":
            project, results = service.search_in_project(
                name=args.project,
                mode=args.mode,
                query=args.query,
                max_results=args.max_results,
            )
            print(f"project={project} mode={args.mode} results={len(results)}")
            for item in results:
                path = item.get("path", "")
                line = item.get("line")
                text = item.get("text", "")
                kind = item.get("kind", "")
                if line is None:
                    print(f"- [{kind}] {path}")
                else:
                    print(f"- [{kind}] {path}:{line} {text}")
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
        if args.command == "prepare-chat":
            project, brief_path = service.prepare_chat_context(
                name=args.project,
                max_files=args.max_files,
                format_name=args.format,
            )
            facts = service.get_prepared_facts(project)
            print(f"active_project={project}")
            print(f"brief={brief_path.resolve()}")
            print(f"verified_active_project={facts['active_project']}")
            print(f"verified_index_file_count={facts['index_file_count']}")
            print(f"verified_brief_exists={facts['brief_exists']}")
            print("MCP обновлён под активный проект; в LM Studio откройте новый чат и подключите config/mcp/mcp.json.")
            return 0
        if args.command == "finalize-task":
            contains_map: dict[str, str] = {}
            for raw in args.expect_contains:
                if "::" not in raw:
                    raise ValueError(f"Некорректный --expect-contains: '{raw}'. Ожидается relative/path::text")
                path_part, text_part = raw.split("::", 1)
                rel = path_part.strip()
                if not rel:
                    raise ValueError(f"Некорректный --expect-contains: '{raw}'. Путь не должен быть пустым")
                contains_map[rel] = text_part
            contract = CompletionContract(
                required_file_exists=[item.strip() for item in args.expect_file if item.strip()],
                required_text_contains=contains_map,
                require_shell_exit_zero=args.shell_exit_code is not None,
                shell_cwd=args.shell_cwd,
                shell_target_path=args.shell_target_path,
            )
            guard_state = ExecutionGuardState(
                step_index=args.step_index,
                max_steps=args.max_steps,
                action_fingerprint=args.action_fingerprint.strip(),
                previous_action_fingerprint=args.previous_action_fingerprint.strip(),
                repeated_fingerprint_count=args.repeated_fingerprint_count,
                max_repeated_fingerprint=args.max_repeated_fingerprint,
                no_progress_steps=args.no_progress_steps,
                max_no_progress_steps=args.max_no_progress_steps,
            )
            outcome = service.finalize_task(
                name=args.project,
                requested_status=args.requested_status,
                contract=contract,
                shell_exit_code=args.shell_exit_code,
                guard_state=guard_state,
            )
            print(f"final_status={outcome.status}")
            print(f"evidence={','.join(outcome.evidence) if outcome.evidence else '(none)'}")
            print(f"reason={outcome.reason or '(none)'}")
            return 0 if outcome.status == "completed" else 1
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
