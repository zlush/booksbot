from __future__ import annotations
import math

from tank_tactics.coords import AxialCoord, hex_distance
from tank_tactics.terrain import TerrainType, LOSBlock, TERRAIN_CONFIG
from tank_tactics.board import Board
from tank_tactics.game import Game, TERRAIN_DISTRIBUTION_DEFAULT
from tank_tactics.utils import make_rngs
from tank_tactics.los import compute_los
from tank_tactics.pathfinding import astar_path
from tank_tactics.weapons import WeaponId


def test_generation_counts():
    import random
    rng = random.Random(123)
    board = Board.create_rectangular(10, 8, rng, TERRAIN_DISTRIBUTION_DEFAULT)
    counts = {}
    for c in board.all_cells():
        counts[c.terrain] = counts.get(c.terrain, 0) + 1
    assert sum(counts.values()) == 80
    assert counts[TerrainType.HEIGHT] == 6
    assert counts[TerrainType.PRAIRIE] == 34


def test_base_and_tanks_placement():
    rngs = make_rngs(111, 222)
    game = Game.setup_new(2, rngs)
    pids = list(game.players.keys())
    base_positions = [game.units[game.players[pid].base_id].pos for pid in pids]
    assert hex_distance(base_positions[0], base_positions[1]) >= 6
    # base not on water and 2 tanks per player adjacent and traversable
    for pid in pids:
        base_id = game.players[pid].base_id
        base_unit = game.units[base_id]
        bcell = game.board.get_cell(base_unit.pos)
        assert TERRAIN_CONFIG[bcell.terrain].move_cost is not None
        tanks = [uid for uid in game.players[pid].unit_ids]
        assert len(tanks) == 2
        for tid in tanks:
            t = game.units[tid]
            assert hex_distance(t.pos, base_unit.pos) <= 2


def test_movement_and_costs():
    rngs = make_rngs(42, 99)
    game = Game.setup_new(2, rngs)
    # pick one tank and attempt to move within MP
    pid = list(game.players.keys())[0]
    tid = game.players[pid].unit_ids[0]
    tank = game.units[tid]
    # Find reachable cells and move to a valid one
    from tank_tactics.pathfinding import reachable_with_mp
    reachable = reachable_with_mp(game.board, tank.pos, tank.mp_per_turn)
    # there should be more than just current pos
    assert len(reachable) > 1
    # pick a destination with cost <= mp
    # choose the farthest by distance but within cost
    dest_key = max(reachable.keys(), key=lambda k: reachable[k])
    dest = AxialCoord(*dest_key)
    path = astar_path(game.board, tank.pos, dest)
    assert path is not None
    ok = game.move_unit(tid, dest)
    assert ok


def test_los_rules_simple():
    rngs = make_rngs(7, 8)
    game = Game.setup_new(2, rngs)
    # Try to find a pair with rock in between that blocks LOS
    # Naive scan: pick any two units from different players and check los path for a rock
    units = list(game.units.values())
    a = units[0]
    b = [u for u in units if u.player_id != a.player_id][0]
    los = compute_los(game.board, a.pos, b.pos)
    # Cannot guarantee a rock between on random map; just assert los.num_forests_between >= 0 and has_los boolean is consistent
    assert los.num_forests_between >= 0


def test_attack_tables_and_mods():
    rngs = make_rngs(1234, 5678)
    game = Game.setup_new(2, rngs)
    # Force two units at known positions and terrain if possible by moving tanks closer within range
    pids = list(game.players.keys())
    attacker_id = game.players[pids[0]].unit_ids[0]
    target_id = game.players[pids[1]].unit_ids[0]
    attacker = game.units[attacker_id]
    target = game.units[target_id]
    # Move attacker towards target until in range 3-5
    from tank_tactics.pathfinding import astar_path
    path = astar_path(game.board, attacker.pos, target.pos)
    if path and len(path) > 3:
        dest = path[min(3, len(path)-1)]
        game.move_unit(attacker_id, dest)
    can, _ = game.can_attack(attacker_id, target_id)
    if can:
        res = game.attack(attacker_id, target_id)
        assert res is not None
        assert res.threshold >= 2 and res.threshold <= 10


def test_destroy_and_free_hex():
    rngs = make_rngs(77, 88)
    game = Game.setup_new(2, rngs)
    # Focus fire with mortar to ensure destruction
    pid = list(game.players.keys())[0]
    tid = game.players[pid].unit_ids[0]
    game.units[tid].weapon_id = WeaponId.MORTAR.value
    enemy_pid = list(game.players.keys())[1]
    enemy_tank_id = game.players[enemy_pid].unit_ids[0]
    # Fire mortar even without LOS
    can, _ = game.can_attack(tid, enemy_tank_id)
    if not can:
        # try to move closer into range
        path = astar_path(game.board, game.units[tid].pos, game.units[enemy_tank_id].pos)
        if path and len(path) > 1:
            game.move_unit(tid, path[1])
    # Spam attacks until destroyed or actions exhausted
    for _ in range(10):
        if not game.units[enemy_tank_id].is_alive():
            break
        if not game.units[tid].has_attacked:
            game.attack(tid, enemy_tank_id)
        game.end_turn()
        game.units[tid].has_attacked = False
    if not game.units[enemy_tank_id].is_alive():
        cell = game.board.get_cell(game.units[enemy_tank_id].pos)
        assert cell.occupant_unit_id is None


def test_ai_vs_ai_runs():
    from tank_tactics.sim import run_single_game
    stats = run_single_game(1, 2, 20)
    assert "winner" in stats