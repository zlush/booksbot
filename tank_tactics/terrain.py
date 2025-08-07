from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict

class TerrainType(Enum):
    PRAIRIE = "pradera"
    FOREST = "bosque"
    SWAMP = "pantano"
    ROCK = "roca"
    WATER = "agua"
    HEIGHT = "altura"

class LOSBlock(Enum):
    NONE = "ninguno"
    PARTIAL = "parcial"
    TOTAL = "total"

@dataclass(frozen=True)
class TerrainConfig:
    move_cost: int | None  # None means intransitable
    los_block: LOSBlock
    defense_mod: int  # adds to hit threshold when target is on this terrain
    is_height: bool

TERRAIN_CONFIG: Dict[TerrainType, TerrainConfig] = {
    TerrainType.PRAIRIE: TerrainConfig(move_cost=1, los_block=LOSBlock.NONE, defense_mod=0, is_height=False),
    TerrainType.FOREST: TerrainConfig(move_cost=2, los_block=LOSBlock.PARTIAL, defense_mod=0, is_height=False),
    TerrainType.SWAMP: TerrainConfig(move_cost=2, los_block=LOSBlock.NONE, defense_mod=0, is_height=False),
    TerrainType.ROCK: TerrainConfig(move_cost=2, los_block=LOSBlock.TOTAL, defense_mod=1, is_height=False),
    TerrainType.WATER: TerrainConfig(move_cost=None, los_block=LOSBlock.NONE, defense_mod=0, is_height=False),
    TerrainType.HEIGHT: TerrainConfig(move_cost=2, los_block=LOSBlock.TOTAL, defense_mod=0, is_height=True),
}