# src/iref/config_store.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional, List
import json
from platformdirs import user_config_dir

APP_NAME = "iref"

class ConfigStore:
    def __init__(self, app_name: str = APP_NAME):
        cfg_dir = Path(user_config_dir(app_name))
        cfg_dir.mkdir(parents=True, exist_ok=True)
        self._path = cfg_dir / "profiles.json"
        self._data: Dict[str, Dict[str, str]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                # 壊れてたら空扱い（将来はバックアップ/復旧を検討）
                self._data = {}
        else:
            self._data = {}

    def _save(self) -> None:
        text = json.dumps(self._data, ensure_ascii=False, indent=2)
        self._path.write_text(text, encoding="utf-8")

    def list_profiles(self) -> List[str]:
        return sorted(self._data.keys())

    def get_root(self, profile: str = "default") -> Optional[Path]:
        info = self._data.get(profile)
        if not info:
            return None
        p = Path(info.get("root", "")).expanduser()
        return p if p.as_posix() else None

    def set_root(self, profile: str, root: Path) -> Path:
        root = root.expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(f"Root not found: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Root must be a directory: {root}")
        self._data.setdefault(profile, {})["root"] = str(root)
        self._save()
        return root

    def as_dict(self) -> Dict[str, Dict[str, str]]:
        return dict(self._data)
