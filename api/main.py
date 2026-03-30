from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from pathlib import Path
import json
import uuid
import shutil
from sqlalchemy import text
from db import SessionLocal

app = FastAPI()

BASE_DIR = Path("/data")
BOTS_DIR = BASE_DIR / "bots"
TASKS_DIR = BASE_DIR / "tasks"
QUEUED_DIR = TASKS_DIR / "queued"
RUNNING_DIR = TASKS_DIR / "running"
FINISHED_DIR = TASKS_DIR / "finished"
RESULTS_DIR = BASE_DIR / "results"

for path in [BOTS_DIR, QUEUED_DIR, RUNNING_DIR, FINISHED_DIR, RESULTS_DIR]:
    path.mkdir(parents=True, exist_ok=True)


class CreateTaskRequest(BaseModel):
    bot_a: str
    bot_b: str
    num_games: int = 5


class SubmitTaskResultRequest(BaseModel):
    worker_id: str
    wins_a: int
    wins_b: int
    winner: str
    details: dict | None = None


@app.get("/")
def root():
    return {"message": "API running"}


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/health/db")
def health_db():
    try:
        with SessionLocal() as db:
            result = db.execute(text("select 1 as ok")).mappings().first()
        return {"ok": True, "db": result["ok"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/bots")
async def upload_bot(file: UploadFile = File(...)):
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Upload a bot .json file")

    raw = await file.read()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="Bot file must be a JSON object")

    if "name" not in parsed:
        raise HTTPException(status_code=400, detail="Bot JSON must contain 'name'")

    bot_id = str(uuid.uuid4())
    bot_dir = BOTS_DIR / bot_id
    bot_dir.mkdir(parents=True, exist_ok=True)

    model_path = bot_dir / "model.json"
    metadata_path = bot_dir / "metadata.json"

    model_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")

    metadata = {
        "bot_id": bot_id,
        "name": parsed["name"],
        "model_file": "model.json",
        "status": "ready",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return metadata


@app.get("/bots")
def list_bots():
    bots = []
    for bot_dir in sorted(BOTS_DIR.iterdir()):
        metadata_path = bot_dir / "metadata.json"
        if metadata_path.exists():
            bots.append(json.loads(metadata_path.read_text(encoding="utf-8")))
    return bots


@app.post("/tasks")
def create_task(payload: CreateTaskRequest):
    bot_a_dir = BOTS_DIR / payload.bot_a
    bot_b_dir = BOTS_DIR / payload.bot_b

    if not bot_a_dir.exists():
        raise HTTPException(status_code=404, detail="bot_a not found")
    if not bot_b_dir.exists():
        raise HTTPException(status_code=404, detail="bot_b not found")

    task_id = str(uuid.uuid4())
    task = {
        "task_id": task_id,
        "bot_a": payload.bot_a,
        "bot_b": payload.bot_b,
        "num_games": payload.num_games,
        "status": "queued",
    }

    (QUEUED_DIR / f"{task_id}.json").write_text(
        json.dumps(task, indent=2),
        encoding="utf-8",
    )

    return task


@app.get("/tasks")
def list_tasks():
    tasks = []
    for folder in [QUEUED_DIR, RUNNING_DIR, FINISHED_DIR]:
        for task_file in sorted(folder.glob("*.json")):
            tasks.append(json.loads(task_file.read_text(encoding="utf-8")))
    return tasks


@app.post("/tasks/next")
def get_next_task():
    queued_tasks = sorted(QUEUED_DIR.glob("*.json"))
    if not queued_tasks:
        return {"task": None}

    task_file = queued_tasks[0]
    task = json.loads(task_file.read_text(encoding="utf-8"))
    task["status"] = "running"

    running_path = RUNNING_DIR / task_file.name
    running_path.write_text(json.dumps(task, indent=2), encoding="utf-8")
    task_file.unlink()

    return {"task": task}


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    for folder in [QUEUED_DIR, RUNNING_DIR, FINISHED_DIR]:
        path = folder / f"{task_id}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="Task not found")


@app.post("/tasks/{task_id}/result")
def submit_task_result(task_id: str, payload: SubmitTaskResultRequest):
    running_path = RUNNING_DIR / f"{task_id}.json"
    if not running_path.exists():
        raise HTTPException(status_code=404, detail="Running task not found")

    task = json.loads(running_path.read_text(encoding="utf-8"))
    task["status"] = "finished"

    result = {
        "task_id": task_id,
        "bot_a": task["bot_a"],
        "bot_b": task["bot_b"],
        "num_games": task["num_games"],
        "worker_id": payload.worker_id,
        "wins_a": payload.wins_a,
        "wins_b": payload.wins_b,
        "winner": payload.winner,
        "details": payload.details or {},
        "status": "finished",
    }

    (RESULTS_DIR / f"{task_id}.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    (FINISHED_DIR / f"{task_id}.json").write_text(
        json.dumps(task, indent=2),
        encoding="utf-8",
    )

    running_path.unlink()

    return {"ok": True}


@app.get("/results/{task_id}")
def get_result(task_id: str):
    result_path = RESULTS_DIR / f"{task_id}.json"
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Result not found")
    return json.loads(result_path.read_text(encoding="utf-8"))


@app.get("/leaderboard")
def leaderboard():
    wins: dict[str, int] = {}
    games: dict[str, int] = {}

    for result_file in RESULTS_DIR.glob("*.json"):
        result = json.loads(result_file.read_text(encoding="utf-8"))
        bot_a = result["bot_a"]
        bot_b = result["bot_b"]
        winner = result["winner"]

        games[bot_a] = games.get(bot_a, 0) + result["num_games"]
        games[bot_b] = games.get(bot_b, 0) + result["num_games"]

        if winner == bot_a:
            wins[bot_a] = wins.get(bot_a, 0) + 1
        elif winner == bot_b:
            wins[bot_b] = wins.get(bot_b, 0) + 1

    output = []
    for bot_dir in BOTS_DIR.iterdir():
        metadata_path = bot_dir / "metadata.json"
        if not metadata_path.exists():
            continue
        meta = json.loads(metadata_path.read_text(encoding="utf-8"))
        bot_id = meta["bot_id"]
        output.append({
            "bot_id": bot_id,
            "name": meta["name"],
            "match_wins": wins.get(bot_id, 0),
            "games_played": games.get(bot_id, 0),
        })

    output.sort(key=lambda x: (-x["match_wins"], -x["games_played"], x["name"]))
    return output
