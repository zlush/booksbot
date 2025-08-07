from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import random

from .coords import AxialCoord, neighbors_axial, oddr_to_axial, axial_to_oddr
from .terrain import TerrainType, TERRAIN_CONFIG

@dataclass
class Cell:
    id: int
    coord: AxialCoord
    terrain: TerrainType
    occupant_unit_id: Optional[str] = None

    @property
    def is_occupied(self) -> bool:
        return self.occupant_unit_id is not None

    def is_traversable(self) -> bool:
        cfg = TERRAIN_CONFIG[self.terrain]
        return cfg.move_cost is not None and not self.is_occupied

    def move_cost_from(self, from_cell: "Cell") -> Optional[int]:
        cfg = TERRAIN_CONFIG[self.terrain]
        if cfg.move_cost is None:
            return None
        cost = cfg.move_cost
        if cfg.is_height and not TERRAIN_CONFIG[from_cell.terrain].is_height:
            cost += 1
        return cost

@dataclass
class Board:
    width: int
    height: int
    cells: Dict[Tuple[int, int], Cell] = field(default_factory=dict)  # keyed by (q,r)

    @staticmethod
    def create_rectangular(width: int, height: int, rng: random.Random, terrain_counts: Dict[TerrainType, int]) -> "Board":
        total = width * height
        assert total == sum(terrain_counts.values()), "Terrain counts must sum to board area"
        tiles: List[TerrainType] = []
        for t, n in terrain_counts.items():
            tiles += [t] * n
        rng.shuffle(tiles)
        board = Board(width, height)
        idx = 0
        cell_id = 0
        for row in range(height):
            for col in range(width):
                coord = oddr_to_axial(col, row)
                terrain = tiles[idx]
                idx += 1
                board.cells[(coord.q, coord.r)] = Cell(id=cell_id, coord=coord, terrain=terrain)
                cell_id += 1
        return board

    def get_cell(self, a: AxialCoord) -> Optional[Cell]:
        return self.cells.get((a.q, a.r))

    def neighbors(self, a: AxialCoord) -> List[Cell]:
        cells: List[Cell] = []
        for n in neighbors_axial(a):
            c = self.get_cell(n)
            if c is not None:
                cells.append(c)
        return cells

    def all_cells(self) -> List[Cell]:
        return list(self.cells.values())

    def find_farthest_positions(self, k: int, min_hex_distance: int) -> List[AxialCoord]:
        # Greedy: pick first a corner-like positions, then farthest from chosen
        candidates = [c.coord for c in self.all_cells() if TERRAIN_CONFIG[c.terrain].move_cost is not None]
        if not candidates:
            return []
        # Seed with extreme corners in offset space for better spread
        extreme_offsets = [(0,0),(self.width-1,0),(0,self.height-1),(self.width-1,self.height-1)]
        seed: List[AxialCoord] = []
        for col,row in extreme_offsets:
            coord = oddr_to_axial(col,row)
            if self.get_cell(coord) and TERRAIN_CONFIG[self.get_cell(coord).terrain].move_cost is not None:
                seed.append(coord)
        chosen: List[AxialCoord] = []
        seed = [s for s in seed if s in candidates]
        while seed and len(chosen) < k:
            chosen.append(seed.pop(0))
        # Greedily add farthest that satisfies min distance
        def ok(c: AxialCoord) -> bool:
            from .coords import hex_distance
            return all(hex_distance(c, o) >= min_hex_distance for o in chosen)
        remaining = [c for c in candidates if c not in chosen]
        from .coords import hex_distance
        while len(chosen) < k and remaining:
            # pick the cell maximizing min distance to chosen
            best = None
            best_d = -1
            for c in remaining:
                if chosen:
                    d = min(hex_distance(c, o) for o in chosen)
                else:
                    d = 999
                if d > best_d and ok(c):
                    best = c
                    best_d = d
            if best is None:
                break
            chosen.append(best)
            remaining.remove(best)
        return chosen

    def nearest_traversable(self, start: AxialCoord) -> Optional[Cell]:
        # BFS to nearest traversable cell
        from collections import deque
        seen = set()
        dq = deque([start])
        while dq:
            cur = dq.popleft()
            if cur in seen:
                continue
            seen.add(cur)
            cell = self.get_cell(cur)
            if cell and cell.is_traversable():
                return cell
            for n in neighbors_axial(cur):
                if (n.q, n.r) in self.cells:
                    dq.append(n)
        return None