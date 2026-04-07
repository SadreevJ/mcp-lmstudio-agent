# Writes config/mcp/mcp.json (filesystem + shell) and patches LM Studio project-filesystem plugin.
# From repo root: powershell -ExecutionPolicy Bypass -File scripts\sync-mcp.ps1

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$workspace = Join-Path $root "workspace"
$mcpOut = Join-Path $root "config\mcp\mcp.json"
$pluginDir = Join-Path $env:USERPROFILE ".lmstudio\extensions\plugins\mcp\project-filesystem"
$pluginConfigPath = Join-Path $pluginDir "mcp-bridge-config.json"

New-Item -ItemType Directory -Path (Split-Path $mcpOut) -Force | Out-Null

# mcp-shell: Node, blacklist-based; cwd = workspace. Python mcp-shell-server is Unix-only (pwd module).
$fullConfig = [ordered]@{
    mcpServers = [ordered]@{
        "project-filesystem" = [ordered]@{
            command = "npx"
            args    = @("-y", "@modelcontextprotocol/server-filesystem", $workspace)
            cwd     = $root
        }
        "project-shell" = [ordered]@{
            command = "npx"
            args    = @("-y", "mcp-shell@0.1.3")
            cwd     = $workspace
        }
    }
}

$json = $fullConfig | ConvertTo-Json -Depth 8
$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($mcpOut, $json, $utf8)
Write-Host ("OK: wrote " + $mcpOut)

$fsOnly = [ordered]@{
    command = "npx"
    args    = @("-y", "@modelcontextprotocol/server-filesystem", $workspace)
    cwd     = $root
}
$fsJson = $fsOnly | ConvertTo-Json -Depth 5
if (-not (Test-Path $pluginDir)) {
    Write-Host ("SKIP: plugin dir missing: " + $pluginDir)
} else {
    [System.IO.File]::WriteAllText($pluginConfigPath, $fsJson, $utf8)
    Write-Host ("OK: updated plugin config (filesystem only). Path: " + $pluginConfigPath)
}

Write-Host "Point LM Studio chat MCP at this file for filesystem + shell:"
Write-Host $mcpOut
