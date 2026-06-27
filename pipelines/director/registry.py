"""The work-project registry — projects as data, not identity.

Loads config/director_registry.json (overridable via DIRECTOR_REGISTRY). Adding a
project is a data edit, not a code change. Could later sync from /opt/_host.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

_DEFAULT = Path(__file__).resolve().parents[2] / "config" / "director_registry.json"


@dataclass
class Project:
    name: str
    path: str
    note: str = ""


def load_registry(path: Path | None = None) -> list[Project]:
    p = path or Path(os.environ.get("DIRECTOR_REGISTRY", str(_DEFAULT)))
    data = json.loads(p.read_text())
    return [
        Project(name=item["name"], path=item["path"], note=item.get("note", ""))
        for item in data.get("projects", [])
    ]
