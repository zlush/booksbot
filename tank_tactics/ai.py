from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .coords import AxialCoord, hex_distance
from .board import Board
from .entities import Unit, UnitType
from .game import Game
from .pathfinding import reachable_with_mp
from .weapons import WEAPONS
from .los import compute_los
from .terrain import TerrainType

@dataclass
class AIWeights:
    W_hit: float = 1.0
    W_dmg: float = 0.5
    W_kill: float = 2.0
    W_risk: float = 0.7
    W_dist: float = 0.05
    W_cover: float = 0.2

class GreedyAI:
    def __init__(self, weights: AIWeights | None = None) -> None:
        self.weights = weights or AIWeights()

    def decide_turn(self, game: Game, player_id: str) -> None:
        # For each unit alive: choose best action (move+attack/attack/move/pass)
        for unit in list(game.units.values()):
            if unit.player_id != player_id or not unit.is_alive():
                continue
            self.act_for_unit(game, unit)

    def act_for_unit(self, game: Game, unit: Unit) -> None:
        # Candidate positions: reachable within MP, plus staying put
        reachable = reachable_with_mp(game.board, unit.pos, unit.mp_per_turn)
        candidate_coords = [AxialCoord(q, r) for (q, r) in reachable.keys()]
        if unit.pos not in candidate_coords:
            candidate_coords.append(unit.pos)

        best_score = -1e18
        best_action: Tuple[AxialCoord, Optional[str]] = (unit.pos, None)  # (move_to, target_id)

        enemies = [u for u in game.units.values() if u.player_id != unit.player_id and u.is_alive()]
        my_base = game.players[unit.player_id].base_id
        enemy_bases = [game.players[pid].base_id for pid in game.players if pid != unit.player_id]
        key_targets = [tid for tid in enemy_bases if tid is not None]

        for pos in candidate_coords:
            # Temporarily consider unit at pos for scoring
            # List possible attacks
            best_attack_target: Optional[str] = None
            best_attack_score = -1e9
            for e in enemies:
                dist = hex_distance(pos, e.pos)
                weapon = game.get_weapon(unit)
                if dist < weapon.min_range or dist > weapon.max_range:
                    continue
                if not weapon.ignores_los and not compute_los(game.board, pos, e.pos).has_los:
                    continue
                # Temporarily simulate attacker at pos for threshold
                original_pos = unit.pos
                unit.pos = pos
                U, _mods = game.compute_attack_threshold(unit, e)
                unit.pos = original_pos
                p_hit = max(0.0, min(1.0, (11 - U) / 10.0))
                expected_damage = weapon.base_damage * p_hit
                p_kill = 1.0 if e.hp_current - expected_damage <= 0 else 0.0
                score = (self.weights.W_hit * p_hit +
                         self.weights.W_dmg * expected_damage +
                         self.weights.W_kill * p_kill)
                if score > best_attack_score:
                    best_attack_score = score
                    best_attack_target = e.id

            # Risk: enemies that can hit this pos
            risk = 0.0
            for e in enemies:
                weapon_e = game.get_weapon(e)
                dist_e = hex_distance(e.pos, pos)
                if dist_e < weapon_e.min_range or dist_e > weapon_e.max_range:
                    continue
                if not weapon_e.ignores_los and not compute_los(game.board, e.pos, pos).has_los:
                    continue
                # Temporarily simulate target at pos for threshold
                original_pos = unit.pos
                unit.pos = pos
                Ue, _ = game.compute_attack_threshold(e, unit)
                unit.pos = original_pos
                p_hit_e = max(0.0, min(1.0, (11 - Ue) / 10.0))
                risk += p_hit_e

            # Distance to key enemy target (nearest base)
            dist_to_key = min((hex_distance(pos, game.units[tid].pos) for tid in key_targets), default=0)

            # Cover bonus if ending on forest or height
            cell = game.board.get_cell(pos)
            assert cell is not None
            cover = 1.0 if cell.terrain in (TerrainType.FOREST, TerrainType.HEIGHT) else 0.0

            total = best_attack_score - self.weights.W_risk * risk - self.weights.W_dist * dist_to_key + self.weights.W_cover * cover

            if total > best_score:
                best_score = total
                best_action = (pos, best_attack_target)

        # Execute: move if needed, then attack if available
        move_to, target_id = best_action
        if move_to != unit.pos:
            game.move_unit(unit.id, move_to)
        if target_id and not unit.has_attacked:
            # Ensure at attack time we are using the latest pos
            game.attack(unit.id, target_id)