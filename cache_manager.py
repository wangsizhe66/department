import json
import hashlib
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import config


class CacheManager:
    def __init__(self):
        self.table_cache_path = config.TABLE_CACHE_PATH
        self.table_hash_path = config.TABLE_HASH_PATH
        self.query_cache_path = config.QUERY_CACHE_PATH

    def save_table(self, df: pd.DataFrame) -> None:
        df.to_pickle(self.table_cache_path)
        with open(self.table_hash_path, "w", encoding="utf-8") as f:
            f.write(str(datetime.now().timestamp()))

    def load_table(self) -> Optional[pd.DataFrame]:
        if self.table_cache_path.exists():
            return pd.read_pickle(self.table_cache_path)
        return None

    def get_table_hash(self) -> Optional[str]:
        if self.table_hash_path.exists():
            with open(self.table_hash_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        return None

    def _load_query_cache(self) -> dict:
        if self.query_cache_path.exists():
            with open(self.query_cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_query_cache(self, cache: dict) -> None:
        with open(self.query_cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    def get_query_result(self, inputs: List[str], table_hash: str) -> Optional[List[str]]:
        key = self._compute_key(inputs, table_hash)
        cache = self._load_query_cache()
        return cache.get(key)

    def save_query_result(self, inputs: List[str], table_hash: str, result: List[str]) -> None:
        key = self._compute_key(inputs, table_hash)
        cache = self._load_query_cache()
        cache[key] = result
        self._save_query_cache(cache)

    def clear_query_cache(self) -> None:
        if self.query_cache_path.exists():
            self.query_cache_path.unlink()

    @staticmethod
    def _compute_key(inputs: List[str], table_hash: str) -> str:
        sorted_inputs = sorted(inputs)
        raw = "||".join(sorted_inputs) + "||" + table_hash
        return hashlib.md5(raw.encode("utf-8")).hexdigest()