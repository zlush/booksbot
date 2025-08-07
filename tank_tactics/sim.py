from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple
import json
import csv
import os

from .utils import make_rngs
from .game import Game
from .ai import GreedyAI

@dataclass
class SimParams:
    games: int
    seed_mapa: int
    seed_dados: int
    max_rounds: int = 200


def run_single_game(seed_mapa: int, seed_dados: int, max_rounds: int = 200) -> Dict:
    rngs = make_rngs(seed_mapa, seed_dados)
    game = Game.setup_new(num_players=2, rngs=rngs)
    ai = GreedyAI()

    winner = None
    for _ in range(max_rounds * len(game.players)):
        current = game.current_player_id
        ai.decide_turn(game, current)
        winner = game.victory_state()
        if winner is not None:
            break
        game.end_turn()
    if winner is None:
        winner = "EMPATE"
    stats = {
        "winner": winner,
        "rounds": game.round_index,
        "history_len": len(game.history),
    }
    return stats


def run_simulations(params: SimParams, out_dir: str = "out") -> Tuple[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    results: List[Dict] = []
    for i in range(params.games):
        stats = run_single_game(params.seed_mapa + i, params.seed_dados + i, params.max_rounds)
        results.append(stats)
    # Export JSON
    json_path = os.path.join(out_dir, "results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    # Export CSV
    csv_path = os.path.join(out_dir, "results.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["winner","rounds","history_len"])
        writer.writeheader()
        writer.writerows(results)
    return json_path, csv_path