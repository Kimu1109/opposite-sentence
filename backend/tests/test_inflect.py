import pytest

from app.inflect import conjugate, inflect_word, negate


@pytest.mark.parametrize(
    "lemma, ctype, cform, before_ta, expected",
    [
        # 五段
        ("走る", "五段-ラ行", "連用形-促音便", True, ("走っ", False)),
        ("読む", "五段-マ行", "連用形-撥音便", True, ("読ん", True)),
        ("書く", "五段-カ行", "連用形-イ音便", True, ("書い", False)),
        ("泳ぐ", "五段-ガ行", "連用形-イ音便", True, ("泳い", True)),
        ("話す", "五段-サ行", "連用形-一般", True, ("話し", False)),
        ("行く", "五段-カ行", "連用形-促音便", True, ("行っ", False)),
        ("買う", "五段-ワア行", "未然形-一般", False, ("買わ", False)),
        ("走る", "五段-ラ行", "連用形-一般", False, ("走り", False)),
        ("走る", "五段-ラ行", "仮定形-一般", False, ("走れ", False)),
        ("走る", "五段-ラ行", "意志推量形", False, ("走ろ", False)),
        # 一段
        ("食べる", "下一段-バ行", "連用形-一般", True, ("食べ", False)),
        ("起きる", "上一段-カ行", "仮定形-一般", False, ("起きれ", False)),
        ("寝る", "下一段-ナ行", "終止形-一般", False, ("寝る", False)),
        # 変格
        ("する", "サ行変格", "連用形-一般", False, ("し", False)),
        ("愛する", "サ行変格", "仮定形-一般", False, ("愛すれ", False)),
        ("来る", "カ行変格", "連用形-一般", True, ("来", False)),
        ("くる", "カ行変格", "命令形", False, ("こい", False)),
        # 形容詞
        ("高い", "形容詞", "連用形-一般", False, ("高く", False)),
        ("高い", "形容詞", "連用形-促音便", True, ("高かっ", False)),
        ("高い", "形容詞", "仮定形-一般", False, ("高けれ", False)),
        ("いい", "形容詞", "連用形-一般", False, ("よく", False)),
        ("悪い", "形容詞", "連体形-一般", False, ("悪い", False)),
    ],
)
def test_conjugate(lemma, ctype, cform, before_ta, expected):
    assert conjugate(lemma, ctype, cform, before_ta) == expected


def test_conjugate_picks_onbin_for_the_replacement_row():
    # 元の語が一段（食べ＋た）でも、置換語が五段なら音便にする
    assert conjugate("飲む", "五段-マ行", "連用形-一般", before_ta=True) == ("飲ん", True)
    assert conjugate("飲む", "五段-マ行", "連用形-一般", before_ta=False) == ("飲み", False)


def test_inflect_word_reads_conjugation_type_from_sudachi():
    assert inflect_word("止まる", "連用形-促音便", before_ta=True) == ("止まっ", False)
    assert inflect_word("寝る", "連用形-一般") == ("寝", False)
    assert inflect_word("低い", "連用形-一般") == ("低く", False)
    assert inflect_word("谷", "*") == ("谷", False)


@pytest.mark.parametrize(
    "lemma, pos1, ctype, ending, expected",
    [
        ("食べる", "動詞", "下一段-バ行", "ない", "食べない"),
        ("走る", "動詞", "五段-ラ行", "なかっ", "走らなかっ"),
        ("買う", "動詞", "五段-ワア行", "ない", "買わない"),
        ("する", "動詞", "サ行変格", "ない", "しない"),
        ("来る", "動詞", "カ行変格", "ない", "来ない"),
        ("ある", "動詞", "五段-ラ行", "ない", "ない"),
        ("高い", "形容詞", "形容詞", "ない", "高くない"),
        ("いい", "形容詞", "形容詞", "なかっ", "よくなかっ"),
        ("静か", "形状詞", "*", "ない", None),
    ],
)
def test_negate(lemma, pos1, ctype, ending, expected):
    assert negate(lemma, pos1, ctype, ending) == expected
