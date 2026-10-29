import csv

import pytest

from app import config
from app.tokenizer import analyze_word, tokenize


def test_tokenize_gives_lemma_pos_and_conjugation():
    tokens = tokenize("明るい気持ちで走った。")
    assert [t.surface for t in tokens] == ["明るい", "気持ち", "で", "走っ", "た", "。"]
    run = tokens[3]
    assert run.lemma == "走る"
    assert run.pos1 == "動詞"
    assert run.ctype == "五段-ラ行"
    assert run.cform == "連用形-促音便"


def test_pos_groups_treat_keiyodoshi_nouns_as_keiyodoshi():
    (safe,) = analyze_word("安全")
    assert safe.pos1 == "名詞"
    assert "形状詞" in safe.pos_groups


def _csv_rows():
    with open(config.ANTONYMS_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.mark.parametrize("row", _csv_rows(), ids=lambda r: f"{r['語']}-{r['反意語']}")
def test_every_csv_word_is_one_morpheme_of_its_pos(row):
    for word in (row["語"], row["反意語"]):
        morphs = analyze_word(word)
        assert len(morphs) == 1, word
        assert row["品詞"] in morphs[0].pos_groups, (word, morphs[0].pos)
        assert morphs[0].lemma == word
