"""Движок сроков: строит персональный план «первые 30 дней».

Сроки считаются детерминированно по правилам из data/rules.yaml.
Языковая модель в расчёте сроков не участвует — это защита от «выдуманных» дедлайнов.
Дата въезда необязательна: без неё план строится как упорядоченный чек-лист (минимум персональных данных, 152-ФЗ).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import yaml

DATA = Path(__file__).parent / "data"
LANGS = ("ru", "en", "zh")


def load_rules() -> dict:
    return yaml.safe_load((DATA / "rules.yaml").read_text(encoding="utf-8"))


def add_business_days(start: date, n: int) -> date:
    d = start
    added = 0
    while added < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            added += 1
    return d


@dataclass
class PlanStep:
    id: str
    order: int
    title: str
    hint: str
    kind: str  # legal | recommended
    days: int
    due: Optional[str]  # ISO date or None when entry date is not given
    source: str
    kb: str


def _group_of(country: str, groups: dict) -> Optional[str]:
    for name, members in groups.items():
        if country in members:
            return name
    return None


def build_plan(country: str = "", entry_date: Optional[date] = None, lang: str = "ru") -> list[PlanStep]:
    """country — ISO-код страны (CN, KZ, BY…); entry_date — дата въезда или None."""
    if lang not in LANGS:
        lang = "en"
    rules = load_rules()
    country = (country or "").upper()
    group = _group_of(country, rules.get("groups", {}))
    steps: list[PlanStep] = []
    for r in rules["steps"]:
        if country and country in r.get("skip_for", []):
            continue
        days = r["days"]
        if group and group in r.get("days_by_group", {}):
            days = r["days_by_group"][group]
        due = None
        if entry_date:
            if r.get("business_days") and not (group and group in r.get("days_by_group", {})):
                due = add_business_days(entry_date, days).isoformat()
            else:
                due = (entry_date + timedelta(days=days)).isoformat()
        steps.append(PlanStep(
            id=r["id"], order=r["order"], title=r["title"][lang], hint=r["hint"][lang],
            kind=r["kind"], days=days, due=due, source=r["source"], kb=r["kb"],
        ))
    # Сортировка: по сроку, если он известен, иначе по порядку
    steps.sort(key=lambda s: (s.due or "", s.order) if entry_date else (s.order,))
    return steps


def plan_as_dicts(*args, **kwargs) -> list[dict]:
    return [asdict(s) for s in build_plan(*args, **kwargs)]
