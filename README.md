# 対義文ジェネレーター

入力した日本語の文を分かち書きし、各語を対義語に置き換えて「反対の文」を返す、遊び用のWebアプリです。
正しさより面白さを優先し、どの語をどの方式で置き換えたかを画面に出します。

```
今日は天気がよいので、明るい気持ちで走った。
→ 昨日は嵐が悪いので、暗い気持ちで止まった。
```

## 起動

Python 3.11以上が必要です。

```bash
make setup
```

```bash
make run
```

<http://127.0.0.1:8000/> を開きます。`make` が無い環境では次の1コマンドでも起動できます。

```bash
uvicorn app.main:app --app-dir backend
```

テストは `make test`（または `python -m pytest`）で動きます。

## しくみ

1. **分かち書き**: SudachiPy（`sudachidict_core`）で形態素に分け、原形・品詞・活用形を取る
2. **対義語探索**: 語ごとに次の順で試し、最初に見つかったものを採用する

   | 順 | 方式 | `method` | 中身 |
   | --- | --- | --- | --- |
   | 1 | 自作CSV | `csv` | `backend/data/antonyms.csv` から原形と品詞が一致する反意語を選ぶ。複数あればシードで選ぶ |
   | 2 | 日本語WordNet | `wordnet` | 反義リンクを引く（任意） |
   | 3 | ベクトル | `vector` | chiVeで近い語を探す。同じ品詞の候補だけ残す（任意） |
   | 4 | 否定化 | `negate` | 動詞・形容詞を否定形にする（食べる → 食べない、食べた → 食べなかった、食べます → 食べません、高い → 高くない） |
   | 5 | 素通し | `keep` | 助詞・固有名詞・数字などはそのまま |

3. **活用の復元**: 置換した語を元の活用形に戻す（走った → 止まった、読んだ ↔ 走った のように「た／だ」も合わせる）

### モード

| モード | 使う方式 | 狙い |
| --- | --- | --- |
| `dict`（辞書） | 1・2 | 安定した結果 |
| `vector`（ベクトル） | 3（ベクトル反転法） | 似た語が返る失敗を観察して遊ぶ |
| `mix`（ミックス、既定） | 1→2→3（方向ベクトル法）→4 | 一番それらしくなる |

ベクトル方式は2通りあります。

- **方向ベクトル法**（ミックス）: CSVの反意語ペアの差分ベクトルを平均し、対象語に足し引きして最近傍を引く
- **ベクトル反転法**（ベクトル）: `most_similar(negative=[語])` で符号を反転したベクトルの最近傍を引く

どちらを使うかは `backend/app/config.py` の `VECTOR_METHOD_FOR_MODE` で変えられます。

## 任意のデータ

WordNetとchiVeは容量が大きいのでgit管理していません。無くても辞書と否定化だけで動きます。
置き場所は [`backend/data/README.md`](backend/data/README.md) を見てください。

| 環境変数 | 既定値 | 中身 |
| --- | --- | --- |
| `TAIGI_ANTONYMS` | `backend/data/antonyms.csv` | 反意語CSV |
| `TAIGI_WORDNET` | `backend/data/wnjpn.db` | 日本語WordNet |
| `TAIGI_VECTORS` | `backend/data/chive.kv` | chiVe（`.kv` / `.txt` / `.bin`） |
| `TAIGI_DEFAULT_MODE` | `mix` | 既定モード |

## API

### `POST /api/invert`

```json
{ "text": "今日は天気がよいので、明るい気持ちで走った。", "mode": "mix", "seed": 42 }
```

`mode` は `dict` / `vector` / `mix`、`seed` は省略可（省略するとサーバーが決めて返す）。`text` は200文字まで。

```json
{
  "result": "昨日は嵐が悪いので、暗い気持ちで止まった。",
  "mode": "mix",
  "seed": 42,
  "tokens": [
    { "surface": "よい", "lemma": "よい", "pos": "形容詞", "replaced": "悪い", "method": "csv", "score": null },
    { "surface": "走っ", "lemma": "走る", "pos": "動詞", "replaced": "止まっ", "method": "csv", "score": null }
  ]
}
```

`score` はベクトル方式のときだけ類似度が入ります。

### `GET /api/health`

```json
{ "status": "ok", "antonym_pairs": 113, "wordnet_loaded": false, "vectors_loaded": false }
```

## 画面

- 置換した語を方式ごとの色で強調し、カーソルを合わせると元の語・方式・スコアを出す
- トレース表で 原語 → 置換語 → 方式 を語ごとに一覧する
- 「もう一回」でシードを変えて再実行する
- URLに `?text=&mode=&seed=` が入るので、面白い結果をそのまま共有できる

## ディレクトリ構成

```
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI起点。ルーティングと静的配信
│   │   ├── schemas.py     # リクエスト/レスポンスの型
│   │   ├── tokenizer.py   # Sudachiのラッパー。Token型を返す
│   │   ├── antonyms.py    # CSV・WordNetの読み込みと検索
│   │   ├── vectors.py     # chiVeの読み込み、最近傍、方向ベクトル
│   │   ├── inflect.py     # 活用の復元、否定化
│   │   ├── pipeline.py    # 全体の組み立て（FastAPIに依存しない純粋関数）
│   │   └── config.py      # パス、既定モード
│   ├── data/
│   │   ├── antonyms.csv   # 語, 反意語, 品詞（手書き）
│   │   └── README.md      # chiVe・WordNetの置き場所メモ
│   └── tests/
└── frontend/
    ├── index.html
    ├── app.js
    └── style.css
```

## 既知の限界

- ベクトルでは反意語が近い位置に来るため、ベクトルモードは「似た語」を返しがち
- 多義語は文脈を見ないので、意味の違う反意語を選ぶことがある
- 助詞と語順は触らないので、因果の文などは意味が崩れる
- 活用は自作の表で復元するため、まれな活用形では崩れる
