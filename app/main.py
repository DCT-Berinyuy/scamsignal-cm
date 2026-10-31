"""FastAPI app: POST /check, GET /health (PRD §8.2). Nothing is stored; request bodies are never logged."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.advice import AdviceBook, default_advice
from app.combine import Label, ModelVote, combine
from app.config import APP_NAME, LANGS, MAX_TEXT_LEN, SENDER_TYPES
from app.rules import RuleSet, default_rules

logger = logging.getLogger("scamsignal")

INVALID_INPUT = {"error": "invalid input"}
INTERNAL_ERROR = {"error": "internal error"}


class CheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=MAX_TEXT_LEN)
    lang: str
    sender_type: str

    @field_validator("text")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("blank text")
        return value

    @field_validator("lang")
    @classmethod
    def _known_lang(cls, value: str) -> str:
        if value not in LANGS:
            raise ValueError("unknown lang")
        return value

    @field_validator("sender_type")
    @classmethod
    def _known_sender(cls, value: str) -> str:
        if value not in SENDER_TYPES:
            raise ValueError("unknown sender_type")
        return value


class RuleHitOut(BaseModel):
    id: str
    severity: Literal["hard", "soft"]


class CheckResponse(BaseModel):
    label: Label
    reasons: list[str]
    rule_hits: list[RuleHitOut]
    why: str
    advice: str
    model_used: bool
    lang: str


def analyze(req: CheckRequest, rules: RuleSet, advice: AdviceBook) -> CheckResponse:
    """text → rules → (model, step 5) → combine. Pure function, reused by eval/eval.py."""
    hits = rules.check(req.text, req.sender_type)
    vote: ModelVote | None = None
    reasons = rules.reasons(hits, req.lang)
    return CheckResponse(
        label=combine(hits, vote),
        reasons=reasons,
        rule_hits=[RuleHitOut(id=h.id, severity=h.severity.value) for h in hits],
        why=advice.why_template(reasons, bool(hits), req.lang),
        advice=advice.advice(hits, req.lang),
        model_used=False,
        lang=req.lang,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Fail fast at startup if rules.json or advice.json is malformed.
    app.state.rules = default_rules()
    app.state.advice = default_advice()
    app.state.model_loaded = False
    yield


app = FastAPI(title=APP_NAME, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.exception_handler(RequestValidationError)
async def _invalid_input(_: Request, __: RequestValidationError) -> JSONResponse:
    # FastAPI's default handler echoes the submitted input; ours never does.
    return JSONResponse(status_code=422, content=INVALID_INPUT)


@app.middleware("http")
async def _contain_errors(request: Request, call_next):
    # Catch here, not with exception_handler(Exception): Starlette re-raises from that handler so the
    # server logs a traceback, and exception messages may contain the submitted text.
    try:
        return await call_next(request)
    except Exception as exc:
        logger.error("unhandled error: %s", type(exc).__name__)
        return JSONResponse(status_code=500, content=INTERNAL_ERROR)


@app.get("/health")
def health(request: Request) -> dict:
    return {"status": "ok", "model_loaded": request.app.state.model_loaded, "app_name": APP_NAME}


@app.post("/check", response_model=CheckResponse)
def check(req: CheckRequest, request: Request) -> CheckResponse:
    return analyze(req, request.app.state.rules, request.app.state.advice)
