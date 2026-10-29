# data/

| ファイル | 中身 | git管理 |
| --- | --- | --- |
| `antonyms.csv` | 手書きの反意語辞書（`語,反意語,品詞`）。どちら向きにも引く | する |
| `wnjpn.db` | 日本語WordNet（SQLite版） | しない |
| `chive.kv` | chiVe（gensim形式） | しない |

## antonyms.csv

- `品詞` はSudachiの品詞大分類（`名詞` / `動詞` / `形容詞` / `形状詞` / `副詞` / `代名詞` など）。
- 語は辞書形で書く。表記ゆれ（「よい」「良い」など）はSudachiの正規化形でも引くので、どちらかで書けばよい。
- 1つの語に反意語が複数あるときは行を分けて書く。シードでどれを使うかが変わる。
- ミックスモードの方向ベクトル法は、各行の「語 → 反意語」の差分を平均する。
  向きをそろえるため、なるべく「大きい・良い・多い側」を左に書く。

## 日本語WordNet（任意）

1. <https://bond-lab.github.io/wnja/> から `wnjpn.db.gz` を入手して展開する。
2. `backend/data/wnjpn.db` に置く（別の場所なら環境変数 `TAIGI_WORDNET` で指定）。

日本語WordNetには日本語同士の反義リンクがほとんどないため、
`pip install nltk` のうえ `python -m nltk.downloader wordnet` で英語WordNetを入れておくと、
英語側の反義関係を経由して引けるようになる。

## chiVe（任意）

1. <https://github.com/WorksApplications/chiVe> から gensim 形式のファイルを入手する。
   まずは容量の小さい `mc90` 版で試すとよい。
2. 展開した `.kv`（と同じ場所の `.vectors.npy`）を `backend/data/chive.kv` に置くか、
   環境変数 `TAIGI_VECTORS` でパスを指定する。word2vec形式（`.txt` / `.bin`）も読める。

読み込みに失敗してもサーバーは落ちず、ベクトル方式を飛ばして動く。状態は `GET /api/health` で確認できる。
