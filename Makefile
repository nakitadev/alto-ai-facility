.PHONY: help up down seed eval test clean

help:
	@echo "=========================================================="
	@echo " AltoTech Global - Commercial Building AI Assistant"
	@echo "=========================================================="
	@echo " make up    : Bring up TimescaleDB, auto-seed, and run backend/UI"
	@echo " make eval  : Run 3-iteration Golden Set evaluation harness"
	@echo " make seed  : Run or re-seed the 7-day database"
	@echo " make down  : Shut down all containers"
	@echo "=========================================================="

up:
	docker compose up --build

seed:
	@if docker compose ps | grep -q "altotech_timescaledb"; then \
		docker compose run --rm seed python db/seed.py; \
	else \
		python3 db/seed.py; \
	fi

eval:
	@if docker compose ps | grep -q "altotech_timescaledb"; then \
		docker compose run --rm backend python eval/eval_runner.py --runs 3; \
	else \
		python3 eval/eval_runner.py --runs 3; \
	fi

down:
	docker compose down -v
