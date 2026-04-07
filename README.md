# xUdav

Сборка для **локальной** разработки с LLM: свой код и скрипты вокруг **LM Studio**, папка **`workspace/`** для новых и существующих проектов, отдельная память и реестр на диске — без облачного хостинга кода.

**Автор сборки:** xUdav (оркестрация, CLI, структура репозитория). Идеи и компоненты сторонних проектов перечислены ниже; их лицензии не заменяются этим файлом.

---

## Зачем

- Писать и править код **у себя на машине**, подключая к чату MCP (файлы, при необходимости shell — см. `config/mcp/`).
- Держать **несколько проектов** в `workspace/` с изолированным контекстом (`data/memory/projects/<имя>/`).
- Повторяемый минимум: правила в `rules/`, проверка API LM Studio, индексация/контекст через CLI.

---

## Преимущества

| | |
|--|--|
| Данные | Проекты и память у вас на диске, не на чужом сервере. |
| Модель | Любая совместимая с LM Studio, без привязки к одному вендору API. |
| Инструменты | Стандартные MCP-сервера (`npx`), расширяемо. |
| Простота | Один репозиторий: CLI + `workspace/` + конфиги MCP. |

---

## Структура (кратко)

| Путь | Назначение |
|------|------------|
| `src/local_ai_dev/` | Python: реестр проектов, bootstrap, статус LM Studio, индекс. |
| `src/local_ai_dev/gui/` | Опциональный пульт Tkinter (`scripts/gui_launcher.py`, `gui.bat`). |
| `scripts/` | Вход: `run_cli.py`, `*.bat` / `*.sh`. |
| `workspace/` | Ваши проекты (произвольные имена папок). |
| `data/context/registry.json` | Активный проект и пути. |
| `data/context/briefs/<имя>/` | Сгенерированные брифы для нового чата (`latest.md`, история, `brief-meta.json`; в git не коммитится). |
| `data/memory/projects/<имя>/` | summary, notes, index и т.д. |
| `rules/` | Правила для модели (глобальные, по языку, по проекту). |
| `config/mcp/` | Шаблон и сгенерированный `mcp.json` (в git не коммитится). |

---

## Установка (Windows)

Пошагово в **`инструкция.txt`**.

**Пульт (Tkinter, без терминала):** дважды щёлкните **`gui.bat`** в корне или выполните `python scripts\gui_launcher.py` — те же шаги (bootstrap, MCP, проект, бриф), статус LM Studio и лог команд.

Общие команды:

```text
python scripts\run_cli.py bootstrap
python scripts\run_cli.py sync-mcp
python scripts\run_cli.py status
python scripts\run_cli.py brief
python scripts\run_cli.py brief --format full
python scripts\run_cli.py brief --handoff
python scripts\run_cli.py --help
```

**Новая сессия в LM Studio:** после `index-project` / `rebuild-context` (если код менялся) выполните `brief`, откройте напечатанный путь `data\context\briefs\<проект>\latest.md` — вставьте в чат или попросите модель прочитать этот файл через MCP. `--handoff` — шаблон «передачи смены»; `--no-history` — не писать копию с timestamp.

MCP под машину и **активный проект** (корень файлов и shell = `workspace/<имя>` из реестра):

```text
python scripts\run_cli.py sync-mcp
```

То же: `powershell -ExecutionPolicy Bypass -File scripts\sync-mcp.ps1`. Подробности — `config/mcp/README.md`.

LM Studio (сервер, модель, вложение `config\mcp\mcp.json` в чат) — **настраиваете вручную** в приложении.

---

## Сторонние компоненты (честные ссылки)

Сборка **не включает** бинарники LM Studio и модели — их ставите сами.

| Компонент | Зачем | Ссылка |
|-----------|--------|--------|
| LM Studio | Локальный сервер чата и API | https://lmstudio.ai/ |
| Model Context Protocol | Протокол инструментов | https://modelcontextprotocol.io |
| `@modelcontextprotocol/server-filesystem` | MCP: доступ к файлам | https://www.npmjs.com/package/@modelcontextprotocol/server-filesystem |
| `mcp-shell` | MCP: выполнение команд (осторожно, см. README пакета) | https://www.npmjs.com/package/mcp-shell |

Лицензии этих пакетов — у их авторов; при публикации форка сохраняйте их уведомления, если того требует их лицензия.

---

## Лицензия

Код и документы **в этом репозитории** (оригинальные файлы xUdav): **MIT**, см. `LICENSE`.

Поле `name` в `pyproject.toml`: `local-ai-dev-system` — техническое имя пакета; продукт в документации — **xUdav**.
