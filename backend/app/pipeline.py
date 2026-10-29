"""全体の組み立て。FastAPIに依存しない純粋関数にする。

分かち書き → 語ごとの対義語探索（CSV・WordNet・ベクトル・否定化・素通しの順）
→ 活用の復元 → 文の再構成。
"""

import random
from dataclasses import dataclass, field

from . import config
from .antonyms import AntonymDict, WordNet
from .inflect import inflect_word, negate, word_ctype
from .tokenizer import Token, tokenize
from .vectors import VectorIndex

# 対義語を探す対象の品詞
CONTENT_POS = {"名詞", "代名詞", "動詞", "形容詞", "形状詞", "副詞", "連体詞", "接続詞"}
# ベクトルで探す品詞。名詞は普通名詞だけ（固有名詞・数詞は素通し）
VECTOR_POS = {"動詞", "形容詞", "形状詞", "副詞", "名詞"}
# 否定化しない語（すでに否定の意味を持つ語）
_NO_NEGATE = {"ない", "無い"}

METHODS_FOR_MODE = {
    "dict": ("csv", "wordnet"),
    "vector": ("vector",),
    "mix": ("csv", "wordnet", "vector", "negate"),
}


@dataclass
class Resources:
    antonyms: AntonymDict
    wordnet: WordNet | None = None
    vectors: VectorIndex | None = None


@dataclass
class TokenTrace:
    surface: str
    lemma: str
    pos: str
    replaced: str
    method: str  # csv / wordnet / vector / negate / keep
    score: float | None = None


@dataclass
class InvertResult:
    result: str
    mode: str
    seed: int
    tokens: list[TokenTrace] = field(default_factory=list)


def _is_ta(t: Token | None) -> bool:
    """後ろに続く「た・だ（助動詞）」「て・で（接続助詞）」か。"""
    if t is None:
        return False
    if t.pos1 == "助動詞" and t.normalized == "た":
        return True
    return t.pos1 == "助詞" and t.pos2 == "接続助詞" and t.surface in ("て", "で")


def _voice(surface: str, voiced: bool) -> str:
    table = {"た": "だ", "て": "で"} if voiced else {"だ": "た", "で": "て"}
    return table.get(surface, surface)


def _pick(rng: random.Random, items: list):
    return items[0] if len(items) == 1 else rng.choice(items)


def _find(method: str, token: Token, res: Resources, mode: str, rng: random.Random):
    """方式 method で反意語（辞書形, スコア）を探す。見つからなければ None。"""
    if method == "csv":
        found = res.antonyms.lookup(token)
        return (_pick(rng, found), None) if found else None
    if method == "wordnet":
        if res.wordnet is None:
            return None
        found = [w for w in res.wordnet.lookup(token) if word_ctype(w)[0] == token.pos1]
        return (_pick(rng, found), None) if found else None
    if method == "vector":
        if res.vectors is None or token.pos1 not in VECTOR_POS:
            return None
        if token.pos1 == "名詞" and token.pos2 != "普通名詞":
            return None
        vec_method = config.VECTOR_METHOD_FOR_MODE.get(mode, "invert")
        found = res.vectors.candidates(token, vec_method)[: config.VECTOR_TOP_K]
        return _pick(rng, found) if found else None
    raise ValueError(method)


def _negate(tokens: list[Token], i: int, flipped: set[int]) -> str | None:
    """i番目の語を否定形にする。否定にできない文脈なら None。

    - 終止形・連体形 → 「ない」（食べる → 食べない、高い → 高くない）
    - 過去 → 「なかっ」＋た（食べた → 食べなかった）
    - 丁寧 → 「ます」を「ません」にする（食べます → 食べません）
    """
    t = tokens[i]
    nxt = tokens[i + 1] if i + 1 < len(tokens) else None

    if t.pos1 == "助動詞" and t.lemma == "ます":
        # 直前の動詞をすでに反意語にしていたら、二重に反転しない
        if i - 1 in flipped:
            return None
        if t.cform.startswith(("終止形", "連体形")):
            return "ません"
        if t.cform.startswith("連用形") and nxt is not None and nxt.normalized == "た":
            return "ませんでし"
        return None

    if t.pos1 not in ("動詞", "形容詞") or t.lemma in _NO_NEGATE or t.normalized in _NO_NEGATE:
        return None
    if nxt is not None and nxt.pos1 == "助動詞":
        if nxt.normalized == "た":
            return negate(t.lemma, t.pos1, t.ctype, "なかっ")
        if t.pos1 == "形容詞" and nxt.lemma == "です":
            return negate(t.lemma, t.pos1, t.ctype, "ない")
        return None  # ます・ない・らしい などが続くときは触らない
    if nxt is not None and nxt.pos1 == "形容詞" and nxt.lemma in _NO_NEGATE:
        return None  # すでに否定（高くない）
    if _is_ta(nxt):
        return None  # 「食べて」のような途中の語は否定しない
    if t.cform.startswith(("終止形", "連体形")):
        return negate(t.lemma, t.pos1, t.ctype, "ない")
    return None


def invert(text: str, resources: Resources, mode: str = "mix", seed: int | None = None) -> InvertResult:
    """文 text の各語を対義語に置き換えた「反対の文」を返す。"""
    if mode not in METHODS_FOR_MODE:
        raise ValueError(f"unknown mode: {mode}")
    if seed is None:
        seed = random.randrange(1 << 31)
    rng = random.Random(seed)

    tokens = tokenize(text)
    outputs = [t.surface for t in tokens]
    traces: list[TokenTrace] = []
    flipped: set[int] = set()

    for i, t in enumerate(tokens):
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        method, replaced, score = "keep", outputs[i], None

        for m in METHODS_FOR_MODE[mode]:
            if m == "negate":
                neg = _negate(tokens, i, flipped)
                if neg is not None:
                    method, replaced = "negate", neg
                    if t.pos1 == "動詞" and nxt is not None and nxt.normalized == "た":
                        outputs[i + 1] = _voice(nxt.surface, False)  # 読んだ → 読まなかった
                    break
                continue
            if t.pos1 not in CONTENT_POS:
                continue
            found = _find(m, t, resources, mode, rng)
            if found is None:
                continue
            word, score = found
            before_ta = _is_ta(nxt)
            replaced, voiced = inflect_word(word, t.cform, before_ta)
            if t.pos1 == "動詞" and before_ta:
                outputs[i + 1] = _voice(nxt.surface, voiced)
            method = m
            flipped.add(i)
            break

        outputs[i] = replaced
        traces.append(
            TokenTrace(
                surface=t.surface,
                lemma=t.lemma,
                pos=t.pos_label,
                replaced=replaced,
                method=method,
                score=None if score is None else round(score, 4),
            )
        )

    return InvertResult(result="".join(outputs), mode=mode, seed=seed, tokens=traces)
