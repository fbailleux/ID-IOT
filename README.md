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
 ┌──────────────────────────────────────┐
 ▼                                      ▼
Agent Swarm (CrewAI)           Cognitive Services
                                        │
           ┌──────────────┬─────────────┬─────────────┐
           ▼              ▼             ▼             ▼
      Vector RAG     Graph RAG    Document RAG  Episodic RAG
           │              │             │             │
           ▼              ▼             ▼             ▼
        Qdrant          Neo4j        Haystack     Redis + PG
                                        │
                                        ▼
                                   LLM Runtime
                                     Ollama
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
make up        # Démarrer
make down      # Arrêter
make status    # État des services
make logs      # Logs en temps réel
make models    # Télécharger les modèles Ollama
make init      # Initialiser les BDD
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
| **Total** | **~36–40 Go** |

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
├── requirements.txt            # Dependances Cognitive Core
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
├── scripts/
│   ├── init_postgres.sql       # Schema episodique
│   ├── init_neo4j.py           # Init Graph RAG
│   └── pull_models.sh          # Telechargement modeles
└── docker/
    ├── Dockerfile.cognitive
    └── Dockerfile.haystack
```
