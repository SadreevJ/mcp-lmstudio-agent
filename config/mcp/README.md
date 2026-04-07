# MCP Notes

Шаблон: `mcp.lmstudio.template.json`. Актуальный локальный файл с абсолютными путями генерируется скриптом (файл `mcp.json` в git не хранится):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\sync-mcp.ps1
```

Сервера:

- **`project-filesystem`** — `@modelcontextprotocol/server-filesystem`, корень разрешённых путей: `workspace/`.
- **`project-shell`** — `mcp-shell@0.1.3` (`npx`): инструмент `run_command`, рабочая папка по умолчанию — `workspace/`. Нужны Node.js и `npx`.  
  Пакет **`mcp-shell-server`** (Python, whitelist) на Windows не использовать — там модуль `pwd` (Unix).  
  **Безопасность:** у `mcp-shell` blacklist, не whitelist; команды через shell — возможны обходы. Это не песочница.

Порядок для LM Studio:

1. Выполните `scripts\sync-mcp.ps1`.
2. В чате укажите **`config\mcp\mcp.json`** — будут и диск, и shell. Плагин `project-filesystem` в LM Studio даёт только один сервер; для терминала нужен этот файл.

**Плагин `project-filesystem`:** `mcp-bridge-config.json` в `%USERPROFILE%\.lmstudio\extensions\plugins\mcp\project-filesystem\`. `sync-mcp.ps1` обновляет его (только filesystem). Старый ярлык: `scripts\sync-lmstudio-mcp-plugin.ps1` вызывает тот же `sync-mcp.ps1`.

Другие MCP можно дописать в сгенерированный `mcp.json` вручную.
