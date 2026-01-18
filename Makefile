.PHONY: up down logs test itest

up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f

test:
	pytest -q

itest:
	RUN_INTEGRATION_TESTS=1 pytest -q
