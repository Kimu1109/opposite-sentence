"""活用の復元と否定化。

Sudachiの活用型（五段-ラ行 など）と活用形（連用形-促音便 など）を使い、
辞書形の語を元の語と同じ活用形に戻す。自作の表なので、まれな活用形では崩れる。
"""

from .tokenizer import analyze_word

# 五段活用の行ごとの「あいうえお」段
_GODAN_ROWS = {
    "カ": "かきくけこ",
    "ガ": "がぎぐげご",
    "サ": "さしすせそ",
    "タ": "たちつてと",
    "ナ": "なにぬねの",
    "バ": "ばびぶべぼ",
    "マ": "まみむめも",
    "ラ": "らりるれろ",
    "ワア": "わいうえお",
}
_A, _I, _U, _E, _O = range(5)

# 連用形の音便。値は（語尾, 後ろの「た・て」が濁るか）
_ONBIN = {
    "カ": ("い", False),
    "ガ": ("い", True),
    "サ": ("し", False),
    "タ": ("っ", False),
    "ラ": ("っ", False),
    "ワア": ("っ", False),
    "ナ": ("ん", True),
    "バ": ("ん", True),
    "マ": ("ん", True),
}
_IKU = ("行く", "いく", "逝く")


def _godan_row(ctype: str) -> str | None:
    # 「五段-ラ行」→「ラ」、「五段-ワア行」→「ワア」
    if not ctype.startswith("五段-"):
        return None
    return ctype.split("-", 1)[1].removesuffix("行")


def conjugate(lemma: str, ctype: str, cform: str, before_ta: bool = False) -> tuple[str, bool]:
    """辞書形 lemma を活用型 ctype の cform に活用させる。

    before_ta は後ろに「た・て」が続くかどうか（五段の音便を選ぶのに使う）。
    戻り値は（活用した表記, 後ろの「た・て」を「だ・で」にすべきか）。
    """
    if cform in ("*", "") or cform.startswith(("終止形", "連体形")):
        return lemma, False

    row = _godan_row(ctype)
    if row is not None and row in _GODAN_ROWS:
        stem, kana = lemma[:-1], _GODAN_ROWS[row]
        if cform.startswith("未然形"):
            return stem + kana[_A], False
        if cform.startswith("連用形"):
            if before_ta or "音便" in cform:
                if lemma.endswith(_IKU):
                    return stem + "っ", False
                ending, voiced = _ONBIN[row]
                return stem + ending, voiced
            return stem + kana[_I], False
        if cform.startswith(("仮定形", "命令形")):
            return stem + kana[_E], False
        if cform.startswith("意志推量形"):
            return stem + kana[_O], False
        return lemma, False

    if ctype.startswith(("上一段", "下一段")):
        stem = lemma[:-1]
        if cform.startswith(("未然形", "連用形")):
            return stem, False
        if cform.startswith("仮定形"):
            return stem + "れ", False
        if cform.startswith("命令形"):
            return stem + "ろ", False
        if cform.startswith("意志推量形"):
            return stem + "よ", False
        return lemma, False

    if ctype == "サ行変格" and lemma.endswith("する"):
        stem = lemma[:-2]
        if cform == "未然形-サ":
            return stem + "さ", False
        if cform.startswith(("未然形", "連用形")):
            return stem + "し", False
        if cform.startswith("仮定形"):
            return stem + "すれ", False
        if cform.startswith("命令形"):
            return stem + "しろ", False
        if cform.startswith("意志推量形"):
            return stem + "しよ", False
        return lemma, False

    if ctype == "カ行変格":
        kanji = lemma.endswith("来る")
        stem = lemma[:-2]
        if cform.startswith("未然形"):
            return stem + ("来" if kanji else "こ"), False
        if cform.startswith("連用形"):
            return stem + ("来" if kanji else "き"), False
        if cform.startswith("仮定形"):
            return stem + ("来れ" if kanji else "くれ"), False
        if cform.startswith("命令形"):
            return stem + ("来い" if kanji else "こい"), False
        return lemma, False

    if ctype == "形容詞":
        stem = _adjective_stem(lemma)
        if cform == "連用形-促音便":
            return stem + "かっ", False
        if cform.startswith("連用形"):
            return stem + "く", False
        if cform.startswith("仮定形"):
            return stem + "けれ", False
        if cform.startswith("未然形"):
            return stem + "かろ", False
        if cform.startswith("語幹"):
            return stem, False
        return lemma, False

    return lemma, False


def _adjective_stem(lemma: str) -> str:
    if lemma == "いい":
        return "よ"
    if lemma.endswith("いい"):
        return lemma[:-2] + "よ"
    return lemma[:-1]


def inflect_word(word: str, cform: str, before_ta: bool = False) -> tuple[str, bool]:
    """辞書の見出し語 word（複数形態素でもよい）を cform に活用させる。

    「勉強する」のように複数形態素になる語は、最後の形態素だけを活用させる。
    """
    morphs = analyze_word(word)
    if not morphs:
        return word, False
    last = morphs[-1]
    prefix = word[: len(word) - len(last.surface)]
    if last.surface != last.lemma:
        # 見出しが活用形で書かれていた場合は活用させずに返す
        return word, False
    surface, voiced = conjugate(last.lemma, last.ctype, cform, before_ta)
    return prefix + surface, voiced


def word_ctype(word: str) -> tuple[str, str]:
    """見出し語の（品詞, 活用型）。最後の形態素で判断する。"""
    morphs = analyze_word(word)
    if not morphs:
        return "", "*"
    return morphs[-1].pos1, morphs[-1].ctype


# ---- 否定化 ----

def mizen_for_nai(lemma: str, ctype: str) -> str | None:
    """動詞の「ない」につく形（未然形）。分からなければ None。"""
    if lemma in ("ある", "有る", "在る"):
        return ""  # 「ある」の否定は「ない」
    row = _godan_row(ctype)
    if row is not None and row in _GODAN_ROWS:
        return lemma[:-1] + _GODAN_ROWS[row][_A]
    if ctype.startswith(("上一段", "下一段")):
        return lemma[:-1]
    if ctype == "サ行変格" and lemma.endswith("する"):
        return lemma[:-2] + "し"
    if ctype == "カ行変格":
        return lemma[:-2] + ("来" if lemma.endswith("来る") else "こ")
    return None


def negate(lemma: str, pos1: str, ctype: str, ending: str = "ない") -> str | None:
    """動詞・形容詞を否定形にする。ending は「ない」「なかっ」など。

    食べる → 食べない、高い → 高くない、走る + なかっ → 走らなかっ
    """
    if pos1 == "動詞":
        base = mizen_for_nai(lemma, ctype)
        return None if base is None else base + ending
    if pos1 == "形容詞" and ctype == "形容詞":
        return _adjective_stem(lemma) + "く" + ending
    return None
