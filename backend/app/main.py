from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import db
from .agent import propose
from .trainer import train

app = FastAPI(title="LoopLab API", description="A local, closed-loop ML experimentation workbench.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="looplab-train")
start_lock = Lock()
BASELINE = {"learning_rate": 0.001, "batch_size": 128, "hidden_units": 128, "dropout": 0.1, "optimizer": "Adam", "epochs": 3, "seed": 42}


class RunRequest(BaseModel):
    config: dict = Field(default_factory=dict)


@app.on_event("startup")
def startup():
    db.init_db()


def start(config, parent_id, note, rationale):
    with start_lock:
        if db.is_running():
            raise HTTPException(409, "An experiment is already running.")
        run_id = str(uuid4())[:8]
        db.create_run(run_id, parent_id, config, note, rationale)
    executor.submit(train, run_id, config)
    return db.get_run(run_id)


@app.get("/api/health")
def health():
    return {"ok": True, "busy": db.is_running()}


@app.get("/api/runs")
def runs():
    return db.all_runs()


@app.get("/api/runs/{run_id}")
def run_detail(run_id: str):
    result = db.get_run(run_id)
    if not result:
        raise HTTPException(404, "Run not found")
    return result


@app.get("/api/best")
def best():
    return db.best_run()


@app.post("/api/runs/baseline", status_code=202)
def baseline():
    if db.best_run():
        raise HTTPException(409, "A baseline already exists.")
    return start(BASELINE, None, "Baseline · default configuration", "Establish a reference score before exploring changes.")


@app.post("/api/runs/propose", status_code=202)
def propose_run():
    best_run = db.best_run()
    if not best_run:
        raise HTTPException(409, "Run the baseline before asking the agent to propose an experiment.")
    result = propose(best_run, db.all_runs())
    if result is None:
        raise HTTPException(409, "The agent has no valid changes left to propose.")
    config, note, rationale = result
    return start(config, best_run["id"], note, rationale)


@app.post("/api/runs", status_code=202)
def manual_run(request: RunRequest):
    best_run = db.best_run()
    config = {**(best_run["config"] if best_run else BASELINE), **request.config}
    allowed = {"learning_rate", "batch_size", "hidden_units", "dropout", "optimizer", "epochs", "seed"}
    if set(config) - allowed:
        raise HTTPException(422, "Unknown configuration field")
    if config["optimizer"] not in ("Adam", "SGD") or not 1 <= int(config["epochs"]) <= 5:
        raise HTTPException(422, "Optimizer must be Adam or SGD; epochs must be 1–5")
    return start(config, best_run["id"] if best_run else None, "Manual configuration", "User supplied configuration.")
