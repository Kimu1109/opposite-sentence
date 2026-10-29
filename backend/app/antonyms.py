"""反意語辞書（自作CSV）と日本語WordNetの読み込み・検索。"""

import csv
import logging
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .tokenizer import Token, analyze_word

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Pair:
    word: str
    antonym: str
    pos: str


def _keys(word: str) -> set[str]:
    """見出し語の引き当てキー。表記そのものと、Sudachiの正規化形・辞書形。"""
    keys = {word}
    morphs = analyze_word(word)
    if len(morphs) == 1:
        keys.add(morphs[0].normalized)
        keys.add(morphs[0].lemma)
    return keys


def token_keys(token: Token) -> list[str]:
    return list(dict.fromkeys([token.lemma, token.normalized, token.surface]))


class AntonymDict:
    """語, 反意語, 品詞 のCSV。どちら向きにも引ける。"""

    def __init__(self, pairs: list[Pair]):
        self.pairs = pairs
        self._index: dict[tuple[str, str], list[str]] = defaultdict(list)
        for p in pairs:
            for a, b in ((p.word, p.antonym), (p.antonym, p.word)):
                for key in _keys(a):
                    if b not in self._index[(key, p.pos)]:
                        self._index[(key, p.pos)].append(b)

    @classmethod
    def load(cls, path: Path) -> "AntonymDict":
        pairs = []
        with open(path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                word, ant, pos = (row.get(k, "").strip() for k in ("語", "反意語", "品詞"))
                if word and ant and pos and not word.startswith("#"):
                    pairs.append(Pair(word, ant, pos))
        return cls(pairs)

    def lookup(self, token: Token) -> list[str]:
        """原形と品詞が一致する反意語を返す。"""
        found: list[str] = []
        for group in token.pos_groups:
            for key in token_keys(token):
                for ant in self._index.get((key, group), []):
                    if ant not in found and ant != token.lemma:
                        found.append(ant)
        return found


class WordNet:
    """日本語WordNet（wnjpn.db）の反義リンクを引く。

    wnjpn.db の synlink に反義（ants）リンクがあればそれを使う。
    NLTKの英語WordNetが入っていれば、英語側の反義語を経由して同義集合を引く。
    """

    _POS = {"名詞": "n", "動詞": "v", "形容詞": "a", "形状詞": "a", "副詞": "r"}

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._nltk_wn = _load_nltk_wordnet()

    @classmethod
    def load(cls, path: Path) -> "WordNet | None":
        if not path.exists():
            return None
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
            conn.execute("SELECT 1 FROM word LIMIT 1")
            return cls(conn)
        except sqlite3.Error as e:
            log.warning("WordNetを読み込めませんでした: %s", e)
            return None

    def _synsets(self, lemma: str, pos: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT s.synset FROM word w JOIN sense s ON w.wordid = s.wordid "
            "WHERE w.lemma = ? AND w.lang = 'jpn' AND w.pos = ?",
            (lemma, pos),
        ).fetchall()
        return [r[0] for r in rows]

    def _antonym_synsets(self, synset: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT synset2 FROM synlink WHERE synset1 = ? AND link = 'ants'", (synset,)
        ).fetchall()
        result = [r[0] for r in rows]
        if self._nltk_wn is not None:
            result += _nltk_antonym_synsets(self._nltk_wn, synset)
        return result

    def _words(self, synset: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT w.lemma FROM sense s JOIN word w ON w.wordid = s.wordid "
            "WHERE s.synset = ? AND w.lang = 'jpn'",
            (synset,),
        ).fetchall()
        return [r[0] for r in rows]

    def lookup(self, token: Token) -> list[str]:
        pos = self._POS.get(token.pos1)
        if pos is None:
            return []
        found: list[str] = []
        for key in token_keys(token):
            for syn in self._synsets(key, pos):
                for ant_syn in self._antonym_synsets(syn):
                    for w in self._words(ant_syn):
                        if w not in found and w != token.lemma:
                            found.append(w)
        return found


def _load_nltk_wordnet():
    try:
        from nltk.corpus import wordnet as wn

        wn.ensure_loaded()
        return wn
    except Exception:  # NLTKやデータが無ければ使わない
        return None


def _nltk_antonym_synsets(wn, synset: str) -> list[str]:
    # wnjpn の synset ID は「08位のオフセット-品詞」（WordNet 3.0）
    try:
        offset, pos = synset.split("-")
        ss = wn.synset_from_pos_and_offset(pos, int(offset))
    except Exception:
        return []
    result = []
    for lemma in ss.lemmas():
        for ant in lemma.antonyms():
            s = ant.synset()
            result.append(f"{s.offset():08d}-{s.pos().replace('s', 'a')}")
    return result
