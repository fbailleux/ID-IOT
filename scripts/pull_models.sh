#!/usr/bin/env bash
# ─────────────────────────────────────────────
# Téléchargement des modèles Ollama
# À exécuter une fois après le démarrage d'Ollama
# ─────────────────────────────────────────────

set -euo pipefail

OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
TIMEOUT=300

wait_for_ollama() {
    echo "Attente du démarrage d'Ollama..."
    local elapsed=0
    until curl -sf "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; do
        if [ "$elapsed" -ge "$TIMEOUT" ]; then
            echo "Timeout : Ollama n'est pas disponible après ${TIMEOUT}s" >&2
            exit 1
        fi
        sleep 3
        elapsed=$((elapsed + 3))
    done
    echo "Ollama est prêt."
}

pull_model() {
    local model="$1"
    echo ""
    echo "Téléchargement : $model"
    curl -sf -X POST "${OLLAMA_URL}/api/pull" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"${model}\"}" \
        | grep -E '"status"|"completed"' || true
    echo "OK : $model"
}

# ── Main ──────────────────────────────────────
wait_for_ollama

echo ""
echo "=== Modèles LLM ==="
pull_model "mistral"          # 7B — raisonnement principal
pull_model "phi3:mini"        # 3.8B — tâches rapides (planner)

echo ""
echo "=== Modèle d'embedding ==="
pull_model "nomic-embed-text" # embeddings pour Vector RAG

echo ""
echo "Tous les modèles sont téléchargés."
echo "Accès Open WebUI : http://localhost:3000"
echo "Accès Cognitive Core : http://localhost:8000"
