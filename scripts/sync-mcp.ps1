# Delegates to Python (single source of truth): активный проект из registry -> config/mcp/mcp.json
# From repo root: powershell -ExecutionPolicy Bypass -File scripts\sync-mcp.ps1

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $root
try {
    python "$PSScriptRoot\run_cli.py" sync-mcp
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}
