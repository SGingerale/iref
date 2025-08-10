from __future__ import annotations
from pathlib import Path
import orjson
from platformdirs import user_config_dir
import os

APP_NAME = "iref"
CONF_DIR = Path(user_config_dir(APP_NAME))
CONF_DIR.mkdir(parents=True, exist_ok=True)
CONF_PATH = CONF_DIR / "config.json"


def _load():
    if CONF_PATH.exists():
        return orjson.loads(CONF_PATH.read_bytes())
    return {"profiles": {"default": ""}, "active": "default"}


def _save(cfg):
    CONF_PATH.write_bytes(orjson.dumps(cfg, option=orjson.OPT_INDENT_2))


def set_root(profile: str, path: Path):
    cfg = _load()
    cfg["profiles"][profile] = str(path)
    _save(cfg)


def get_root(profile: str | None = None) -> Path:
    # 環境変数最優先
    env = os.getenv("IREF_ROOT")
    if env:
        return Path(env)

    cfg = _load()
    name = profile or cfg.get("active", "default")
    path = cfg["profiles"].get(name, "")
    if not path:
        raise SystemExit(
            f"root not set for profile '{name}'. Run: iref config set-root --path <dir>"
        )
    return Path(path)


def set_active(profile: str):
    cfg = _load()
    if profile not in cfg["profiles"]:
        raise SystemExit(f"profile '{profile}' not found.")
    cfg["active"] = profile
    _save(cfg)
