# src/iref/models.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal, TypedDict

Status = Literal["queued", "skipped-duplicate"]

class RefItemDict(TypedDict):
    path: str
    size: int
    mtime: float
    phash: str
    status: Status

@dataclass
class RefItem:
    path: Path
    size: int
    mtime: float
    phash: str
    status: Status = "queued"

    def to_dict(self) -> RefItemDict:
        return {
            "path": str(self.path),
            "size": self.size,
            "mtime": self.mtime,
            "phash": self.phash,
            "status": self.status,
        }
