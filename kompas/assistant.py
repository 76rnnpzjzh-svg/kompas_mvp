"""Ответ на вопрос студента: ограничители → поиск по базе → (модель) → ответ со ссылкой или передача человеку."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, asdict

from . import guard, llm
from .retriever import Retriever, keyword_match

log = logging.getLogger("kompas")

# Ниже этого порога считаем, что в базе нет ответа, и передаём вопрос человеку.
MIN_SCORE = 0.8

HANDOFF = {
    "ru": "В проверенной базе пока нет точного ответа. Передаю вопрос сотруднику международного отдела вуза — ответ придёт сюда же.",
    "en": "There is no verified answer in my knowledge base yet. I'm forwarding your question to the university international office — the reply will come here.",
    "zh": "知识库中暂无经过核实的答案。我会将您的问题转交给大学国际处的工作人员——回复将发送到这里。",
}
SOURCE_LABEL = {"ru": "Источник", "en": "Source", "zh": "来源"}

_retriever: Retriever | None = None


def retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def detect_lang(text: str) -> str:
    if re.search(r"[一-鿿]", text):
        return "zh"
    if re.search(r"[а-яё]", text, re.IGNORECASE):
        return "ru"
    return "en"


@dataclass
class Answer:
    text: str
    lang: str
    sources: list[str] = field(default_factory=list)
    card_id: str | None = None
    handoff: bool = False
    refused: bool = False
    pii_masked: list[str] = field(default_factory=list)
    mode: str = "extractive"


def ask(question: str, lang: str | None = None) -> Answer:
    lang = lang or detect_lang(question)
    masked, pii = guard.mask_pii(question)

    if guard.is_forbidden(masked):
        return Answer(guard.REFUSAL[lang], lang, refused=True, pii_masked=pii, mode="guard")

    hits = [h for h in retriever().search(masked, k=3)
            if h.score >= MIN_SCORE and keyword_match(masked, h.card)]
    if not hits:
        return Answer(HANDOFF[lang], lang, handoff=True, pii_masked=pii, mode="handoff")

    card = hits[0].card
    mode = llm.provider()
    text = card[lang]
    try:
        generated = llm.generate(masked, f"{card[lang]}\n({SOURCE_LABEL[lang]}: {card['source']})", lang)
        if generated:
            text = generated
    except Exception as e:  # модель недоступна — отвечаем проверенной карточкой
        log.warning("LLM failed, falling back to extractive answer: %s", e)
        mode = "extractive"
    return Answer(text, lang, sources=[card["source"]], card_id=card["id"], pii_masked=pii, mode=mode)


def ask_dict(question: str, lang: str | None = None) -> dict:
    return asdict(ask(question, lang))
