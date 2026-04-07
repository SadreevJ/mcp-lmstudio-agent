# mcp-lmstudio-agent

Offline-first coding workflow for local LLM development with LM Studio and MCP.  
This project provides a Python CLI to manage project context, generate MCP config for the active project, and prepare chat-ready brief files from local code and notes.

## What it does

- Works with local projects inside `workspace/`
- Keeps per-project memory on disk (`data/memory/projects/<project>/`)
- Builds searchable project indexes
- Generates brief files for new chat sessions
- Syncs MCP config so filesystem and shell tools point to the active project

## Why this exists

When you switch between multiple local codebases, AI context often becomes inconsistent.  
This repo gives you a repeatable local flow: pick a project, rebuild context, sync MCP, and start a clean chat with project-scoped data.

## Stack

- Python 3.10+
- LM Studio (configured manually in the app) — [lmstudio.ai](https://lmstudio.ai/)
- Model Context Protocol (MCP) — [modelcontextprotocol.io](https://modelcontextprotocol.io/)
- MCP servers:
  - `@modelcontextprotocol/server-filesystem`
  - `mcp-shell` (via `npx`)

## Repository layout

- `src/local_ai_dev/` — CLI + services for registry, indexing, brief generation, MCP sync
- `scripts/` — launch and helper scripts (`run_cli.py`, PowerShell helpers)
- `workspace/` — your local projects
- `data/context/registry.json` — active project and registered project paths
- `data/context/briefs/<project>/` — generated session briefs (`latest.md`, history, metadata)
- `data/memory/projects/<project>/` — project memory (`summary.md`, `notes.md`, `decision-log.md`, etc.)
- `config/mcp/` — MCP template and generated `mcp.json`
- `rules/` — model rules/prompts used by your workflow

## Requirements

- Python 3.10 or newer
- Node.js + `npx` (for MCP shell server)
- LM Studio installed and running locally

## Quick start (Windows)

```powershell
python scripts\run_cli.py bootstrap
python scripts\run_cli.py sync-mcp
python scripts\run_cli.py status
python scripts\run_cli.py prepare-chat --project test1
```

Then in LM Studio, attach/connect `config\mcp\mcp.json` to the chat session.

## CLI commands

```powershell
python scripts\run_cli.py bootstrap
python scripts\run_cli.py sync-mcp
python scripts\run_cli.py list-projects
python scripts\run_cli.py add-project <name> [--path <path>]
python scripts\run_cli.py switch-project <name>
python scripts\run_cli.py index-project [--project <name>] [--max-files 1500]
python scripts\run_cli.py rebuild-context [--project <name>] [--max-files 1500]
python scripts\run_cli.py search-project [--project <name>] --mode <file|text|todo|entrypoints|defs> [--query <text>] [--max-results 30]
python scripts\run_cli.py log-decision "<text>" [--project <name>]
python scripts\run_cli.py brief [--project <name>] [--format short|full] [--handoff] [--no-history]
python scripts\run_cli.py prepare-chat [--project <name>] [--max-files 1500] [--format short|full]
```

## Typical workflow

1. Select or switch active project
2. Rebuild index/context
3. Sync MCP config
4. Generate brief
5. Start a new LM Studio chat with `config\mcp\mcp.json`

This keeps filesystem access, shell working directory, and memory/brief files aligned with one active project.
`prepare-chat` is restricted to projects inside `workspace/`, which keeps sessions isolated and predictable.

## Notes on MCP scope

Generated MCP config is scoped to the active project and includes:
- project code directory in `workspace/<project>/`
- project memory directory in `data/memory/projects/<project>/`
- project brief directory in `data/context/briefs/<project>/`

So the model can read/write both code context and project memory files in one session.

## License

MIT — see `LICENSE`.
