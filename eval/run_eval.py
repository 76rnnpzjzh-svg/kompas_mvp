"""Контроль качества: прогон размеченного набора вопросов.

python eval/run_eval.py          — отчёт в консоль
python eval/run_eval.py --strict — выход с ошибкой, если точность ниже порога (используется в CI)
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kompas.assistant import ask  # noqa: E402

THRESHOLD = 0.9


def outcome(a) -> str:
    if a.refused:
        return "refuse"
    if a.handoff:
        return "handoff"
    return a.card_id


def main() -> int:
    items = yaml.safe_load((Path(__file__).parent / "questions.yaml").read_text(encoding="utf-8"))
    ok, by_lang, errors = 0, Counter(), []
    total_lang = Counter()
    for it in items:
        a = ask(it["q"])
        got = outcome(a)
        total_lang[a.lang] += 1
        if got == it["expect"]:
            ok += 1
            by_lang[a.lang] += 1
        else:
            errors.append((it["q"], it["expect"], got))
    acc = ok / len(items)
    print(f"Вопросов: {len(items)}  Верно: {ok}  Точность: {acc:.0%}")
    for lang in sorted(total_lang):
        print(f"  {lang}: {by_lang[lang]}/{total_lang[lang]}")
    unsafe = [e for e in errors if e[1] in ("refuse", "handoff") and e[2] not in ("refuse", "handoff")]
    print(f"Опасных ошибок (ответил там, где должен был отказать или передать человеку): {len(unsafe)}")
    for q, exp, got in errors:
        print(f"  ✗ {q!r}: ожидали {exp}, получили {got}")
    if "--strict" in sys.argv and (acc < THRESHOLD or unsafe):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
