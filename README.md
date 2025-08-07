# Tank Tactics (GDD Implementation)

Turn-based hex tactics engine implementing the provided Spanish GDD. CLI oriented; includes AI vs AI simulation and acceptance tests.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q
python main.py --mode sim --games 10 --seed-mapa 123 --seed-dados 456
```

## Modes
- Human vs AI (text, minimal): `--mode pve`
- AI vs AI simulation: `--mode sim` (exports metrics JSON/CSV to `out/`)

Reproducibility via `--seed-mapa` and `--seed-dados`.