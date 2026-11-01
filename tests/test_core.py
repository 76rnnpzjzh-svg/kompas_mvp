from datetime import date

from fastapi.testclient import TestClient

from kompas.api import app
from kompas.assistant import ask, detect_lang
from kompas.guard import mask_pii, is_forbidden
from kompas.plan import build_plan, add_business_days


def test_business_days_skip_weekend():
    # пятница + 1 рабочий день = понедельник
    assert add_business_days(date(2026, 9, 4), 1) == date(2026, 9, 7)


def test_plan_with_date_has_due_dates():
    steps = build_plan("CN", date(2026, 9, 1), "ru")
    med = next(s for s in steps if s.id == "medical_exam")
    assert med.due == "2026-10-01" and med.kind == "legal"
    reg = next(s for s in steps if s.id == "migration_registration")
    assert reg.due == "2026-09-10"  # 7 рабочих дней


def test_plan_without_date_is_ordered_checklist():
    steps = build_plan("CN", None, "en")
    assert all(s.due is None for s in steps)
    assert [s.order for s in steps] == sorted(s.order for s in steps)


def test_eaeu_registration_30_days_and_belarus_skips_medical():
    kz = {s.id: s for s in build_plan("KZ", date(2026, 9, 1))}
    assert kz["migration_registration"].due == "2026-10-01"
    by = {s.id for s in build_plan("BY", date(2026, 9, 1))}
    assert "medical_exam" not in by


def test_pii_is_masked():
    text, found = mask_pii("паспорт 1234 567890, тел +7 000 000 00 00, E12345678")
    assert "567890" not in text and "000 00 00" not in text and "E12345678" not in text
    assert {"PASSPORT", "PHONE"} <= set(found)


def test_forbidden_topics():
    assert is_forbidden("как раздробить перевод")
    assert is_forbidden("how to bypass currency control")
    assert not is_forbidden("почему задержали перевод")


def test_answers_have_sources_and_language():
    a = ask("我的转账被冻结了怎么办")
    assert a.lang == "zh" and a.card_id == "transfer_from_home" and a.sources


def test_unknown_question_goes_to_human():
    assert ask("где купить зимнюю куртку").handoff


def test_detect_lang():
    assert detect_lang("привет") == "ru" and detect_lang("hello") == "en" and detect_lang("你好") == "zh"


def test_api():
    c = TestClient(app)
    r = c.post("/api/plan", json={"country": "CN", "entry_date": "2026-09-01", "lang": "zh"})
    assert r.status_code == 200 and len(r.json()["steps"]) >= 5
    r = c.post("/api/ask", json={"question": "нужен ли СНИЛС"})
    assert r.json()["card_id"] == "snils"
