from __future__ import annotations
import subprocess
import sys
import shlex
from pathlib import Path

def open_image(path: Path, viewer: str | None = None) -> None:
    """
    画像を外部ビューアで開く。
    viewer を指定すればそれを使い、未指定なら OS 既定アプリで開く。
    """
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    if viewer:
        # 例: viewer="mspaint" とか viewer="code -r"
        cmd = shlex.split(viewer) + [str(path)]
        subprocess.Popen(cmd)  # 非同期でOK
        return

    if sys.platform.startswith("win"):
        # start はシェル組み込み。空タイトル "" が必要
        subprocess.Popen(["cmd", "/c", "start", "", str(path)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
