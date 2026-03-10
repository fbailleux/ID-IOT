# Cerveau Numérique Persistant — Multi-RAG Cognitive System

Système cognitif multi-RAG basé sur LangGraph, CrewAI et 4 types de mémoire.

## Architecture

```
Utilisateurs
    │
    ▼
Open WebUI (port 3000)
    │
    ▼
LangGraph Cognitive Core (port 8000)
    │
    ▼
Planner Agent
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Couche RAG parallèle                                   │
│                                                         │
│  Mode standard (USE_RAY=false)  Mode Ray (USE_RAY=true) │
│  ┌──────────────────────────┐   ┌──────────────────────┐│
│  │ fan-out LangGraph natif  │   │ Ray Orchestrator     ││
│  │ (4 nœuds async)          │   │ (workers distribués) ││
│  └──────────────────────────┘   └──────────────────────┘│
└─────────────────────────────────────────────────────────┘
    │
    ├── Vector RAG   → Qdrant
    ├── Graph RAG    → Neo4j
    ├── Document RAG → Haystack
    └── Episodic RAG → Redis + PostgreSQL
    │
    ▼
Agent Swarm (CrewAI) → Synthesis → Mémoire épisodique
    │
    ▼
LLM Runtime (Ollama) — Mistral 7B / Phi-3 Mini
```

## Les 4 systèmes RAG

| RAG | Backend | Rôle |
|-----|---------|------|
| **Vector RAG** | Qdrant | Recherche sémantique par similarité |
| **Graph RAG** | Neo4j | Raisonnement sur les relations entités |
| **Document RAG** | Haystack | Extraction de passages documentaires |
| **Episodic RAG** | Redis + PostgreSQL | Mémoire des expériences passées |

## Le Swarm d'agents (CrewAI)

| Agent | Rôle |
|-------|------|
| **Planner** | Décompose les problèmes en sous-tâches |
| **Research** | Synthétise les informations RAG |
| **Infra** | Analyse Docker, services, réseau |
| **Log** | Analyse journalctl, docker logs |
| **Synthesis** | Fusionne tous les résultats |

## Modèles LLM (Ollama)

| Modèle | Usage | RAM |
|--------|-------|-----|
| Mistral 7B | Raisonnement principal | ~8 Go |
| Phi-3 Mini | Planification rapide | ~3 Go |
| nomic-embed-text | Embeddings | ~1 Go |

## Démarrage rapide

### Prérequis
- Docker + Docker Compose
- 40+ Go RAM recommandé

### Installation

```bash
# 1. Copier la configuration
cp .env.example .env

# 2. Démarrer tous les services
make up

# 3. Initialiser les bases de données
make init

# 4. Accéder à l'interface
open http://localhost:3000
```

### Commandes utiles

```bash
make up        # Démarrer tous les services (inclut l'admin)
make down      # Arrêter
make status    # État des services
make logs      # Logs en temps réel
make models    # Télécharger les modèles Ollama
make init      # Initialiser les BDD
make admin     # Vérifier l'interface d'administration
```

### Interface d'administration

Disponible sur `http://localhost:8080` dès que les services sont démarrés.

| Section | Fonctionnalités |
|---------|----------------|
| **Dashboard** | Santé de tous les services en temps réel |
| **Test RAG** | Envoyer une requête au système cognitif |
| **Indexer** | Ajouter des documents dans les RAG |
| **Ollama** | Télécharger, lister, supprimer des modèles |
| **Qdrant** | Gérer les collections vectorielles |
| **Neo4j** | Statistiques, requêtes Cypher, vidage |
| **Mémoire** | Épisodes Redis/PostgreSQL, flush cache |
| **Haystack** | Indexation documentaire |
| **Ray** | État du cluster distribué |

#### Ray (orchestration distribuée)

```bash
make ray-up        # Démarrer le cluster Ray (dashboard http://localhost:8265)
make ray-down      # Arrêter le cluster Ray
make ray-status    # État du cluster Ray
make ray-dashboard # Vérifier le dashboard Ray

# Activer Ray dans cognitive-core (mode local — pas de cluster requis)
USE_RAY=true docker compose up -d cognitive-core

# Activer Ray avec cluster distribué
make ray-up
USE_RAY=true RAY_ADDRESS=ray://ray-head:10001 docker compose up -d cognitive-core
```

## RAM utilisée (serveur)

| Composant | RAM |
|-----------|-----|
| Ollama (LLM) | 14–18 Go |
| Neo4j | 8 Go |
| Qdrant | 4 Go |
| Haystack + Cognitive Core | 4 Go |
| Agents CrewAI | 4 Go |
| Redis + PostgreSQL | 2 Go |
| Admin UI | 1 Go |
| **Total (sans Ray)** | **~37–41 Go** |
| Ray head (optionnel) | +2 Go |

## Ports exposés

