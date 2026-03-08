# ─────────────────────────────────────────────
# Multi-RAG Cognitive System — Makefile
# ─────────────────────────────────────────────

.PHONY: help up down build logs init models status clean

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Infrastructure ─────────────────────────────────────────────────────────

up: ## Démarre tous les services
	cp -n .env.example .env 2>/dev/null || true
	docker compose up -d
	@echo ""
	@echo "Services démarrés. Initialisation en cours..."
	@sleep 5
	@$(MAKE) models

down: ## Arrête tous les services
	docker compose down

build: ## Reconstruit les images Docker
	docker compose build --no-cache

logs: ## Affiche les logs en temps réel
	docker compose logs -f

logs-%: ## Logs d'un service spécifique (ex: make logs-ollama)
	docker compose logs -f $*

restart-%: ## Redémarre un service (ex: make restart-cognitive-core)
	docker compose restart $*

# ── Initialisation ─────────────────────────────────────────────────────────

init: ## Initialise les bases de données (Neo4j, Qdrant)
	@echo "Initialisation Neo4j..."
	docker compose exec cognitive-core python scripts/init_neo4j.py
	@echo "Initialisation terminée."

models: ## Télécharge les modèles Ollama
	@echo "Téléchargement des modèles Ollama..."
	docker compose exec ollama bash /scripts/pull_models.sh || \
		OLLAMA_URL=http://localhost:11434 bash scripts/pull_models.sh

# ── Monitoring ─────────────────────────────────────────────────────────────

status: ## État des services
	@echo "=== Services Docker ==="
	@docker compose ps
	@echo ""
	@echo "=== Cognitive Core ==="
	@curl -sf http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "Cognitive Core non disponible"
	@echo ""
	@echo "=== Qdrant ==="
	@curl -sf http://localhost:6333/health | python3 -m json.tool 2>/dev/null || echo "Qdrant non disponible"

# ── Nettoyage ──────────────────────────────────────────────────────────────

clean: ## Supprime les conteneurs et volumes (ATTENTION : perte de données)
	@echo "ATTENTION : Cette commande supprime toutes les données !"
	@read -p "Continuer ? [y/N] " confirm && [ "$$confirm" = "y" ]
	docker compose down -v --remove-orphans
