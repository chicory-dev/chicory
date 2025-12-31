up:
	docker compose up -d --build

down:
	docker compose down -v

init:
	uv sync --dev --all-extras 

ty:
	uv run ty check src/chicory tests

ruff:
	uv run ruff check src/chicory tests --fix

lint: ruff ty

test: lint
	uv run pytest -vv

test-fast: lint
	uv run pytest -vv -m "not slow and not integration"

test-slow: lint
	uv run pytest -vv -n auto -m "slow"

test-unit: lint
	uv run pytest -vv -n auto -m "not integration"
	
test-integration: lint
	uv run pytest -vv -m "integration"