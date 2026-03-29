
## Current state

Just a simple test of a system to kick-start the project. Creates a worker to send json over to the api. Should be nice and expandable.


Flow:

1. A user uploads a JSON file
2. The API stores the file
3. The API creates a Kubernetes Job
4. A worker pod processes the JSON
5. The result is sent back to the API

Built with:

- FastAPI
- Kubernetes (minikube)
- Python workers

## Setup

### 1. Start Kubernetes

```bash
minikube start
```

### 2. Use minikube Docker

```bash
eval $(minikube docker-env)
```

### 3. Create namespace

```bash
kubectl create namespace beta-champions
```

### 4. Apply Kubernetes resources

```bash
kubectl apply -f manifests/storage.yaml
kubectl apply -f manifests/rbac.yaml
kubectl apply -f manifests/api.yaml
```

### 5. Build images

```bash
cd api
docker build -t json-api:latest .

cd ../worker
docker build -t json-worker:latest .
```

### 6. Access API

```bash
kubectl -n beta-champions port-forward svc/json-api 8000:8000
```

### 7. Test it out

Docs at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

```bash
curl -F "file=@example.json" http://127.0.0.1:8000/jobs
```

It returns a job ID that can be checked with:

```bash
curl http://127.0.0.1:8000/jobs/<job_id>
```

## 🧰 Debugging

```bash
kubectl -n beta-champions get pods
kubectl -n beta-champions get jobs

kubectl -n beta-champions logs deploy/json-api
kubectl -n beta-champions logs job/<job-name>
```
