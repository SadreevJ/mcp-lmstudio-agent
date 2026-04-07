from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class LmStudioStatus:
    reachable: bool
    message: str
    models: list[str]


def check_lmstudio(base_url: str, api_key: str | None) -> LmStudioStatus:
    url = f"{base_url.rstrip('/')}/v1/models"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            body = response.read().decode("utf-8", errors="replace")
            payload: dict[str, Any] = json.loads(body)
            models = [item.get("id", "<unknown>") for item in payload.get("data", [])]
            if not models:
                return LmStudioStatus(
                    reachable=True,
                    message="LM Studio доступен, но моделей не обнаружено (возможно, модель не загружена).",
                    models=[],
                )
            return LmStudioStatus(reachable=True, message="LM Studio доступен.", models=models)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            return LmStudioStatus(
                reachable=False,
                message="LM Studio ответил 401 Unauthorized. Проверьте LMSTUDIO_API_KEY в .env.",
                models=[],
            )
        return LmStudioStatus(reachable=False, message=f"LM Studio HTTP ошибка: {exc.code}.", models=[])
    except Exception as exc:
        return LmStudioStatus(
            reachable=False,
            message=f"LM Studio недоступен по адресу {base_url}: {exc}.",
            models=[],
        )
