from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from kubernetes import client, config
from pathlib import Path
import json
import os
import uuid

app = FastAPI()

BASE_DIR = Path("/data")
INPUT_DIR = BASE_DIR / "inputs"
RESULT_DIR = BASE_DIR / "results"
INPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)

NAMESPACE = os.environ.get("NAMESPACE", "beta-champions")
WORKER_IMAGE = os.environ.get("WORKER_IMAGE", "json-worker:latest")
API_URL = os.environ.get("API_URL", "http://json-api:8000")
PVC_NAME = os.environ.get("PVC_NAME", "shared-data-pvc")


class JobResult(BaseModel):
    job_id: str
    status: str
    output: dict | list | str | int | float | bool | None = None


def create_k8s_job(job_id: str) -> None:
    config.load_incluster_config()
    batch = client.BatchV1Api()

    job_name = f"json-job-{job_id[:8]}"

    job = client.V1Job(
        metadata=client.V1ObjectMeta(
            name=job_name,
            namespace=NAMESPACE,
            labels={"app": "json-worker", "job-id": job_id},
        ),
        spec=client.V1JobSpec(
            backoff_limit=0,
            ttl_seconds_after_finished=300,
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={"app": "json-worker", "job-id": job_id}
                ),
                spec=client.V1PodSpec(
                    restart_policy="Never",
                    containers=[
                        client.V1Container(
                            name="worker",
                            image=WORKER_IMAGE,
                            image_pull_policy="IfNotPresent",
                            env=[
                                client.V1EnvVar(name="JOB_ID", value=job_id),
                                client.V1EnvVar(name="API_URL", value=API_URL),
                                client.V1EnvVar(name="INPUT_DIR", value="/data/inputs"),
                            ],
                            volume_mounts=[
                                client.V1VolumeMount(name="shared-data", mount_path="/data")
                            ],
                        )
                    ],
                    volumes=[
                        client.V1Volume(
                            name="shared-data",
                            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                claim_name=PVC_NAME
                            ),
                        )
                    ],
                ),
            ),
        ),
    )

    batch.create_namespaced_job(namespace=NAMESPACE, body=job)


@app.get("/")
def root():
    return {"message": "API running"}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/jobs")
async def create_job(file: UploadFile = File(...)):
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Upload a .json file")

    raw = await file.read()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    job_id = str(uuid.uuid4())
    (INPUT_DIR / f"{job_id}.json").write_text(json.dumps(parsed), encoding="utf-8")

    create_k8s_job(job_id)

    return {"job_id": job_id, "status": "queued"}


@app.post("/jobs/{job_id}/result")
def submit_result(job_id: str, payload: JobResult):
    (RESULT_DIR / f"{job_id}.json").write_text(
        json.dumps(payload.model_dump()),
        encoding="utf-8",
    )
    return {"ok": True}


@app.get("/jobs/{job_id}")
def get_result(job_id: str):
    result_path = RESULT_DIR / f"{job_id}.json"
    if result_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))
    return {"job_id": job_id, "status": "pending"}
