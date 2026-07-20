import os
from pathlib import Path

MODEL_NAME = "qwen3.7-max"
TEMPERATURE = 0.0

CACHE_DIR = Path("./cache")
CACHE_DIR.mkdir(exist_ok=True)

TABLE_CACHE_PATH = CACHE_DIR / "table_data.pkl"
TABLE_HASH_PATH = CACHE_DIR / "table_hash.txt"
QUERY_CACHE_PATH = CACHE_DIR / "query_cache.json"

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise ValueError("请设置环境变量 DASHSCOPE_API_KEY")