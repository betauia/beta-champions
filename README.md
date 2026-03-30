# BETA CHAMPIONS

![PKMNCHAMPIONS](./assets/BETA_PKMN_champions.png)

## Current state

This is an early proto to kick-start the project and prove core architecture.

It currently supports:

- uploading simple bot JSON files to the API
- storing uploaded bots on shared storage
- creating battle tasks between two bots
- running long-lived worker pods that poll for tasks
- executing a dummy battle between two bots
- sending results back to the API
- generating a simple leaderboard

The current battle logic is intentionally fake. The goal right now is to validate the system design before replacing it with real model loading and real battle sooner.

Built with:

- FastAPI
- Kubernetes (minikube)
- Python workers
- PersistentVolumeClaim shared storage

---

## Architecture

The system currently has these main parts:

### API

The FastAPI service acts as the control plane. It:

- accepts bot uploads
- stores bot metadata and files
- creates battle tasks
- assigns tasks to workers
- receives battle results
- computes the leaderboard

### Worker

The worker is a long-running pod that:

- repeatedly asks the API for the next available task
- loads two bots from shared storage
- runs a dummy battle
- submits the result back to the API

### Shared storage

A PVC is mounted into both API and worker pods. It stores:

- uploaded bots
- queued/running/finished tasks
- battle results

---

## Current flow

1. A user uploads a bot JSON file to the API
2. The API stores it under `/data/bots/<bot_id>/`
3. A battle task is created for two uploaded bots
4. A worker pod polls the API for work
5. The worker receives a task and loads both bots
6. The worker runs a dummy battle
7. The worker sends the result back to the API
8. The API stores the result and updates the leaderboard

---

## Setup

### 1. Start Kubernetes

```bash
minikube start
```

### 2. Ue minikube Docker

```bash
eval $(minikube docker-env)
```

### 3. Create namespace

```bash
kubectl create namespace beta-champions
```

### 4. Apply resources

```bash
kubectl apply -f manifests/storage.yaml
kubectl apply -f manifests/rbac.yaml
kubectl apply -f manifests/api.yaml
kubectl apply -f manifests/worker.yaml
```

### 5. Build images

```bash
cd api
docker build -t json-api:latest .

cd ../worker
docker build -t json-worker:latest .

cd ..
```

### 6. Restart deployments after rebuild

```bash
kubectl -n beta-champions rollout restart deployment/json-api
kubectl -n beta-champions rollout restart deployment/battle-worker

kubectl -n beta-champions rollout status deployment/json-api
kubectl -n beta-champions rollout status deployment/battle-worker
```

### 7. Access API

```bash
kubectl -n beta-champions port-forward svc/json-api 8000:8000
```

Docs at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Testing system

### 1. Upload two bots

Example bot file:

```json
{
  "name": "Arne",
  "strength": 7
}
```

Upload:

```bash
curl -F "file=@bot-a.json" http://127.0.0.1:8000/bots
curl -F "file=@bot-b.json" http://127.0.0.1:8000/bots
```

### 2. List uploaded bots

Go to [http://127.0.0.1:8000/bots](http://127.0.0.1:8000/bots) and copy the returned `bot_id` values.

### 3. Create a battle task

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "bot_a": "BOT_A_ID",
    "bot_b": "BOT_B_ID",
    "num_games": 5
  }'
```

### 4. Check it out 

- Tasks: [http://127.0.0.1:8000/tasks](http://127.0.0.1:8000/tasks)
- Results by ID: [http://127.0.0.1:8000/results/<task_id>](http://127.0.0.1:8000/results/<task_id>)
- Leaderboard: [http://127.0.0.1:8000/leaderboard](http://127.0.0.1:8000/leaderboard)

## Debugging

```bash
kubectl -n beta-champions get pods
kubectl -n beta-champions get deployments
kubectl -n beta-champions get pvc
```

API logs:

```bash
kubectl -n beta-champions logs deploy/json-api
```

Worker logs

```bash
kubectl -n beta-champions logs deploy/battle-worker -f
```

Inspect files in shared storage through API pod:

```bash
kubectl -n beta-champions exec deploy/json-api -- sh -c "find /data -maxdepth 3 | sort"
```
