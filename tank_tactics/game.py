from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import uuid

from .coords import AxialCoord, hex_distance
from .terrain import TerrainType, TERRAIN_CONFIG
from .board import Board, Cell
from .entities import Player, UnitType, UnitState, Unit, Tank, Base
from .weapons import WeaponId, WEAPONS, Weapon
from .pathfinding import astar_path, reachable_with_mp
from .los import compute_los
from .utils import RNGs, roll_d10

TERRAIN_DISTRIBUTION_DEFAULT: Dict[TerrainType, int] = {
    TerrainType.PRAIRIE: 34,
    TerrainType.FOREST: 16,
    TerrainType.ROCK: 10,
    TerrainType.WATER: 8,
    TerrainType.SWAMP: 6,
    TerrainType.HEIGHT: 6,
}

@dataclass
class AttackResult:
    success: bool
    roll: int
    threshold: int
    damage_main: int
    targets_hit: List[Tuple[str, int]]  # (unit_id, damage)

@dataclass
class Game:
    board: Board
    players: Dict[str, Player]
    units: Dict[str, Unit]
    current_player_id: str
    round_index: int
    rngs: RNGs
    history: List[Dict] = field(default_factory=list)
    mode: str = "PVP"

    @staticmethod
    def setup_new(num_players: int, rngs: RNGs) -> "Game":
        assert 2 <= num_players <= 4
        width, height = 10, 8  # 80 hex in odd-r rectangle
        board = Board.create_rectangular(width, height, rngs.map_rng, TERRAIN_DISTRIBUTION_DEFAULT)

        # Players
        players: Dict[str, Player] = {}
        for i in range(num_players):
            pid = f"P{i+1}"
            players[pid] = Player(id=pid, name=f"Jugador {i+1}", color_hex=["#FF0000","#0000FF","#00AA00","#AA00AA"][i], control="IA")

        # Base placement: farthest with min distance >= 6
        base_positions = board.find_farthest_positions(num_players, min_hex_distance=6)
        # If any position is water, move to nearest traversable
        fixed_positions: List[AxialCoord] = []
        for pos in base_positions:
            cell = board.get_cell(pos)
            if not cell or TERRAIN_CONFIG[cell.terrain].move_cost is None:
                nearest = board.nearest_traversable(pos)
                assert nearest, "No traversable cell found for base placement"
                fixed_positions.append(nearest.coord)
            else:
                fixed_positions.append(pos)

        units: Dict[str, Unit] = {}
        # Create bases and two tanks per player
        for i, pid in enumerate(players.keys()):
            base_pos = fixed_positions[i]
            base_id = f"B-{pid}"
            base_unit = Base(id=base_id, player_id=pid, type=UnitType.BASE, hp_current=40, hp_max=40,
                             pos=base_pos, weapon_id=WEAPONS[WeaponId.NORMAL].id.value, mp_per_turn=3)
            units[base_id] = base_unit
            players[pid].base_id = base_id

            # occupy cell
            bcell = board.get_cell(base_pos)
            assert bcell and not bcell.is_occupied
            bcell.occupant_unit_id = base_id

            # Place 2 tanks adjacent transitables
            neighbors = board.neighbors(base_pos)
            def terrain_priority(t: TerrainType) -> int:
                if t == TerrainType.PRAIRIE:
                    return 3
                if t == TerrainType.FOREST:
                    return 2
                if t == TerrainType.SWAMP:
                    return 1
                if t == TerrainType.ROCK:
                    return 0
                return -999
            candidates = [c for c in neighbors if c.is_traversable()]
            candidates.sort(key=lambda c: (terrain_priority(c.terrain), rngs.map_rng.random()), reverse=True)
            placed = 0
            used_coords: List[AxialCoord] = []
            for c in candidates:
                if placed >= 2:
                    break
                if c.coord in used_coords:
                    continue
                tank_id = f"T{placed+1}-{pid}"
                tank_unit = Tank(id=tank_id, player_id=pid, type=UnitType.TANK, hp_current=20, hp_max=20,
                                 pos=c.coord, weapon_id=WEAPONS[WeaponId.NORMAL].id.value, mp_per_turn=5)
                units[tank_id] = tank_unit
                players[pid].unit_ids.append(tank_id)
                c.occupant_unit_id = tank_id
                used_coords.append(c.coord)
                placed += 1
            # If not enough adjacent, search nearby
            if placed < 2:
                for cell in board.all_cells():
                    if placed >= 2:
                        break
                    if cell.is_traversable() and hex_distance(cell.coord, base_pos) == 2 and not cell.is_occupied:
                        tank_id = f"T{placed+1}-{pid}"
                        tank_unit = Tank(id=tank_id, player_id=pid, type=UnitType.TANK, hp_current=20, hp_max=20,
                                         pos=cell.coord, weapon_id=WEAPONS[WeaponId.NORMAL].id.value, mp_per_turn=5)
                        units[tank_id] = tank_unit
                        players[pid].unit_ids.append(tank_id)
                        cell.occupant_unit_id = tank_id
                        placed += 1
            assert placed == 2, "Failed to place two tanks per player"

        current_player_id = list(players.keys())[0]
        return Game(board=board, players=players, units=units, current_player_id=current_player_id, round_index=1, rngs=rngs)

    def reset_turn(self, player_id: str) -> None:
        for u in self.units.values():
            if u.player_id == player_id and u.is_alive():
                u.has_attacked = False
                # movement points are per action; not stored; use mp_per_turn

    def cell_by_unit(self, unit_id: str) -> Cell:
        unit = self.units[unit_id]
        cell = self.board.get_cell(unit.pos)
        assert cell is not None
        return cell

    def move_unit(self, unit_id: str, dest: AxialCoord) -> bool:
        unit = self.units[unit_id]
        if not unit.is_alive():
            return False
        path = astar_path(self.board, unit.pos, dest)
        if path is None:
            return False
        # compute cost along path excluding start
        cur_cell = self.board.get_cell(unit.pos)
        assert cur_cell is not None
        cost = 0
        ok = True
        for step in path[1:]:
            step_cell = self.board.get_cell(step)
            assert step_cell is not None
            if not step_cell.is_traversable():
                ok = False
                break
            step_cost = step_cell.move_cost_from(cur_cell)
            if step_cost is None:
                ok = False
                break
            cost += step_cost
            cur_cell = step_cell
        if not ok or cost > unit.mp_per_turn:
            return False
        # move
        start_cell = self.board.get_cell(unit.pos)
        assert start_cell is not None
        start_cell.occupant_unit_id = None
        end_cell = self.board.get_cell(dest)
        assert end_cell is not None and not end_cell.is_occupied
        end_cell.occupant_unit_id = unit.id
        unit.pos = dest
        self.history.append({"type":"move","unit":unit.id,"from":(start_cell.coord.q,start_cell.coord.r),"to":(dest.q,dest.r)})
        return True

    def get_weapon(self, unit: Unit) -> Weapon:
        for w in WEAPONS.values():
            if w.id.value == unit.weapon_id:
                return w
        raise KeyError(unit.weapon_id)

    def can_attack(self, attacker_id: str, target_id: str) -> Tuple[bool, Optional[str]]:
        attacker = self.units[attacker_id]
        target = self.units[target_id]
        if not attacker.is_alive() or not target.is_alive():
            return False, "attacker or target dead"
        if attacker.has_attacked:
            return False, "attacker already attacked"
        dist = hex_distance(attacker.pos, target.pos)
        weapon = self.get_weapon(attacker)
        if dist < weapon.min_range or dist > weapon.max_range:
            return False, "out of range"
        if not weapon.ignores_los:
            los = compute_los(self.board, attacker.pos, target.pos)
            if not los.has_los:
                return False, "no los"
        return True, None

    def compute_attack_threshold(self, attacker: Unit, target: Unit) -> Tuple[int, Dict[str,int]]:
        dist = hex_distance(attacker.pos, target.pos)
        weapon = self.get_weapon(attacker)
        base_U = weapon.thresholds_by_distance.get(dist)
        if base_U is None:
            # Should already be range-validated
            base_U = 10
        mods: Dict[str, int] = {}
        # Terrain defense mods on target (objective en roca/bosque)
        tcell = self.board.get_cell(target.pos)
        assert tcell is not None
        tcfg = TERRAIN_CONFIG[tcell.terrain]
        if tcell.terrain == TerrainType.FOREST:
            mods["objetivo_en_bosque"] = 1
        if tcfg.defense_mod != 0:
            mods["objetivo_en_roca" if tcell.terrain == TerrainType.ROCK else "defensa_terreno"] = tcfg.defense_mod
        # Forest in between (only if using LoS weapons)
        los_forests = 0
        weapon = self.get_weapon(attacker)
        if not weapon.ignores_los:
            los = compute_los(self.board, attacker.pos, target.pos)
            los_forests = los.num_forests_between
            if los_forests == 1:
                mods["bosque_intermedio"] = 1
        # Height relative
        acell = self.board.get_cell(attacker.pos)
        assert acell is not None
        if TERRAIN_CONFIG[acell.terrain].is_height and not TERRAIN_CONFIG[tcell.terrain].is_height:
            mods["atacante_en_altura"] = -1
        if TERRAIN_CONFIG[tcell.terrain].is_height and not TERRAIN_CONFIG[acell.terrain].is_height:
            mods["objetivo_en_altura"] = 1
        # Sum and clamp [2..10]
        U = base_U + sum(mods.values())
        U = max(2, min(10, U))
        return U, mods

    def attack(self, attacker_id: str, target_id: str) -> Optional[AttackResult]:
        can, reason = self.can_attack(attacker_id, target_id)
        if not can:
            return None
        attacker = self.units[attacker_id]
        target = self.units[target_id]
        weapon = self.get_weapon(attacker)
        U, mods = self.compute_attack_threshold(attacker, target)
        roll = roll_d10(self.rngs.dice_rng)
        success = roll >= U
        total_damage_main = weapon.base_damage if success else 0
        targets_hit: List[Tuple[str, int]] = []
        if success:
            self.apply_damage(target_id, weapon.base_damage)
            targets_hit.append((target_id, weapon.base_damage))
            # Mortar splash
            if weapon.splash_damage > 0:
                for ncell in self.board.neighbors(target.pos):
                    if ncell.occupant_unit_id and ncell.occupant_unit_id in self.units:
                        if self.units[ncell.occupant_unit_id].is_alive():
                            self.apply_damage(ncell.occupant_unit_id, weapon.splash_damage)
                            targets_hit.append((ncell.occupant_unit_id, weapon.splash_damage))
        attacker.has_attacked = True
        self.history.append({
            "type":"attack","attacker":attacker_id,"target":target_id,
            "roll":roll,"U":U,"mods":mods,"success":success,
            "damage":total_damage_main,
        })
        return AttackResult(success=success, roll=roll, threshold=U, damage_main=total_damage_main, targets_hit=targets_hit)

    def apply_damage(self, unit_id: str, dmg: int) -> None:
        unit = self.units[unit_id]
        if not unit.is_alive():
            return
        unit.hp_current -= dmg
        if unit.hp_current <= 0:
            unit.hp_current = 0
            unit.state = UnitState.DESTROYED
            # free cell
            c = self.board.get_cell(unit.pos)
            if c:
                c.occupant_unit_id = None
            self.history.append({"type":"destroyed","unit":unit_id})

    def end_turn(self) -> None:
        # Next player
        ids = list(self.players.keys())
        idx = ids.index(self.current_player_id)
        next_idx = (idx + 1) % len(ids)
        if next_idx == 0:
            self.round_index += 1
        self.current_player_id = ids[next_idx]
        self.reset_turn(self.current_player_id)
        self.history.append({"type":"end_turn","current":self.current_player_id,"round":self.round_index})

    def victory_state(self) -> Optional[str]:
        # Return winner player_id or "EMPATE" or None
        alive_bases = {}
        for pid, p in self.players.items():
            if p.base_id and self.units[p.base_id].is_alive():
                alive_bases[pid] = True
        if len(alive_bases) == 1:
            return list(alive_bases.keys())[0]
        if len(alive_bases) == 0:
            return "EMPATE"
        return None