"""FastAPI entrypoint for the local AI agent server."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent import AgentService
from config import DEBUG, WORK_DIR
from schemas.chat import ChatRequest, ChatResponse
from tools.file_tools import ensure_workdir
from utils.logger import configure_logging, get_logger

logger = get_logger(__name__)
_agent_service = AgentService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    ensure_workdir()
    logger.info("starting ai-server | workdir=%s | debug=%s", WORK_DIR, DEBUG)
    yield
    logger.info("shutting down ai-server")


app = FastAPI(
    title="Local AI Agent Server",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS enabled for future React/HTML clients (tighten origins in production).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        return await _agent_service.agent.chat(req.message)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("unhandled /chat failure")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
