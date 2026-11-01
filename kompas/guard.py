"""Ограничители: маскирование персональных данных и запрещённые темы.

1. Перед отправкой вопроса в языковую модель номера паспортов, карт, телефоны и почта маскируются (152-ФЗ).
   В пилоте дополняется NER (natasha / microsoft presidio) для ФИО и адресов.
2. Вопросы об обходе проверок банка и валютного контроля не обрабатываются моделью —
   помощник отвечает фиксированным текстом (115-ФЗ, 173-ФЗ).
"""
from __future__ import annotations

import re

PII_PATTERNS = [
    ("CARD", re.compile(r"\b(?:\d[ -]?){15,18}\d\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")),
    ("PASSPORT", re.compile(r"\b(?:[A-Z]{1,2}\d{7,8}|\d{2}\s?\d{2}\s?\d{6})\b")),
    ("PHONE", re.compile(r"(?<!\w)\+?\d[\d\s()-]{9,15}\d\b")),
]

FORBIDDEN = re.compile(
    r"обойти|обход|обхитр|дробить|раздробить|обнал|не попасть под|чтобы банк не|скрыть от банка|фиктивн|"
    r"bypass|evade|avoid (?:the )?(?:check|control|aml)|split (?:the )?transfer|structur(?:e|ing)|hide from (?:the )?bank|"
    r"绕过|规避|拆分转账|逃避|隐瞒银行",
    re.IGNORECASE,
)

REFUSAL = {
    "ru": "Я не подсказываю способы обойти проверки банка или валютный контроль: это нарушает закон и может привести к блокировке счёта. "
          "Могу объяснить, почему перевод задержали, и какие документы помогут пройти проверку законно.",
    "en": "I can't help with bypassing bank checks or currency control: it breaks the law and can get your account blocked. "
          "I can explain why a transfer was delayed and which documents help you pass the check legally.",
    "zh": "我无法提供规避银行审查或外汇管制的方法：这违反法律，并可能导致账户被冻结。我可以解释汇款被延迟的原因，以及哪些文件能帮助您合法通过审查。",
}


def mask_pii(text: str) -> tuple[str, list[str]]:
    found: list[str] = []
    for label, rx in PII_PATTERNS:
        if rx.search(text):
            found.append(label)
            text = rx.sub(f"[{label}]", text)
    return text, found


def is_forbidden(text: str) -> bool:
    return bool(FORBIDDEN.search(text))
