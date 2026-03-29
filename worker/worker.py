import os
import json
from pathlib import Path
import requests

job_id = os.environ.get("JOB_ID", "test-job-1")
api_url = os.environ.get("API_URL", "http://127.0.0.1:8001")
input_dir = Path(os.environ.get("INPUT_DIR", "../api/data/inputs"))

input_path = input_dir / f"{job_id}.json"

payload_in = json.loads(input_path.read_text(encoding="utf-8"))

result = {
    "job_id": job_id,
    "status": "finished",
    "output": {
        "received_type": type(payload_in).__name__,
        "content": payload_in,
    },
}

response = requests.post(f"{api_url}/jobs/{job_id}/result", json=result, timeout=10)
response.raise_for_status()

print("Sent result to API")
print(response.json())
