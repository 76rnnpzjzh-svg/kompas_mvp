"""HTTP API и веб-интерфейс.  Запуск: uvicorn kompas.api:app --reload"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .assistant import ask_dict
from .plan import plan_as_dicts

WEB = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Kompas API", version="0.1.0")


class PlanRequest(BaseModel):
    country: str = Field("", description="ISO-код страны: CN, KZ, UZ…")
    entry_date: Optional[date] = Field(None, description="Дата въезда — необязательно")
    lang: str = "ru"


class AskRequest(BaseModel):
    question: str = Field(..., max_length=1000)
    lang: Optional[str] = None


@app.post("/api/plan")
def plan(req: PlanRequest):
    return {"steps": plan_as_dicts(req.country, req.entry_date, req.lang)}


@app.post("/api/ask")
def ask(req: AskRequest):
    return ask_dict(req.question, req.lang)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/", StaticFiles(directory=WEB), name="web")
