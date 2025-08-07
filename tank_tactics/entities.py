from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .coords import AxialCoord

class UnitType(Enum):
    BASE = "base"
    TANK = "tanque"

class UnitState(Enum):
    NORMAL = "normal"
    DESTROYED = "destruido"

@dataclass
class Player:
    id: str
    name: str
    color_hex: str
    control: str  # "humano" or "IA"
    base_id: Optional[str] = None
    unit_ids: List[str] = field(default_factory=list)

@dataclass
class Unit:
    id: str
    player_id: str
    type: UnitType
    hp_current: int
    hp_max: int
    pos: AxialCoord
    weapon_id: str
    mp_per_turn: int
    has_attacked: bool = False
    state: UnitState = UnitState.NORMAL

    def is_alive(self) -> bool:
        return self.state == UnitState.NORMAL and self.hp_current > 0

@dataclass
class Tank(Unit):
    pass

@dataclass
class Base(Unit):
    pass