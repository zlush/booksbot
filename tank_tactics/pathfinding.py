from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import heapq

from .coords import AxialCoord, hex_distance
from .board import Board, Cell
from .terrain import TERRAIN_CONFIG

@dataclass
class Node:
    coord: AxialCoord
    g: int
    f: int
    parent: Optional["Node"]


def astar_path(board: Board, start: AxialCoord, goal: AxialCoord) -> Optional[List[AxialCoord]]:
    if start == goal:
        return [start]
    start_cell = board.get_cell(start)
    goal_cell = board.get_cell(goal)
    if start_cell is None or goal_cell is None:
        return None
    if not goal_cell.is_traversable():
        return None

    open_heap: List[Tuple[int, int, Node]] = []
    start_node = Node(start, g=0, f=hex_distance(start, goal), parent=None)
    heapq.heappush(open_heap, (start_node.f, 0, start_node))
    g_best: Dict[Tuple[int,int], int] = {(start.q, start.r): 0}
    counter = 1

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        if current.coord == goal:
            # reconstruct
            path: List[AxialCoord] = []
            node = current
            while node is not None:
                path.append(node.coord)
                node = node.parent
            return list(reversed(path))
        current_cell = board.get_cell(current.coord)
        assert current_cell is not None
        for ncell in board.neighbors(current.coord):
            if not ncell.is_traversable():
                continue
            step_cost_opt = ncell.move_cost_from(current_cell)
            if step_cost_opt is None:
                continue
            tentative_g = current.g + step_cost_opt
            key = (ncell.coord.q, ncell.coord.r)
            if key not in g_best or tentative_g < g_best[key]:
                g_best[key] = tentative_g
                f = tentative_g + hex_distance(ncell.coord, goal)
                heapq.heappush(open_heap, (f, counter, Node(ncell.coord, tentative_g, f, current)))
                counter += 1
    return None


def reachable_with_mp(board: Board, start: AxialCoord, mp: int) -> Dict[Tuple[int,int], int]:
    # Dijkstra limited by mp
    import heapq
    dist: Dict[Tuple[int,int], int] = {(start.q, start.r): 0}
    heap: List[Tuple[int, Tuple[int,int]]] = [(0, (start.q, start.r))]
    while heap:
        cur_cost, key = heapq.heappop(heap)
        q, r = key
        if cur_cost > mp:
            continue
        cur_coord = AxialCoord(q, r)
        cur_cell = board.get_cell(cur_coord)
        assert cur_cell is not None
        for ncell in board.neighbors(cur_coord):
            if not ncell.is_traversable():
                continue
            step = ncell.move_cost_from(cur_cell)
            if step is None:
                continue
            new_cost = cur_cost + step
            nkey = (ncell.coord.q, ncell.coord.r)
            if new_cost <= mp and (nkey not in dist or new_cost < dist[nkey]):
                dist[nkey] = new_cost
                heapq.heappush(heap, (new_cost, nkey))
    return dist