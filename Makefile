.PHONY: up down build smoke clean logs ps

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

clean:
	docker compose down -v --remove-orphans

logs:
	docker compose logs -f

ps:
	docker compose ps

smoke:
	bash scripts/smoke.sh
