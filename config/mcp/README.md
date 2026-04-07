# MCP Notes

Шаблон: `mcp.lmstudio.template.json`. Актуальный локальный файл с абсолютными путями генерируется из **активного проекта** в реестре (`data/context/registry.json` → `active_project`). Команда (один источник логики):

```powershell
python scripts\run_cli.py sync-mcp
```

То же делает обёртка:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\sync-mcp.ps1
```

После **`switch-project`** / **`add-project`** / **`bootstrap`** `mcp.json` тоже обновляется, если синхронизация не упала с ошибкой.

Сервера:

- **`project-filesystem`** — `@modelcontextprotocol/server-filesystem`, **несколько** разрешённых корней для одного проекта:
  - `…/workspace/<имя>/` — код;
  - `…/data/memory/projects/<имя>/` — summary, notes, decision-log и т.д.;
  - `…/data/context/briefs/<имя>/` — сгенерированные брифы.  
  Иначе модель получает отказ при записи в `data/…`, хотя «логически» работает с проектом `test1`: эти папки **вне** `workspace/<имя>`.
- **`project-shell`** — `mcp-shell@0.1.3` (`npx`): инструмент `run_command`, рабочая папка по умолчанию — **тот же каталог активного проекта**. Нужны Node.js и `npx`.  
  Пакет **`mcp-shell-server`** (Python, whitelist) на Windows не использовать — там модуль `pwd` (Unix).  
  **Безопасность:** у `mcp-shell` blacklist, не whitelist; команды через shell — возможны обходы. Это не песочница.

Порядок для LM Studio:

1. Убедитесь, что в реестре выбран нужный проект (`switch-project` или пульт, шаг 4).
2. Выполните `sync-mcp` (если ещё не делали после смены проекта).
3. В чате укажите **`config\mcp\mcp.json`** — будут и диск, и shell. Плагин `project-filesystem` в LM Studio даёт только один сервер; для терминала нужен этот файл.

**Смена проекта:** файл `mcp.json` перезаписывается. В открытом чате LM Studio может остаться старая сессия MCP — **переподключите** файл или начните **новый чат**.

**Плагин `project-filesystem`:** `mcp-bridge-config.json` в `%USERPROFILE%\.lmstudio\extensions\plugins\mcp\project-filesystem\`. Синхронизация MCP обновляет его (только filesystem). Старый ярлык: `scripts\sync-lmstudio-mcp-plugin.ps1` вызывает тот же `sync-mcp.ps1`.

Другие MCP можно дописать в сгенерированный `mcp.json` вручную.
