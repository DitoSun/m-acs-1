.PHONY: up down restart logs status status-api clean

up:
	docker compose up -d

down:
	docker compose down

restart: down up

logs:
	docker compose logs -f

status:
	@echo "Containers:" && docker compose ps
	@echo "" && echo "GPU:" && nvidia-smi --query-gpu=name,temperature.gpu,memory.used,memory.total,utilization.gpu --format=csv 2>/dev/null || echo "  (no GPU access)"

status-api:
	@echo "Health:    $$(curl -s http://localhost:8080/api/health)"
	@echo "GPU:       $$(curl -s http://localhost:8080/api/gpu | python3 -m json.tool 2>/dev/null || echo '  (not running)')"
	@echo "Models:    $$(curl -s http://localhost:8080/api/models | python3 -m json.tool 2>/dev/null || echo '  (not running)')"

clean:
	docker compose down -v
