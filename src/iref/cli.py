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

from iref.config_store import ConfigStore

app = typer.Typer(help="Illustration Refs – Discovery Queue CLI")
console = Console()

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# 既存の app を使い回し（app = typer.Typer() が既にある前提）
config_app = typer.Typer(help="プロファイル設定を管理します")
app.add_typer(config_app, name="config")

_store = ConfigStore()

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
    root: Path = typer.Argument(
        None,  # ← 省略可に
        dir_okay=True, file_okay=False,
        help="画像ルート（省略時は --profile の設定を使用）",
    ),
    profile: str = typer.Option("default", "--profile", "-p", help="設定プロフィール名（root未指定時に使用）"),
    dry_run: bool = typer.Option(False, "--dry-run", help="書き込みせずスキャンだけ実行"),
    limit: int = typer.Option(0, "--limit", min=0, help="最大件数。0なら制限なし"),
    ext: List[str] = typer.Option(
        list(sorted(SUPPORTED_EXTS)),
        "--ext",
        help="対象拡張子（繰り返し指定可）例: --ext .jpg --ext .png",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="詳細ログ"),
):
    # root 未指定ならプロフィールから取得
    if root is None:
        cfg_root = _store.get_root(profile)
        if not cfg_root:
            typer.secho(
                f"[queue] root 未指定で、プロフィール '{profile}' にも root がありません。\n"
                f"まず: iref config set-root {profile} <フォルダ> を実行してください。",
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=2)
        root = cfg_root
    else:
        # 明示された root の妥当性チェック
        if not root.exists() or not root.is_dir():
            typer.secho(f"[queue] Root が見つからないかディレクトリではありません: {root}", fg=typer.colors.RED)
            raise typer.Exit(code=2)
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

@config_app.command("set-root")
def config_set_root(
    profile: str = typer.Argument(..., help="プロフィール名（例: default）"),
    root: Path = typer.Argument(..., exists=True, file_okay=False, help="ルートフォルダ"),
):
    """プロフィールのルートフォルダを登録"""
    try:
        real = _store.set_root(profile, root)
        typer.secho(f'[config] "{profile}" = {real}', fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"[config] error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

@config_app.command("show")
def config_show(
    profile: str = typer.Argument("default", help="プロフィール名（省略時 default）"),
):
    root = _store.get_root(profile)
    if not root:
        typer.secho(f'[config] "{profile}" は未設定', fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)
    typer.echo(str(root))

@config_app.command("list")
def config_list():
    names = _store.list_profiles()
    if not names:
        typer.echo("（まだプロファイルがありません）")
    else:
        for n in names:
            r = _store.get_root(n)
            typer.echo(f"{n}: {r if r else '(unset)'}")

def main():
    app()

if __name__ == "__main__":
    main()
