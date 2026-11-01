"""Адаптеры языковых моделей.

KOMPAS_LLM=extractive (по умолчанию) — без модели: ответ собирается из проверенной карточки. Работает без ключей.
KOMPAS_LLM=gigachat — GigaChat API (российская модель). Нужна переменная GIGACHAT_CREDENTIALS.
KOMPAS_LLM=openai_compatible — любая модель в контуре банка через OpenAI-совместимый API:
    vLLM, Ollama (http://localhost:11434/v1), открытые веса GigaChat / Qwen. Переменные LLM_BASE_URL, LLM_MODEL, LLM_API_KEY (необязательно).

Ключи читаются ТОЛЬКО из переменных окружения (.env не коммитится, см. .gitignore).
"""
from __future__ import annotations

import os
import uuid

import httpx

SYSTEM_PROMPT = (
    "Ты — Компас, помощник иностранного студента в России. Отвечай на языке вопроса ({lang}), кратко и простыми словами. "
    "Используй ТОЛЬКО факты из блока КОНТЕКСТ. Если ответа в контексте нет — скажи, что передашь вопрос сотруднику. "
    "Не давай советов, как обойти проверки банка или законы. Не придумывай сроки и суммы."
)


class LLMError(RuntimeError):
    pass


def provider() -> str:
    return os.getenv("KOMPAS_LLM", "extractive").lower()


def _messages(question: str, context: str, lang: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT.format(lang=lang)},
        {"role": "user", "content": f"КОНТЕКСТ:\n{context}\n\nВОПРОС: {question}"},
    ]


def _gigachat(question: str, context: str, lang: str) -> str:
    creds = os.getenv("GIGACHAT_CREDENTIALS")
    if not creds:
        raise LLMError("GIGACHAT_CREDENTIALS is not set")
    verify = os.getenv("GIGACHAT_CA_BUNDLE", True)  # путь к сертификату НУЦ Минцифры
    scope = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
    with httpx.Client(verify=verify, timeout=30) as c:
        tok = c.post(
            "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            headers={"Authorization": f"Basic {creds}", "RqUID": str(uuid.uuid4()),
                     "Content-Type": "application/x-www-form-urlencoded"},
            data={"scope": scope},
        ).raise_for_status().json()["access_token"]
        r = c.post(
            "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {tok}"},
            json={"model": os.getenv("GIGACHAT_MODEL", "GigaChat"), "temperature": 0.1,
                  "messages": _messages(question, context, lang)},
        ).raise_for_status().json()
    return r["choices"][0]["message"]["content"]


def _openai_compatible(question: str, context: str, lang: str) -> str:
    base = os.getenv("LLM_BASE_URL")
    if not base:
        raise LLMError("LLM_BASE_URL is not set")
    headers = {}
    if os.getenv("LLM_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['LLM_API_KEY']}"
    r = httpx.post(
        base.rstrip("/") + "/chat/completions", headers=headers, timeout=60,
        json={"model": os.getenv("LLM_MODEL", "qwen3:8b"), "temperature": 0.1,
              "messages": _messages(question, context, lang)},
    ).raise_for_status().json()
    return r["choices"][0]["message"]["content"]


def generate(question: str, context: str, lang: str) -> str | None:
    """Возвращает текст модели или None для экстрактивного режима."""
    p = provider()
    if p == "gigachat":
        return _gigachat(question, context, lang)
    if p == "openai_compatible":
        return _openai_compatible(question, context, lang)
    return None
