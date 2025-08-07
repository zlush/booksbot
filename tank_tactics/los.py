from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple

from .coords import AxialCoord, hex_line
from .board import Board
from .terrain import TerrainType, TERRAIN_CONFIG, LOSBlock

@dataclass
class LOSResult:
    has_los: bool
    num_forests_between: int


def compute_los(board: Board, a: AxialCoord, b: AxialCoord) -> LOSResult:
    if a == b:
        return LOSResult(True, 0)
    line: List[AxialCoord] = hex_line(a, b)
    # exclude endpoints
    intermediates = line[1:-1]
    total_block = 0
    forests = 0
    for c in intermediates:
        cell = board.get_cell(c)
        if not cell:
            continue
        cfg = TERRAIN_CONFIG[cell.terrain]
        if cfg.los_block == LOSBlock.TOTAL:
            total_block += 1
        elif cfg.los_block == LOSBlock.PARTIAL:
            forests += 1
    if total_block >= 1:
        return LOSResult(False, forests)
    if forests >= 2:
        return LOSResult(False, forests)
    return LOSResult(True, forests)