from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
from typing import Callable

from local_ai_dev.infrastructure.env import load_env_file
from local_ai_dev.infrastructure.lmstudio import LmStudioStatus, check_lmstudio
from local_ai_dev.infrastructure.paths import get_paths


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


class ControlPanel:
    LM_REFRESH_MS = 12_000

    def __init__(self) -> None:
        self.paths = get_paths()
        self.root = tk.Tk()
        self.root.title("xUdav — пульт")
        self.root.minsize(720, 640)
        self._lm_refresh_job: str | None = None
        self._step_done = {2: tk.StringVar(value=""), 3: tk.StringVar(value="")}
        self._last_brief_path: Path | None = None

        self._build_ui()
        self.refresh_lm_status()
        self._schedule_lm_refresh()

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill=tk.X)

        ttk.Label(top, text="xUdav — пульт управления", font=("", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(
            top,
            text=f"Корень: {self.paths.root}",
            font=("", 9),
        ).pack(anchor=tk.W)

        lm = ttk.LabelFrame(self.root, text="LM Studio (API)", padding=8)
        lm.pack(fill=tk.X, padx=8, pady=4)

        self._lm_title = ttk.Label(lm, text="Проверка…", font=("", 11, "bold"))
        self._lm_title.pack(anchor=tk.W)
        self._lm_detail = ttk.Label(lm, text="", wraplength=680)
        self._lm_detail.pack(anchor=tk.W, pady=(4, 0))

        row = ttk.Frame(lm)
        row.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(row, text="Проверить сейчас", command=self.refresh_lm_status).pack(side=tk.LEFT)

        guide = ttk.LabelFrame(self.root, text="Шаги (сверху вниз)", padding=8)
        guide.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        ttk.Label(
            guide,
            text=(
                "Шаги 1–3 обычно один раз после установки. Корень MCP (файлы и shell) = папка активного проекта "
                "(шаг 4); после смены проекта снова шаг 3 или переподключите MCP в LM Studio. "
                "Перед работой смотрите статус LM Studio выше. Перед новым чатом — шаг 6 (бриф)."
            ),
            wraplength=680,
        ).pack(anchor=tk.W, pady=(0, 8))

        canvas = tk.Canvas(guide, highlightthickness=0)
        scroll = ttk.Scrollbar(guide, orient=tk.VERTICAL, command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor=tk.NW)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_mousewheel(event: tk.Event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._build_step(inner, 1, "Окружение (.env)", self._step1_env)
        self._build_step(inner, 2, "Bootstrap (папки и реестр)", self._step2_bootstrap)
        self._build_step(inner, 3, "Конфиг MCP (активный проект)", self._step3_sync_mcp)
        self._build_step(inner, 4, "Активный проект", self._step4_project)
        self._build_step(inner, 5, "Обновить индекс / контекст", self._step5_index)
        self._build_step(inner, 6, "Бриф для нового чата", self._step6_brief)

        log_fr = ttk.LabelFrame(self.root, text="Лог команд", padding=6)
        log_fr.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        self._log = scrolledtext.ScrolledText(log_fr, height=10, wrap=tk.WORD, font=("Consolas", 9))
        self._log.pack(fill=tk.BOTH, expand=True)
        self._reload_projects_combo()

    def _build_step(self, parent: ttk.Frame, num: int, title: str, body: Callable[[ttk.Frame], None]) -> None:
        lf = ttk.LabelFrame(parent, text=f"Шаг {num}. {title}", padding=8)
        lf.pack(fill=tk.X, pady=4)
        body(lf)
        if num in (2, 3):
            ttk.Label(lf, textvariable=self._step_done[num], foreground="green").pack(anchor=tk.W, pady=(4, 0))

    def _step1_env(self, lf: ttk.Frame) -> None:
        ttk.Label(
            lf,
            text="Нужен файл .env в корне (ключ API LM Studio при включённой авторизации).",
            wraplength=650,
        ).pack(anchor=tk.W)
        row = ttk.Frame(lf)
        row.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(row, text="Создать .env из примера", command=self._copy_env_example).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(row, text="Открыть папку корня", command=self._open_root_folder).pack(side=tk.LEFT)

    def _step2_bootstrap(self, lf: ttk.Frame) -> None:
        ttk.Label(lf, text="Создаёт workspace, data, синхронизирует реестр с папками.", wraplength=650).pack(
            anchor=tk.W
        )
        ttk.Button(lf, text="Выполнить bootstrap", command=lambda: self._run_cli(["bootstrap"], step_on_ok=2)).pack(
            anchor=tk.W, pady=(6, 0)
        )

    def _step3_sync_mcp(self, lf: ttk.Frame) -> None:
        ttk.Label(
            lf,
            text=(
                "Пишет config/mcp/mcp.json: разрешённая папка файлов и cwd shell = каталог активного проекта "
                "(см. шаг 4). В LM Studio в чате укажите этот файл в Per-request MCP."
            ),
            wraplength=650,
        ).pack(anchor=tk.W)
        row = ttk.Frame(lf)
        row.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(row, text="Синхронизировать MCP", command=self._run_sync_mcp).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(row, text="Копировать путь к mcp.json", command=self._copy_mcp_path).pack(side=tk.LEFT)

    def _step4_project(self, lf: ttk.Frame) -> None:
        ttk.Label(
            lf,
            text=(
                "Активный проект в реестре: workspace/<имя>. Имя контекста, индекс и MCP привязаны к этой папке — "
                "переключили проект → снова «Синхронизировать MCP» или переподключите MCP в чате."
            ),
            wraplength=650,
        ).pack(anchor=tk.W)
        row = ttk.Frame(lf)
        row.pack(fill=tk.X, pady=(6, 0))
        self._project_combo = ttk.Combobox(row, width=32, state="readonly")
        self._project_combo.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(row, text="Обновить список", command=self._reload_projects_combo).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(row, text="Сделать активным", command=self._switch_project).pack(side=tk.LEFT)

    def _step5_index(self, lf: ttk.Frame) -> None:
        ttk.Label(lf, text="После больших изменений в коде проекта.", wraplength=650).pack(anchor=tk.W)
        ttk.Button(
            lf, text="Пересобрать контекст (rebuild-context)", command=lambda: self._run_cli(["rebuild-context"])
        ).pack(anchor=tk.W, pady=(6, 0))

    def _step6_brief(self, lf: ttk.Frame) -> None:
        ttk.Label(
            lf,
            text="Собирает markdown для вставки в новый чат или для чтения через MCP.",
            wraplength=650,
        ).pack(anchor=tk.W)
        row = ttk.Frame(lf)
        row.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(row, text="Бриф (краткий)", command=lambda: self._run_brief([])).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            row,
            text="Бриф (полный)",
            command=lambda: self._run_brief(["--format", "full"]),
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(row, text="Handoff", command=lambda: self._run_brief(["--handoff"])).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(row, text="Копировать путь latest.md", command=self._copy_brief_path).pack(side=tk.LEFT)

    def _log_line(self, text: str) -> None:
        if not hasattr(self, "_log"):
            return
        self._log.insert(tk.END, f"[{_now()}] {text}\n")
        self._log.see(tk.END)

    def _copy_env_example(self) -> None:
        src = self.paths.root / ".env.example"
        dst = self.paths.root / ".env"
        if not src.is_file():
            messagebox.showerror("Ошибка", f"Нет файла {src}")
            return
        if dst.exists():
            if not messagebox.askyesno("Замена", ".env уже есть. Перезаписать из примера?"):
                return
        shutil.copy(src, dst)
        load_env_file(dst)
        self._log_line(f"Скопировано: {dst}")
        messagebox.showinfo("Готово", "Проверьте .env и при необходимости укажите LMSTUDIO_API_KEY.")

    def _open_root_folder(self) -> None:
        os.startfile(self.paths.root)

    def _copy_mcp_path(self) -> None:
        p = self.paths.root / "config" / "mcp" / "mcp.json"
        text = str(p.resolve()) if p.is_file() else str((self.paths.root / "config" / "mcp" / "mcp.json").resolve())
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._log_line(f"В буфер: {text}")
        messagebox.showinfo("Буфер", "Путь к mcp.json скопирован.")

    def _copy_brief_path(self) -> None:
        if not self._last_brief_path or not self._last_brief_path.is_file():
            messagebox.showwarning("Нет файла", "Сначала нажмите один из вариантов брифа.")
            return
        text = str(self._last_brief_path.resolve())
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._log_line(f"В буфер: {text}")
        messagebox.showinfo("Буфер", "Путь к latest.md скопирован.")

    def _reload_projects_combo(self) -> None:
        names: list[str] = []
        active = ""
        if self.paths.state.is_file():
            try:
                data = json.loads(self.paths.state.read_text(encoding="utf-8"))
                active = data.get("active_project") or ""
                names = sorted((data.get("projects") or {}).keys())
            except (json.JSONDecodeError, OSError):
                pass
        self._project_combo["values"] = names
        if active in names:
            self._project_combo.set(active)
        elif names:
            self._project_combo.set(names[0])
        self._log_line(f"Проекты в реестре: {', '.join(names) or '(пусто)'}")

    def _switch_project(self) -> None:
        name = self._project_combo.get().strip()
        if not name:
            messagebox.showwarning("Проект", "Выберите проект из списка.")
            return
        self._run_cli(["switch-project", name])

    def _run_sync_mcp(self) -> None:
        self._run_cli(["sync-mcp"], step_on_ok=3)

    def _run_cli(self, args: list[str], step_on_ok: int | None = None) -> None:
        if args == ["bootstrap"]:
            env_path = self.paths.root / ".env"
            if not env_path.is_file():
                if not messagebox.askyesno(
                    "Нет .env",
                    ".env не найден. Продолжить bootstrap? (Лучше сначала шаг 1.)",
                ):
                    return

        script = self.paths.root / "scripts" / "run_cli.py"
        cmd = [sys.executable, str(script), *args]

        def work() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                cmd,
                cwd=self.paths.root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )

        def done(cp: subprocess.CompletedProcess[str]) -> None:
            out = (cp.stdout or "") + (cp.stderr or "")
            self._log_line(f"{' '.join(args)} exit={cp.returncode}\n{out.strip()}")
            if cp.returncode == 0 and step_on_ok is not None:
                self._step_done[step_on_ok].set("В этой сессии: выполнено")
            if args == ["sync-mcp"]:
                if cp.returncode == 0:
                    messagebox.showinfo(
                        "MCP",
                        "mcp.json обновлён под активный проект.\n"
                        "В LM Studio переподключите MCP к этому файлу или откройте новый чат.",
                    )
                else:
                    messagebox.showerror("sync-mcp", (out.strip() or f"Код выхода {cp.returncode}")[:2000])
            if args and args[0] == "switch-project" and cp.returncode == 0:
                self._reload_projects_combo()
                messagebox.showinfo(
                    "Проект",
                    "Активный проект сохранён; mcp.json перезаписан под папку этого проекта.\n"
                    "В LM Studio переподключите MCP к config/mcp/mcp.json или откройте новый чат.",
                )

        self._run_in_thread(work, done)

    def _run_brief(self, extra: list[str]) -> None:
        script = self.paths.root / "scripts" / "run_cli.py"
        cmd = [sys.executable, str(script), "brief", *extra]

        def work() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                cmd,
                cwd=self.paths.root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )

        def done(cp: subprocess.CompletedProcess[str]) -> None:
            out = (cp.stdout or "") + (cp.stderr or "")
            self._log_line(f"brief exit={cp.returncode}\n{out.strip()}")
            if cp.returncode == 0 and cp.stdout:
                first = cp.stdout.strip().splitlines()[0].strip()
                p = Path(first)
                if p.is_file():
                    self._last_brief_path = p
                    messagebox.showinfo("Бриф", f"Файл:\n{p}")
                else:
                    messagebox.showinfo("Бриф", cp.stdout.strip())
            elif cp.returncode != 0:
                messagebox.showerror("Бриф", out.strip() or "Ошибка")

        self._run_in_thread(work, done)

    def _run_in_thread(
        self,
        work: Callable[[], subprocess.CompletedProcess[str]],
        done: Callable[[subprocess.CompletedProcess[str]], None],
    ) -> None:
        def target() -> None:
            try:
                cp = work()
            except (subprocess.TimeoutExpired, OSError) as exc:
                self.root.after(0, lambda: self._log_line(f"Ошибка subprocess: {exc}"))
                self.root.after(
                    0,
                    lambda: messagebox.showerror("Ошибка", str(exc)),
                )
                return
            self.root.after(0, lambda res=cp: done(res))

        threading.Thread(target=target, daemon=True).start()

    def _apply_lm_status(self, st: LmStudioStatus) -> None:
        if not st.reachable:
            title = "Офлайн — запустите LM Studio и Local Server"
            if "401" in st.message or "Unauthorized" in st.message:
                title = "Ошибка авторизации (401)"
            detail = st.message + "\nПодсказка: проверьте LMSTUDIO_API_KEY в .env и Local Server в LM Studio."
        elif not st.models:
            title = "Подключено (модели не загружены)"
            detail = st.message
        else:
            title = "Подключено"
            detail = st.message + f"\nМоделей в ответе: {len(st.models)}."
        self._lm_title.config(text=title)
        self._lm_detail.config(text=detail)

    def refresh_lm_status(self) -> None:
        root_path = self.paths.root

        def work() -> LmStudioStatus:
            load_env_file(root_path / ".env")
            base_url = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234")
            api_key = os.getenv("LMSTUDIO_API_KEY") or None
            return check_lmstudio(base_url=base_url, api_key=api_key)

        def thread_main() -> None:
            try:
                st = work()
            except Exception as exc:
                def fail() -> None:
                    self._lm_title.config(text="Ошибка проверки")
                    self._lm_detail.config(text=str(exc))

                self.root.after(0, fail)
                return
            self.root.after(0, lambda s=st: self._apply_lm_status(s))

        threading.Thread(target=thread_main, daemon=True).start()

    def _schedule_lm_refresh(self) -> None:
        def tick() -> None:
            self.refresh_lm_status()
            self._lm_refresh_job = self.root.after(self.LM_REFRESH_MS, tick)

        self._lm_refresh_job = self.root.after(self.LM_REFRESH_MS, tick)

    def run(self) -> None:
        self.root.mainloop()
