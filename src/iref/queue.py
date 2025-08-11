# src/iref/queue.py
from __future__ import annotations
from pathlib import Path
from typing import Iterable, List, Set, Tuple
from PIL import Image
import imagehash
import orjson
from .models import RefItem

DEFAULT_EXTS = (".jpg", ".jpeg", ".png", ".webp")

def _image_files(root: Path, exts: Tuple[str, ...]) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            yield p

def _phash_safe(path: Path) -> str | None:
    try:
        with Image.open(path) as im:
            return str(imagehash.phash(im))
    except Exception:
        return None

def build_queue(
    root: Path,
    exts: Tuple[str, ...] = DEFAULT_EXTS,
    limit: int | None = None,
    seen_hashes: Set[str] | None = None,
) -> List[RefItem]:
    seen_hashes = set() if seen_hashes is None else set(seen_hashes)
    items: List[RefItem] = []

    files = list(_image_files(root, exts))
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)  # 新しい順

    for p in files:
        st = p.stat()
        h = _phash_safe(p)
        if not h:
            continue
        if h in seen_hashes:
            items.append(
                RefItem(path=p, size=st.st_size, mtime=st.st_mtime, phash=h, status="skipped-duplicate")
            )
            continue
        seen_hashes.add(h)
        items.append(RefItem(path=p, size=st.st_size, mtime=st.st_mtime, phash=h, status="queued"))
        if limit and sum(1 for i in items if i.status == "queued") >= limit:
            break
    return items

def save_queue(root: Path, items: List[RefItem]) -> Path:
    meta_dir = root / ".iref"
    meta_dir.mkdir(exist_ok=True)
    qpath = meta_dir / "queue.json"
    payload = [it.to_dict() for it in items]
    qpath.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))
    return qpath

def load_seen_hashes(root: Path) -> Set[str]:
    """将来的に processed.json などから既知ハッシュを読み込む想定。今は空集合。"""
    meta_dir = root / ".iref"
    processed = meta_dir / "processed.json"
    if processed.exists():
        try:
            data = orjson.loads(processed.read_bytes())
            return {e.get("phash") for e in data if isinstance(e, dict) and e.get("phash")}
        except Exception:
            return set()
    return set()
