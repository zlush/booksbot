from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

class WeaponId(Enum):
    NORMAL = "Normal"
    SNIPER = "Sniper"
    MORTAR = "Mortero"

@dataclass(frozen=True)
class Weapon:
    id: WeaponId
    name: str
    base_damage: int
    min_range: int
    max_range: int
    thresholds_by_distance: Dict[int, int]  # distance: D10 threshold U
    ignores_los: bool = False
    splash_damage: int = 0

# Threshold tables per GDD §5.2
SNIPER_THRESH = {1:2,2:3,3:4,4:5,5:6,6:7}
NORMAL_THRESH = {1:2,2:4,3:6,4:7,5:8,6:9}
MORTAR_THRESH = {2:5,3:6,4:7,5:8,6:9}

WEAPONS: Dict[WeaponId, Weapon] = {
    WeaponId.SNIPER: Weapon(WeaponId.SNIPER, "Sniper", base_damage=3, min_range=1, max_range=6, thresholds_by_distance=SNIPER_THRESH),
    WeaponId.NORMAL: Weapon(WeaponId.NORMAL, "Normal", base_damage=4, min_range=1, max_range=6, thresholds_by_distance=NORMAL_THRESH),
    WeaponId.MORTAR: Weapon(WeaponId.MORTAR, "Mortero", base_damage=6, min_range=2, max_range=6, thresholds_by_distance=MORTAR_THRESH, ignores_los=True, splash_damage=3),
}