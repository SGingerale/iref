# src/iref/cli.py
from __future__ import annotations

from pathlib import Path
import os
import time
from typing import Iterable, List, Dict, Any, Tuple

import typer
from rich.console import Console
from rich.table import Table
from PIL import Image, UnidentifiedImageError
import orjson

app = typer.Typer(help="Illustration Refs – Discovery Queue CLI")
console = Console()

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

def is_hidden_or_system_dir(p: Path) -> bool:
    name = p.name
    if name.startswith("."):
        return True
    # 明示的にirefの管理ディレクトリは除外
    if name.lower() == ".iref":
        return True
    return False

def iter_image_files(root: Path, exts: Iterable[str]) -> Iterable[Path]:
    exts_l = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in exts}
    for dirpath, dirnames, filenames in os.walk(root):
        # .iref や隠し系をスキップ
        dirnames[:] = [d for d in dirnames if not is_hidden_or_system_dir(Path(dirpath) / d)]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() in exts_l:
                yield p

def get_image_info(p: Path) -> Tuple[Dict[str, Any] | None, str | None]:
    try:
        stat = p.stat()
        width = height = None
        with Image.open(p) as im:
            width, height = im.size

        item = {
            "path": str(p.resolve()),
            "relpath": str(p),
            "size_bytes": stat.st_size,
            "mtime": stat.st_mtime,
            "width": width,
            "height": height,
            "ext": p.suffix.lower(),
        }
        return item, None
    except (UnidentifiedImageError, OSError) as e:
        return None, f"{p}: {e}"

def ensure_state_dir(root: Path) -> Path:
    state = root / ".iref"
    state.mkdir(parents=True, exist_ok=True)
    return state

def save_queue(state_dir: Path, items: List[Dict[str, Any]]) -> Path:
    out_path = state_dir / "queue.json"
    payload = {
        "version": 1,
        "generated_at": time.time(),
        "count": len(items),
        "items": items,
    }
    out_path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))
    return out_path

@app.command("queue")
def queue_cmd(
    root: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True, readable=True, help="画像ルート"),
    dry_run: bool = typer.Option(False, "--dry-run", help="書き込みせずスキャンだけ実行"),
    limit: int = typer.Option(0, "--limit", min=0, help="最大件数。0なら制限なし"),
    ext: List[str] = typer.Option(
        list(sorted(SUPPORTED_EXTS)),
        "--ext",
        help="対象拡張子（繰り返し指定可）例: --ext .jpg --ext .png",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="詳細ログ"),
):
    """
    画像を走査して `ROOT/.iref/queue.json` を作成/更新します。
    """
    root = root.resolve()
    if verbose:
        console.print(f"[bold]Root:[/bold] {root}")

    files = []
    errors = []
    for p in iter_image_files(root, ext):
        info, err = get_image_info(p)
        if info:
            files.append(info)
            if limit and len(files) >= limit:
                break
        elif err:
            errors.append(err)
            if verbose:
                console.print(f"[yellow]WARN[/]: {err}")

    # 人間向けサマリ
    table = Table(title="Scan Summary")
    table.add_column("Found")
    table.add_column("Errors")
    table.add_column("Will write")
    table.add_row(str(len(files)), str(len(errors)), "no (dry-run)" if dry_run else "yes")
    console.print(table)

    if dry_run:
        return

    state_dir = ensure_state_dir(root)
    out_path = save_queue(state_dir, files)
    console.print(f"[green]Wrote:[/green] {out_path}  ({len(files)} items)")

@app.command("config")
def config_cmd():
    """
    いずれ設定系を実装する予定のプレースホルダ。
    """
    console.print("Config command is not implemented yet. Coming soon!")

def main():
    app()

if __name__ == "__main__":
    main()
