"""Sudachiのラッパー。Token型を返す。"""

from dataclasses import dataclass
from functools import lru_cache

from sudachipy import dictionary
from sudachipy import tokenizer as sudachi_tokenizer


@dataclass(frozen=True)
class Token:
    surface: str
    lemma: str  # 辞書形（表記はそのまま）
    normalized: str  # 正規化形（表記ゆれを寄せたもの）
    pos: tuple[str, ...]  # Sudachiの品詞6要素

    @property
    def pos1(self) -> str:
        return self.pos[0]

    @property
    def pos2(self) -> str:
        return self.pos[1]

    @property
    def ctype(self) -> str:
        """活用型（例: 五段-ラ行、形容詞）。活用しない語は '*'。"""
        return self.pos[4]

    @property
    def cform(self) -> str:
        """活用形（例: 連用形-促音便）。活用しない語は '*'。"""
        return self.pos[5]

    @property
    def pos_label(self) -> str:
        return self.pos1

    @property
    def pos_groups(self) -> tuple[str, ...]:
        """辞書を引くときの品詞。「安全」（名詞・形状詞可能）は形状詞としても引く。"""
        groups = [self.pos1]
        if self.pos1 == "名詞" and self.pos[2].endswith("形状詞可能"):
            groups.append("形状詞")
        if self.pos1 == "名詞" and self.pos[2] == "副詞可能":
            groups.append("副詞")
        if self.pos1 == "形状詞":
            groups.append("副詞")
        return tuple(groups)


@lru_cache(maxsize=1)
def _tokenizer():
    return dictionary.Dictionary().create()


def tokenize(text: str) -> list[Token]:
    mode = sudachi_tokenizer.Tokenizer.SplitMode.C
    return [
        Token(
            surface=m.surface(),
            lemma=m.dictionary_form(),
            normalized=m.normalized_form(),
            pos=tuple(m.part_of_speech()),
        )
        for m in _tokenizer().tokenize(text, mode)
    ]


@lru_cache(maxsize=4096)
def analyze_word(word: str) -> tuple[Token, ...]:
    """単語（辞書の見出しなど）を解析する。置換語の活用型を知るのに使う。"""
    return tuple(tokenize(word))
