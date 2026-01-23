from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ReplayData:
    inputs: list[dict[str, bool]]
    meta: dict[str, Any]


def save_replay(
    path: Path, inputs: list[dict[str, bool]], meta: dict[str, Any]
) -> None:
    payload = {"meta": meta, "inputs": inputs}
    path.write_text(json.dumps(payload), encoding="utf-8")


def load_replay(path: Path) -> ReplayData:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return ReplayData(inputs=payload, meta={})
    return ReplayData(inputs=payload.get("inputs", []), meta=payload.get("meta", {}))
