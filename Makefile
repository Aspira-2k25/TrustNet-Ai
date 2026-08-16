.PHONY: test test-unit test-e2e lint up down clean

test:
	python -m pytest -v

test-unit:
	python -m pytest shared/tests models/ services/ -v

test-e2e:
	python -m pytest tests/e2e -v

up:
	docker compose up -d

down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
