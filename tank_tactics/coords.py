from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Tuple

@dataclass(frozen=True)
class AxialCoord:
    q: int
    r: int

    def __add__(self, other: "AxialCoord") -> "AxialCoord":
        return AxialCoord(self.q + other.q, self.r + other.r)

    def __sub__(self, other: "AxialCoord") -> "AxialCoord":
        return AxialCoord(self.q - other.q, self.r - other.r)

AXIAL_DIRECTIONS: Tuple[AxialCoord, ...] = (
    AxialCoord(+1, 0), AxialCoord(+1, -1), AxialCoord(0, -1),
    AxialCoord(-1, 0), AxialCoord(-1, +1), AxialCoord(0, +1),
)

def neighbors_axial(c: AxialCoord) -> List[AxialCoord]:
    return [c + d for d in AXIAL_DIRECTIONS]


def axial_to_cube(a: AxialCoord) -> Tuple[int, int, int]:
    x = a.q
    z = a.r
    y = -x - z
    return x, y, z


def cube_to_axial(x: int, y: int, z: int) -> AxialCoord:
    return AxialCoord(x, z)


def hex_round(x: float, y: float, z: float) -> Tuple[int, int, int]:
    rx = round(x)
    ry = round(y)
    rz = round(z)

    x_diff = abs(rx - x)
    y_diff = abs(ry - y)
    z_diff = abs(rz - z)

    if x_diff > y_diff and x_diff > z_diff:
        rx = -ry - rz
    elif y_diff > z_diff:
        ry = -rx - rz
    else:
        rz = -rx - ry
    return rx, ry, rz


def hex_lerp(a: Tuple[int, int, int], b: Tuple[int, int, int], t: float) -> Tuple[float, float, float]:
    ax, ay, az = a
    bx, by, bz = b
    return (ax + (bx - ax) * t, ay + (by - ay) * t, az + (bz - az) * t)


def hex_line(a: AxialCoord, b: AxialCoord) -> List[AxialCoord]:
    # Inclusive of endpoints
    ac = axial_to_cube(a)
    bc = axial_to_cube(b)
    N = hex_distance(a, b)
    if N == 0:
        return [a]
    results: List[AxialCoord] = []
    for i in range(0, N + 1):
        t = 0.0 if N == 0 else i / N
        x, y, z = hex_lerp(ac, bc, t)
        rx, ry, rz = hex_round(x, y, z)
        results.append(cube_to_axial(rx, ry, rz))
    return results


def hex_distance(a: AxialCoord, b: AxialCoord) -> int:
    ax, ay, az = axial_to_cube(a)
    bx, by, bz = axial_to_cube(b)
    return int((abs(ax - bx) + abs(ay - by) + abs(az - bz)) // 2)


def oddr_to_axial(col: int, row: int) -> AxialCoord:
    q = col - (row - (row & 1)) // 2
    r = row
    return AxialCoord(q, r)


def axial_to_oddr(a: AxialCoord) -> Tuple[int, int]:
    col = a.q + (a.r - (a.r & 1)) // 2
    row = a.r
    return col, row