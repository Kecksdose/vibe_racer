from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MapData:
    width: int
    height: int
    tiles: list[list[str]]
    legend: dict[str, str]
    start: tuple[int, int]
    finish: tuple[int, int]
    checkpoints: list[tuple[int, int]]
    start_angle: float = 0.0

    def tile_at(self, x: int, y: int) -> str:
        return self.tiles[y][x]

    def is_wall(self, x: int, y: int) -> bool:
        return self.legend.get(self.tile_at(x, y)) == "wall"


def load_map(path: Path) -> MapData:
    raw = json.loads(path.read_text(encoding="utf-8"))
    width = int(raw["width"])
    height = int(raw["height"])
    tiles: list[list[str]] = raw["tiles"]
    legend: dict[str, str] = raw["legend"]

    _validate_grid(width, height, tiles)
    start = _find_tile(tiles, "3")
    finish = _find_tile(tiles, "4")
    if start is None or finish is None:
        raise ValueError("Map must include start (3) and finish (4) tiles")

    checkpoints = _find_tiles(tiles, "5")

    start_angle = float(raw.get("start_angle", 0.0))
    return MapData(
        width=width,
        height=height,
        tiles=tiles,
        legend=legend,
        start=start,
        finish=finish,
        checkpoints=checkpoints,
        start_angle=start_angle,
    )


def _validate_grid(width: int, height: int, tiles: list[list[str]]) -> None:
    if len(tiles) != height:
        raise ValueError("Tile rows must match height")
    for row in tiles:
        if len(row) != width:
            raise ValueError("Tile columns must match width")


def _find_tile(tiles: list[list[str]], tile_id: str) -> tuple[int, int] | None:
    for y, row in enumerate(tiles):
        for x, value in enumerate(row):
            if value == tile_id:
                return (x, y)
    return None


def _find_tiles(tiles: list[list[str]], tile_id: str) -> list[tuple[int, int]]:
    results: list[tuple[int, int]] = []
    for y, row in enumerate(tiles):
        for x, value in enumerate(row):
            if value == tile_id:
                results.append((x, y))
    return results
