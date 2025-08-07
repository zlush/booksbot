from __future__ import annotations
import random
from dataclasses import dataclass

@dataclass
class RNGs:
    map_rng: random.Random
    dice_rng: random.Random


def make_rngs(seed_mapa: int | None, seed_dados: int | None) -> RNGs:
    map_rng = random.Random(seed_mapa)
    dice_rng = random.Random(seed_dados)
    return RNGs(map_rng=map_rng, dice_rng=dice_rng)


def roll_d10(rng: random.Random) -> int:
    return rng.randint(1, 10)