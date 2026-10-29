import pytest

from app.antonyms import AntonymDict, Pair
from app.pipeline import Resources, invert
from app.vectors import VectorIndex


def replaced(result):
    return {t.surface: (t.replaced, t.method) for t in result.tokens if t.method != "keep"}


def test_dict_mode_replaces_words_and_keeps_conjugation(resources):
    r = invert("今日は天気がよいので、明るい気持ちで走った。", resources, "dict", seed=1)
    assert r.result == "昨日は嵐が悪いので、暗い気持ちで止まった。"
    assert replaced(r)["よい"] == ("悪い", "csv")
    assert replaced(r)["走っ"] == ("止まっ", "csv")
    assert r.mode == "dict" and r.seed == 1


def test_dict_mode_leaves_unknown_words(resources):
    r = invert("本を読んだ。", resources, "dict", seed=1)
    assert r.result == "本を読んだ。"
    assert all(t.method == "keep" for t in r.tokens)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("本を読んだ。", "本を読まなかった。"),
        ("彼女は泳いだ", "彼は泳がなかった"),
        ("本を読む。", "本を読まない。"),
        ("コーヒーを注ぎます。", "コーヒーを注ぎません。"),
        ("コーヒーを注ぎました。", "コーヒーを注ぎませんでした。"),
        ("犬を飼っていた。", "猫を飼っていなかった。"),
        ("部屋が臭いです。", "部屋が臭くないです。"),
    ],
)
def test_mix_mode_negates_when_no_antonym(resources, text, expected):
    assert invert(text, resources, "mix", seed=1).result == expected


def test_mix_mode_does_not_flip_twice(resources):
    # 「飲む」は辞書で置換されるので、「ます」は否定しない
    r = invert("水を飲みます。", resources, "mix", seed=1)
    assert r.result == "水を吐きます。"


def test_voicing_follows_the_replacement():
    res = Resources(AntonymDict([Pair("走る", "読む", "動詞")]))
    assert invert("走った", res, "dict", seed=0).result == "読んだ"
    assert invert("読んだ", res, "dict", seed=0).result == "走った"


def test_seed_reproduces_and_changes_choice():
    res = Resources(AntonymDict([Pair("高い", "低い", "形容詞"), Pair("高い", "安い", "形容詞")]))
    results = {invert("高い", res, "dict", seed=s).result for s in range(20)}
    assert results == {"低い", "安い"}
    assert invert("高い", res, "dict", seed=7).result == invert("高い", res, "dict", seed=7).result


def test_seed_is_generated_when_missing(resources):
    r = invert("高い山", resources, "dict")
    assert isinstance(r.seed, int)


def test_unknown_mode_is_rejected(resources):
    with pytest.raises(ValueError):
        invert("高い", resources, "llm")


def test_vector_mode_is_skipped_without_vectors(resources):
    r = invert("高い山に登る", resources, "vector", seed=1)
    assert r.result == "高い山に登る"


@pytest.fixture
def tiny_vectors():
    np = pytest.importorskip("numpy")
    KeyedVectors = pytest.importorskip("gensim.models").KeyedVectors
    words = {
        "高い": [1.0, 0.1, 0.0],
        "低い": [-1.0, 0.1, 0.0],
        "大きい": [0.9, 0.0, 0.3],
        "小さい": [-0.9, 0.0, 0.3],
        "長い": [0.8, -0.2, 0.1],
        "短い": [-0.8, -0.1, 0.1],
        "山": [0.1, 1.0, 0.0],
        "谷": [-0.1, 1.0, 0.0],
    }
    kv = KeyedVectors(vector_size=3)
    kv.add_vectors(list(words), np.array(list(words.values()), dtype=np.float32))
    pairs = [Pair("大きい", "小さい", "形容詞"), Pair("長い", "短い", "形容詞")]
    return VectorIndex(kv, pairs)


def test_direction_method_finds_antonym(tiny_vectors):
    res = Resources(AntonymDict([]), vectors=tiny_vectors)
    r = invert("高い", res, "mix", seed=0)
    (tok,) = r.tokens
    assert tok.method == "vector"
    assert tok.score is not None
    # 方向ベクトル法の最上位は「低い」
    cands = tiny_vectors.candidates(tokens_of("高い")[0], "direction")
    assert cands[0][0] == "低い"


def test_vector_candidates_keep_same_pos_only(tiny_vectors):
    for word, _ in tiny_vectors.candidates(tokens_of("高い")[0], "invert"):
        assert word not in ("山", "谷", "高い")


def tokens_of(text):
    from app.tokenizer import tokenize

    return tokenize(text)
