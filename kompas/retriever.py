"""Поиск по проверенной базе знаний (BM25 по символьным n-граммам).

Символьные n-граммы одинаково работают для русского, английского и китайского без токенизаторов
и внешних моделей — демо запускается офлайн за секунды.
В пилоте заменяется на мультиязычные эмбеддинги BAAI/bge-m3 + Qdrant в контуре банка (интерфейс тот же).
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import yaml

DATA = Path(__file__).parent / "data"


def load_cards() -> list[dict]:
    return yaml.safe_load((DATA / "kb.yaml").read_text(encoding="utf-8"))["cards"]


def _norm(text: str) -> str:
    text = text.lower().replace("ё", "е")
    return re.sub(r"[^\w一-鿿]+", " ", text)


def ngrams(text: str) -> list[str]:
    grams: list[str] = []
    for word in _norm(text).split():
        if re.search(r"[一-鿿]", word):
            grams += [word[i:i + 2] for i in range(len(word) - 1)] or [word]
        else:
            w = f" {word} "
            grams += [w[i:i + 4] for i in range(max(1, len(w) - 3))]
    return grams


@dataclass
class Hit:
    card: dict
    score: float


class Retriever:
    def __init__(self, cards: list[dict] | None = None, k1: float = 1.5, b: float = 0.75):
        self.cards = cards or load_cards()
        self.k1, self.b = k1, b
        self.docs = [Counter(ngrams(self._doc_text(c))) for c in self.cards]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lens) / len(self.lens)
        df: Counter = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    @staticmethod
    def _doc_text(c: dict) -> str:
        # Ключевые слова весят втрое больше основного текста
        return " ".join([c.get("keywords", "")] * 3 + [c.get("ru", ""), c.get("en", ""), c.get("zh", "")])

    def search(self, query: str, k: int = 3) -> list[Hit]:
        q = Counter(ngrams(query))
        if not q:
            return []
        hits = []
        for card, d, ln in zip(self.cards, self.docs, self.lens):
            s = 0.0
            for t in q:
                if t in d:
                    tf = d[t]
                    s += self.idf[t] * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * ln / self.avg))
            # нормируем на длину запроса, чтобы порог не зависел от длины вопроса
            hits.append(Hit(card, s / math.sqrt(sum(q.values()))))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k]


def keyword_match(query: str, card: dict) -> bool:
    """Второй барьер от ложных срабатываний: в вопросе должно быть хотя бы одно ключевое слово карточки.
    Для кириллицы и латиницы сравниваем по основе (первые 5 букв), для китайского — вхождение слова."""
    q = _norm(query)
    q_words = q.split()
    for kw in card.get("keywords", "").split():
        kw = _norm(kw).strip()
        if not kw:
            continue
        if re.search(r"[\u4e00-\u9fff]", kw):
            if kw in q:
                return True
        else:
            stem = kw[:5]
            if any(w.startswith(stem) or (len(w) >= 4 and kw.startswith(w)) for w in q_words if len(w) >= 3):
                return True
    return False
