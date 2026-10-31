# LoopLab

LoopLab is a local experiment loop for Fashion-MNIST. A transparent, rule-based agent proposes one untried configuration change, a background worker trains it, and the run is promoted only when its validation accuracy beats the current best.

## Run locally

Requirements: Python 3.10+ and Node 18+. The first training run downloads Fashion-MNIST from the public torchvision mirror (about 30 MB).

From the project root, run one command:

```bash
./start.sh
```

The script creates the Python virtual environment, installs backend and dashboard dependencies on first launch, and starts both services. It requires Python 3 and Node.js/npm. Press Ctrl+C to stop them.

Open http://localhost:5173. Click **Run baseline** once to initialize the leaderboard. Subsequent runs can be proposed by the agent or started manually. The API runs on port 8001 (API docs: http://localhost:8001/docs) to avoid common local development server conflicts. Training runs use a small, fixed Fashion-MNIST subset and short epoch budget to keep the local demo quick. Checkpoints and the SQLite database live under `backend/data/` and are ignored by git.

## What happens in a run

The baseline is a one-hidden-layer MLP. Each agent proposal changes exactly one setting from a small, inspectable search space. Runs train on the same fixed subset and seed. The API stores status, configuration, parent run, validation accuracy, elapsed time, proposal explanation, and promotion decision. Only one run may train at a time.

Fashion-MNIST is downloaded on first use. To disable downloads, set `LOOPLAB_ALLOW_DOWNLOAD=0`; training will report a clear error if the data is not cached.

## Layout

- `backend/app/` — FastAPI API, SQLite tracking, proposer, and PyTorch trainer
- `frontend/` — React + Vite dashboard
- `backend/data/` — local database, dataset cache, and checkpoints (not committed)