| Service | Port |
|---------|------|
| Open WebUI | 3000 |
| Cognitive Core API | 8000 |
| Haystack API | 8001 |
| Ollama | 11434 |
| Qdrant HTTP | 6333 |
| Neo4j HTTP | 7474 |
| Redis | 6379 |
| PostgreSQL | 5432 |
| Admin UI | 8080 |
| Ray Dashboard (optionnel) | 8265 |
| Ray Client (optionnel) | 10001 |

## API Cognitive Core

```bash
# Requête cognitive complète
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Analyse l etat des services Docker"}'

# Indexer un document
curl -X POST http://localhost:8000/api/index \
  -H "Content-Type: application/json" \
  -d '{"content": "...", "rag_type": "vector"}'

# Etat des services
curl http://localhost:8000/api/status
```

## Structure du projet

```
ID-IOT/
├── docker-compose.yml          # Orchestration des services
├── .env.example                # Variables d'environnement
├── Makefile                    # Commandes simplifiées
├── requirements.txt            # Dépendances Cognitive Core
├── requirements-admin.txt      # Dépendances Admin Service
├── requirements-haystack.txt   # Dépendances Haystack Service
├── cognitive_core/             # LangGraph + noeuds du graphe
│   ├── graph.py               # Graphe LangGraph principal
│   ├── nodes.py               # Noeuds (planner, rag, synthesis...)
│   └── state.py               # Etat partage TypedDict
├── rag/                        # 4 systemes RAG
│   ├── vector_rag.py          # Qdrant
│   ├── graph_rag.py           # Neo4j
│   ├── document_rag.py        # Haystack client
│   └── episodic_rag.py        # Redis + PostgreSQL
├── agents/                     # CrewAI agent swarm
│   ├── crew.py                # Construction du Crew
│   ├── definitions.py         # Definitions des agents
│   └── tasks.py               # Taches assignees
├── api/                        # FastAPI gateway
│   ├── main.py
│   ├── routes.py
│   └── openai_compat.py       # Compatibilite API OpenAI
├── haystack_service/           # Service Document RAG
│   └── main.py
├── config/                     # Configurations services
│   ├── qdrant/config.yaml
│   ├── neo4j/neo4j.conf
│   └── haystack/pipeline.yaml
├── admin_service/              # Interface d'administration (port 8080)
│   ├── main.py                # FastAPI — toutes les routes admin
│   └── static/index.html      # UI single-page (Tailwind + JS vanilla)
├── ray_orchestrator/           # Couche Ray distribuée
│   ├── cluster.py             # Init Ray (local ou cluster distant)
│   ├── remote_tasks.py        # Tâches @ray.remote pour les 4 RAG
│   └── __init__.py
├── scripts/
│   ├── init_postgres.sql       # Schema episodique
│   ├── init_neo4j.py           # Init Graph RAG
│   └── pull_models.sh          # Telechargement modeles
└── docker/
    ├── Dockerfile.cognitive
    ├── Dockerfile.haystack
    └── Dockerfile.admin
```

## API Admin Service

```bash
# Santé de tous les services
curl http://localhost:8080/api/health

# Lister les modèles Ollama
curl http://localhost:8080/api/ollama/models

# Télécharger un modèle
curl -X POST http://localhost:8080/api/ollama/pull \
  -H "Content-Type: application/json" \
  -d '{"model": "mistral"}'

# Statistiques Neo4j
curl http://localhost:8080/api/neo4j/stats

# Requête Cypher (lecture)
curl -X POST http://localhost:8080/api/neo4j/query \
  -H "Content-Type: application/json" \
  -d '{"query": "MATCH (n) RETURN n LIMIT 10"}'

# Statistiques mémoire épisodique
curl http://localhost:8080/api/episodic/stats

# Épisodes récents
curl http://localhost:8080/api/episodic/recent

# Vider le cache Redis
curl -X DELETE http://localhost:8080/api/episodic/flush-redis

# État du cluster Ray
curl http://localhost:8080/api/ray/status

# Test d'une requête cognitive
curl -X POST http://localhost:8080/api/cognitive/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Quel est l état du système ?"}'
```

## Variables d'environnement

### Ray

| Variable | Défaut | Description |
|----------|--------|-------------|
| `USE_RAY` | `false` | Active le mode Ray pour les 4 RAG parallèles |
| `RAY_ADDRESS` | _(vide)_ | Adresse du cluster Ray (`ray://ray-head:10001`) |
| `RAY_NUM_CPUS` | `4` | CPUs alloués en mode local |

### LLM et services

| Variable | Défaut | Description |
|----------|--------|-------------|
| `DEFAULT_MODEL` | `mistral` | Modèle principal pour la synthèse |
| `FAST_MODEL` | `phi3:mini` | Modèle rapide pour le planificateur |
| `LOG_LEVEL` | `INFO` | Niveau de logs (`DEBUG`, `INFO`, `WARNING`) |
| `WEBUI_SECRET_KEY` | _(à changer)_ | Clé secrète Open WebUI |
