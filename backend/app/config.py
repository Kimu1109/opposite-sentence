"""パスと既定値。環境変数で上書きできる。"""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
FRONTEND_DIR = ROOT_DIR / "frontend"

ANTONYMS_CSV = Path(os.environ.get("TAIGI_ANTONYMS", DATA_DIR / "antonyms.csv"))
# 日本語WordNetのSQLite（wnjpn.db）。無ければWordNet方式は飛ばす
WORDNET_DB = Path(os.environ.get("TAIGI_WORDNET", DATA_DIR / "wnjpn.db"))
# chiVeのgensim形式（.kv）またはword2vec形式（.txt / .bin）。無ければベクトル方式は飛ばす
VECTORS_PATH = Path(os.environ.get("TAIGI_VECTORS", DATA_DIR / "chive.kv"))

MODES = ("dict", "vector", "mix")
DEFAULT_MODE = os.environ.get("TAIGI_DEFAULT_MODE", "mix")
MAX_TEXT_LENGTH = 200

# ベクトルモードは「似た語が返る失敗を観察する」用のベクトル反転法、
# ミックスモードは反意語を狙う方向ベクトル法を使う
VECTOR_METHOD_FOR_MODE = {"vector": "invert", "mix": "direction"}
# ベクトル候補の上位何件からシードで選ぶか
VECTOR_TOP_K = 3
