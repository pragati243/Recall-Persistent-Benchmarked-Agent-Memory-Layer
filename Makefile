.PHONY: dev down benchmark report test

dev:
	docker compose up -d --wait qdrant neo4j postgres api

down:
	docker compose down

benchmark:
	uv run python benchmark/run_benchmark.py

report:
	uv run python benchmark/score.py

test:
	uv run pytest
