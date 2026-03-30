SHELL := /bin/bash

ifneq (,$(wildcard ./.env))
include .env
export
endif

NAMESPACE := beta-champions
API_IMAGE := json-api:latest
WORKER_IMAGE := json-worker:latest

POSTGRES_DB ?= beta_champions
POSTGRES_USER ?= beta

.PHONY: help secret apply build restart logs port-forward db-init db-shell

help:
	@echo "make secret       Create/update postgres-secret from .env"
	@echo "make apply        Apply manifests"
	@echo "make build        Build API and worker images"
	@echo "make restart      Restart deployments"
	@echo "make logs         Show API logs"
	@echo "make port-forward Port-forward API to localhost:8000"
	@echo "make db-init      Apply db/schema.sql"
	@echo "make db-shell     Open psql shell"

secret:
	kubectl -n $(NAMESPACE) delete secret postgres-secret --ignore-not-found
	kubectl -n $(NAMESPACE) create secret generic postgres-secret --from-env-file=.env

apply:
	kubectl apply -f manifests/postgres.yaml
	kubectl apply -f manifests/api.yaml
	kubectl apply -f manifests/worker.yaml

build:
	docker build -t $(API_IMAGE) ./api
	docker build -t $(WORKER_IMAGE) ./worker

restart:
	kubectl -n $(NAMESPACE) rollout restart deployment/postgres
	kubectl -n $(NAMESPACE) rollout restart deployment/json-api
	kubectl -n $(NAMESPACE) rollout restart deployment/battle-worker

logs:
	kubectl -n $(NAMESPACE) logs deploy/json-api -f

port-forward:
	kubectl -n $(NAMESPACE) port-forward svc/json-api 8000:8000

db-init:
	kubectl -n $(NAMESPACE) exec -i deploy/postgres -- \
		psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) < db/schema.sql

db-reset:
	kubectl -n $(NAMESPACE) exec -i deploy/postgres -- \
		psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "drop schema public cascade; create schema public;"

db-shell:
	kubectl -n $(NAMESPACE) exec -it deploy/postgres -- \
		psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)
