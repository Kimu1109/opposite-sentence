"""FastAPI起点。ルーティングと静的配信。"""

import logging
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from . import config
from .antonyms import AntonymDict, WordNet
from .pipeline import Resources, invert
from .schemas import HealthResponse, InvertRequest, InvertResponse
from .vectors import VectorIndex

logging.basicConfig(level=logging.INFO)


def load_resources() -> Resources:
    antonyms = AntonymDict.load(config.ANTONYMS_CSV)
    return Resources(
        antonyms=antonyms,
        wordnet=WordNet.load(config.WORDNET_DB),
        vectors=VectorIndex.load(config.VECTORS_PATH, antonyms.pairs),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not hasattr(app.state, "resources"):
        app.state.resources = load_resources()
    yield


app = FastAPI(title="対義文ジェネレーター", lifespan=lifespan)


@app.post("/api/invert", response_model=InvertResponse)
def api_invert(req: InvertRequest, request: Request) -> InvertResponse:
    result = invert(req.text, request.app.state.resources, mode=req.mode, seed=req.seed)
    return InvertResponse.model_validate(asdict(result))


@app.get("/api/health", response_model=HealthResponse)
def api_health(request: Request) -> HealthResponse:
    res: Resources = request.app.state.resources
    return HealthResponse(
        antonym_pairs=len(res.antonyms.pairs),
        wordnet_loaded=res.wordnet is not None,
        vectors_loaded=res.vectors is not None,
    )


app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
