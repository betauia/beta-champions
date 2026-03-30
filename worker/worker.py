import os
import json
import time
import socket
from pathlib import Path
import requests

API_URL = os.environ.get("API_URL", "http://json-api:8000")
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
WORKER_ID = os.environ.get("WORKER_ID", socket.gethostname())

BOTS_DIR = DATA_DIR / "bots"


def load_bot(bot_id: str) -> dict:
    model_path = BOTS_DIR / bot_id / "model.json"
    return json.loads(model_path.read_text(encoding="utf-8"))


def run_dummy_battle(bot_a: dict, bot_b: dict, num_games: int) -> dict:
    strength_a = int(bot_a.get("strength", 1))
    strength_b = int(bot_b.get("strength", 1))

    wins_a = 0
    wins_b = 0

    for game in range(num_games):
        # Simple deterministic fake battle:
        # higher strength wins every game, ties alternate
        if strength_a > strength_b:
            wins_a += 1
        elif strength_b > strength_a:
            wins_b += 1
        else:
            if game % 2 == 0:
                wins_a += 1
            else:
                wins_b += 1

    return {
        "wins_a": wins_a,
        "wins_b": wins_b,
    }


def main():
    print(f"Worker {WORKER_ID} starting")

    while True:
        try:
            response = requests.post(f"{API_URL}/tasks/next", timeout=10)
            response.raise_for_status()
            payload = response.json()
            task = payload.get("task")

            if not task:
                print("No task available, sleeping...")
                time.sleep(2)
                continue

            task_id = task["task_id"]
            bot_a_id = task["bot_a"]
            bot_b_id = task["bot_b"]
            num_games = int(task["num_games"])

            print(f"Picked up task {task_id}: {bot_a_id} vs {bot_b_id}")

            bot_a = load_bot(bot_a_id)
            bot_b = load_bot(bot_b_id)

            battle_result = run_dummy_battle(bot_a, bot_b, num_games)

            if battle_result["wins_a"] >= battle_result["wins_b"]:
                winner = bot_a_id
            else:
                winner = bot_b_id

            result_payload = {
                "worker_id": WORKER_ID,
                "wins_a": battle_result["wins_a"],
                "wins_b": battle_result["wins_b"],
                "winner": winner,
                "details": {
                    "bot_a_name": bot_a.get("name"),
                    "bot_b_name": bot_b.get("name"),
                    "strength_a": bot_a.get("strength", 1),
                    "strength_b": bot_b.get("strength", 1),
                },
            }

            submit = requests.post(
                f"{API_URL}/tasks/{task_id}/result",
                json=result_payload,
                timeout=10,
            )
            submit.raise_for_status()
            print(f"Finished task {task_id}")

        except Exception as e:
            print(f"Worker loop error: {e}")
            time.sleep(3)


if __name__ == "__main__":
    main()
