"""chiVeの読み込み、最近傍、方向ベクトル。

読み込みに失敗しても例外で落とさず None を返し、辞書だけで動き続ける。
"""

import logging
from pathlib import Path

from .antonyms import Pair, token_keys
from .tokenizer import Token, analyze_word

log = logging.getLogger(__name__)

# 候補を何件引いてから品詞で絞るか
_SEARCH_TOPN = 50


class VectorIndex:
    def __init__(self, kv, pairs: list[Pair] = ()):
        import numpy as np

        self.kv = kv
        self._np = np
        self.direction = None
        self.centre = None
        diffs, members = [], []
        for p in pairs:
            a, b = self._key(p.word), self._key(p.antonym)
            if a is None or b is None:
                continue
            va, vb = self._unit(a), self._unit(b)
            diffs.append(vb - va)
            members += [va, vb]
        if diffs:
            self.direction = np.mean(diffs, axis=0)
            self.centre = np.mean(members, axis=0)
        self.pair_count = len(diffs)

    @classmethod
    def load(cls, path: Path, pairs: list[Pair] = ()) -> "VectorIndex | None":
        if not path.exists():
            log.info("ベクトルファイルがありません: %s", path)
            return None
        try:
            from gensim.models import KeyedVectors

            if path.suffix == ".kv":
                kv = KeyedVectors.load(str(path), mmap="r")
            else:
                kv = KeyedVectors.load_word2vec_format(str(path), binary=path.suffix == ".bin")
            return cls(kv, pairs)
        except Exception as e:  # gensimが無い、形式が違う、など
            log.warning("ベクトルを読み込めませんでした: %s", e)
            return None

    def _key(self, word: str) -> str | None:
        candidates = [word]
        morphs = analyze_word(word)
        if len(morphs) == 1:
            candidates += [morphs[0].normalized, morphs[0].lemma]
        for c in candidates:
            if c in self.kv.key_to_index:
                return c
        return None

    def _token_key(self, token: Token) -> str | None:
        for k in token_keys(token):
            if k in self.kv.key_to_index:
                return k
        return None

    def _unit(self, key: str):
        v = self.kv[key]
        return v / (self._np.linalg.norm(v) or 1.0)

    def candidates(self, token: Token, method: str) -> list[tuple[str, float]]:
        """同じ品詞の候補を（語, 類似度）で返す。method は 'invert' か 'direction'。"""
        key = self._token_key(token)
        if key is None:
            return []
        if method == "direction" and self.direction is not None:
            v = self._unit(key)
            # 対象語が反意語ペアのどちら側にいるかで、方向を足すか引くかを決める
            side = self._np.dot(v - self.centre, self.direction)
            target = v - self.direction if side > 0 else v + self.direction
            raw = self.kv.similar_by_vector(target, topn=_SEARCH_TOPN)
        else:
            raw = self.kv.most_similar(negative=[key], topn=_SEARCH_TOPN)
        return [(w, float(s)) for w, s in raw if self._same_pos(token, key, w)]

    @staticmethod
    def _same_pos(token: Token, key: str, word: str) -> bool:
        morphs = analyze_word(word)
        if len(morphs) != 1:
            return False
        m = morphs[0]
        if m.pos1 != token.pos1 or m.lemma != word:
            return False
        if m.lemma in (token.lemma, token.normalized, key) or m.normalized == token.normalized:
            return False
        return True
