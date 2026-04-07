# xUdav — быстрый старт на Windows

Нужно установить отдельно:
- Python 3.10+ (в PATH)
- Node.js (нужен `npx`, для MCP)
- LM Studio — скачать с [lmstudio.ai](https://lmstudio.ai/), один раз открыть приложение

После `git clone` в репозитории не будет: `.env`, `config/mcp/mcp.json` — их создаёте локально.

Терминальный режим (Windows, рекомендуется): дважды щёлкните `terminal.bat` в корне.

Откроется меню, где всё делается последовательно:
- проверка статуса;
- bootstrap (при первом запуске);
- подготовка проекта к новому чату (`prepare-chat`);
- поиск по проекту (`search-project`).
- мастер для двух проектов подряд (удобно для `test2 -> test1`).

Ручной запуск того же меню:

```powershell
python scripts\terminal_menu.py
```

Можно работать только через это меню и не запоминать команды.

## Шаги

1. Клонирование:

```powershell
git clone <url>
cd xUdav
```

2. Создать `.env`:

```powershell
copy .env.example .env
```

Откройте `.env`: укажите `LMSTUDIO_API_KEY`, если в LM Studio включена авторизация API.

3. Базовая инициализация:

```powershell
python scripts\run_cli.py bootstrap
```

4. Синхронизация MCP:

```powershell
python scripts\run_cli.py sync-mcp
```

или:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\sync-mcp.ps1
```

Появится `config\mcp\mcp.json`: корень MCP (файлы и shell) = папка активного проекта в реестре.  
При `switch-project` / `add-project` / `bootstrap` `mcp.json` перезаписывается; в открытом чате LM Studio переподключите MCP к файлу или начните новый чат.

5. LM Studio (вручную):
- Поднимите Local Server, загрузите модель.
- Новый чат -> Per-request MCP -> файл:
  `<путь_к_клону>\config\mcp\mcp.json`

6. Проекты кладите в `workspace\<имя_папки>\` (см. `README.md`).  
Активный проект (реестр): `scripts\switch-project.bat`  
Статус и LM Studio:

```powershell
python scripts\run_cli.py status
```

7. Новый чат / восстановление контекста:

```powershell
python scripts\run_cli.py brief
```

В консоли появится путь к `data\context\briefs\<проект>\latest.md` — вставьте содержимое в LM Studio или откройте файл через MCP.

Полный бриф:

```powershell
python scripts\run_cli.py brief --format full
```

Handoff:

```powershell
python scripts\run_cli.py brief --handoff
```

## Короткий сценарий с несколькими проектами

1. Запустите `terminal.bat`
2. Выберите пункт `3` и введите `test2`
3. Перейдите в LM Studio, создайте новый чат, подключите `config\mcp\mcp.json`
4. Работайте по проекту `test2`
5. Вернитесь в терминал, снова пункт `3`, введите `test1`
6. В LM Studio создайте НОВЫЙ чат и работайте уже по `test1`

Так вы переключаете контекст проекта без смешивания с предыдущим чатом.

## Примечание

Плагин LM Studio `project-filesystem` может подставлять неверный относительный путь; если `ENOENT` на `...\project-filesystem\workspace` — снова выполните `sync-mcp` (см. `config\mcp\README.md`).
