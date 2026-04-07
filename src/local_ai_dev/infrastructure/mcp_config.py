from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from pathlib import Path

logger = logging.getLogger(__name__)

MCP_SHELL_VERSION = "mcp-shell@0.1.3"


def _filesystem_allowed_dirs(project_root: Path, extra_allowed: Sequence[Path] | None) -> list[Path]:
    """Absolute unique roots for @modelcontextprotocol/server-filesystem (multiple dirs allowed)."""
    seen_lower: set[str] = set()
    out: list[Path] = []
    for p in (project_root, *(extra_allowed or ())):
        r = p.resolve()
        key = str(r).casefold()
        if key in seen_lower:
            continue
        seen_lower.add(key)
        out.append(r)
    return out


def _filesystem_npx_args(roots: list[Path]) -> list[str]:
    return ["-y", "@modelcontextprotocol/server-filesystem", *[str(r) for r in roots]]


def build_mcp_json_payload(
    project_root: Path,
    repo_root: Path,
    *,
    extra_allowed: Sequence[Path] | None = None,
) -> dict:
    roots = _filesystem_allowed_dirs(project_root, extra_allowed)
    pr_fs = str(project_root.resolve())
    pr_shell = str(project_root.resolve())
    return {
        "mcpServers": {
            "project-filesystem": {
                "command": "npx",
                "args": _filesystem_npx_args(roots),
                "cwd": pr_fs,
            },
            "project-shell": {
                "command": "npx",
                "args": ["-y", MCP_SHELL_VERSION],
                "cwd": pr_shell,
            },
        }
    }


def build_lmstudio_plugin_filesystem_payload(
    project_root: Path,
    repo_root: Path,
    *,
    extra_allowed: Sequence[Path] | None = None,
) -> dict:
    roots = _filesystem_allowed_dirs(project_root, extra_allowed)
    pr_fs = str(project_root.resolve())
    return {
        "command": "npx",
        "args": _filesystem_npx_args(roots),
        "cwd": pr_fs,
    }


def write_mcp_json(
    out_path: Path,
    project_root: Path,
    repo_root: Path,
    *,
    extra_allowed: Sequence[Path] | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_mcp_json_payload(project_root, repo_root, extra_allowed=extra_allowed)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    roots = _filesystem_allowed_dirs(project_root, extra_allowed)
    logger.info("Wrote MCP config: %s filesystem_roots=%s", out_path, roots)


def patch_lmstudio_filesystem_plugin(
    project_root: Path,
    repo_root: Path,
    *,
    extra_allowed: Sequence[Path] | None = None,
) -> Path | None:
    plugin = Path.home() / ".lmstudio" / "extensions" / "plugins" / "mcp" / "project-filesystem" / "mcp-bridge-config.json"
    if not plugin.parent.is_dir():
        logger.info("LM Studio plugin dir missing, skip: %s", plugin.parent)
        return None
    payload = build_lmstudio_plugin_filesystem_payload(
        project_root, repo_root, extra_allowed=extra_allowed
    )
    plugin.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("Updated LM Studio plugin config: %s", plugin)
    return plugin
