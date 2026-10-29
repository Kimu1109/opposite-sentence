"""リクエスト/レスポンスの型。"""

from typing import Literal

from pydantic import BaseModel, Field

from . import config

Mode = Literal["dict", "vector", "mix"]
Method = Literal["csv", "wordnet", "vector", "negate", "keep"]


class InvertRequest(BaseModel):
    text: str = Field(min_length=1, max_length=config.MAX_TEXT_LENGTH)
    mode: Mode = config.DEFAULT_MODE
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)


class TokenOut(BaseModel):
    surface: str
    lemma: str
    pos: str
    replaced: str
    method: Method
    score: float | None = None


class InvertResponse(BaseModel):
    result: str
    mode: Mode
    seed: int
    tokens: list[TokenOut]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    antonym_pairs: int
    wordnet_loaded: bool
    vectors_loaded: bool
