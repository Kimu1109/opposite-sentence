import sqlite3

from app.antonyms import AntonymDict, Pair, WordNet
from app.tokenizer import tokenize


def test_csv_lookup_works_both_ways_and_by_normalized_form():
    d = AntonymDict([Pair("良い", "悪い", "形容詞")])
    (yoi,) = [t for t in tokenize("よい") if t.pos1 == "形容詞"]
    (warui,) = tokenize("悪い")
    assert d.lookup(yoi) == ["悪い"]
    assert d.lookup(warui) == ["良い"]


def test_csv_lookup_requires_same_pos():
    d = AntonymDict([Pair("上", "下", "名詞")])
    (ue,) = tokenize("上")
    assert d.lookup(ue) == ["下"]
    assert AntonymDict([Pair("上", "下", "動詞")]).lookup(ue) == []


def test_wordnet_follows_ants_links(tmp_path):
    db = tmp_path / "wnjpn.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE word (wordid INTEGER, lang TEXT, lemma TEXT, pron TEXT, pos TEXT);
        CREATE TABLE sense (synset TEXT, wordid INTEGER, lang TEXT, rank TEXT, lexid INTEGER, freq INTEGER, src TEXT);
        CREATE TABLE synlink (synset1 TEXT, synset2 TEXT, link TEXT, src TEXT);
        INSERT INTO word VALUES (1, 'jpn', '暑い', NULL, 'a'), (2, 'jpn', '寒い', NULL, 'a');
        INSERT INTO sense VALUES ('001-a', 1, 'jpn', NULL, 0, 0, NULL), ('002-a', 2, 'jpn', NULL, 0, 0, NULL);
        INSERT INTO synlink VALUES ('001-a', '002-a', 'ants', NULL);
        """
    )
    conn.commit()
    conn.close()

    wn = WordNet.load(db)
    assert wn is not None
    (atsui,) = tokenize("暑い")
    assert wn.lookup(atsui) == ["寒い"]


def test_wordnet_missing_file_returns_none(tmp_path):
    assert WordNet.load(tmp_path / "nope.db") is None
