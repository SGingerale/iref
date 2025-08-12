# src/iref/store/queue_store.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Union
import os
import tempfile
import orjson


# ---- internal helpers -------------------------------------------------------

def _queue_path(root: Path) -> Path:
    return (root / ".iref" / "queue.json").resolve()


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    """
    Windowsでも安全な原子的置換。必ず同一ディレクトリに一時ファイルを作る。
    """
    path.parent.mkdir(parents=True, exist_ok=True)  # 既存前提だが安全側で
    tmp_fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(tmp_fd, "wb") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
            f.write(b"\n")
        os.replace(tmp_name, path)  # 原子的置換
    except Exception:
        # 失敗時は一時ファイルを掃除
        try:
            os.remove(tmp_name)
        except OSError:
            pass
        raise


def _validate_queue_payload(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("queue.json: top-level must be an object")
    if "items" not in payload or not isinstance(payload["items"], list):
        raise ValueError("queue.json: 'items' list is missing")
    # 各 item の最小チェック（MVP簡易版）
    for i, item in enumerate(payload["items"]):
        if not isinstance(item, dict):
            raise ValueError(f"queue.json: items[{i}] must be an object")
        if "relpath" not in item or not isinstance(item["relpath"], str):
            raise ValueError(f"queue.json: items[{i}].relpath must be a string")
        # status は後方互換で任意扱い（存在するなら str）
        st = item.get("status", None)
        if st is not None and not isinstance(st, str):
            raise ValueError(f"queue.json: items[{i}].status must be a string when present")
        # decided_at も同様に任意
        dt = item.get("decided_at", None)
        if dt is not None and not (isinstance(dt, str) or dt is None):
            raise ValueError(f"queue.json: items[{i}].decided_at must be ISO8601 string or null when present")



# ---- public API --------------------------------------------------------------

def load_queue(root: Path) -> Dict[str, Any]:
    """
    .iref/queue.json を読み込んで dict を返す。
    なければ FileNotFoundError。壊れていれば ValueError。
    """
    qp = _queue_path(root)
    if not qp.exists():
        raise FileNotFoundError(f"queue.json not found: {qp}")
    try:
        data = orjson.loads(qp.read_bytes())
    except orjson.JSONDecodeError as e:
        raise ValueError(f"queue.json is not valid JSON: {qp}") from e
    _validate_queue_payload(data)
    return data


def save_item(root: Path, idx: int, new_item: Dict[str, Any]) -> None:
    """
    items[idx] を new_item で置き換えて保存（atomic write）。
    """
    q = load_queue(root)
    items: List[Dict[str, Any]] = q["items"]
    if not (0 <= idx < len(items)):
        raise IndexError(f"index out of range: {idx}")
    # 置換（安全のため shallow copy）
    items[idx] = dict(new_item)
    _atomic_write_json(_queue_path(root), q)


def save_all(root: Path, queue_data: Dict[str, Any]) -> None:
    """
    queue 全体を保存（atomic）。review ループからの flush 用。
    """
    _validate_queue_payload(queue_data)
    _atomic_write_json(_queue_path(root), queue_data)


def first_pending_index(items: List[Dict[str, Any]]) -> int:
    """
    status == 'pending' の最初の index。無ければ 0。
    """
    for i, it in enumerate(items):
        if it.get("status") == "pending":
            return i
    return 0


def find_index(items: List[Dict[str, Any]], token: Union[str, int]) -> int:
    """
    token が int ならそれを index として使用。
    str なら relpath 完全一致 → サフィックス一致（末尾一致）の順で探索。
    見つからなければ ValueError。
    """
    if isinstance(token, int):
        if 0 <= token < len(items):
            return token
        raise ValueError(f"index out of range: {token}")

    # 完全一致
    for i, it in enumerate(items):
        if it.get("relpath") == token:
            return i

    # 末尾一致（例: "set1/img001.jpg" に対し "img001.jpg" でヒット）
    for i, it in enumerate(items):
        rp = it.get("relpath", "")
        if isinstance(rp, str) and rp.endswith(token):
            return i

    raise ValueError(f"relpath not found (token='{token}')")
