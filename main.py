from __future__ import annotations
import argparse

from tank_tactics.utils import make_rngs
from tank_tactics.game import Game
from tank_tactics.ai import GreedyAI
from tank_tactics.sim import run_simulations, SimParams


def main():
    parser = argparse.ArgumentParser(description="Tank Tactics (GDD) - CLI")
    parser.add_argument("--mode", choices=["pve","sim"], default="sim")
    parser.add_argument("--seed-mapa", type=int, default=123)
    parser.add_argument("--seed-dados", type=int, default=456)
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--max-rounds", type=int, default=200)
    args = parser.parse_args()

    if args.mode == "sim":
        params = SimParams(games=args.games, seed_mapa=args.seed_mapa, seed_dados=args.seed_dados, max_rounds=args.max_rounds)
        json_path, csv_path = run_simulations(params)
        print(f"Exported metrics to {json_path} and {csv_path}")
        return

    if args.mode == "pve":
        rngs = make_rngs(args.seed_mapa, args.seed_dados)
        game = Game.setup_new(num_players=2, rngs=rngs)
        ai = GreedyAI()
        print("Starting PVE minimal mode. You control Player 1 tanks. Commands: list, move <unit> q r, attack <attacker> <target>, end")
        while True:
            print(f"Turno de {game.current_player_id}, Ronda {game.round_index}")
            if game.current_player_id == "P1":
                cmd = input("> ").strip()
                if cmd == "list":
                    for u in game.units.values():
                        print(u)
                    continue
                if cmd.startswith("move "):
                    parts = cmd.split()
                    uid, q, r = parts[1], int(parts[2]), int(parts[3])
                    ok = game.move_unit(uid, __import__('tank_tactics').tank_tactics.coords.AxialCoord(q, r))
                    print("ok" if ok else "fail")
                    continue
                if cmd.startswith("attack "):
                    parts = cmd.split()
                    aid, tid = parts[1], parts[2]
                    res = game.attack(aid, tid)
                    print(res)
                    continue
                if cmd == "end":
                    game.end_turn()
                    continue
            else:
                ai.decide_turn(game, game.current_player_id)
                game.end_turn()
            winner = game.victory_state()
            if winner is not None:
                print(f"Winner: {winner}")
                break

if __name__ == "__main__":
    main()