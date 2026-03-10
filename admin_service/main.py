"""
Admin Service — Interface d'administration du Cerveau Numérique Persistant
Port : 8080

Gère : Ollama, Qdrant, Neo4j, Redis, PostgreSQL, Haystack, Ray, Cognitive Core
"""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Configuration ─────────────────────────────────────────────────────────────
OLLAMA_URL    = os.getenv("OLLAMA_BASE_URL",    "http://ollama:11434")
QDRANT_URL    = os.getenv("QDRANT_URL",         "http://qdrant:6333")
NEO4J_URI     = os.getenv("NEO4J_URI",          "bolt://neo4j:7687")
NEO4J_USER    = os.getenv("NEO4J_USER",         "neo4j")
NEO4J_PASS    = os.getenv("NEO4J_PASSWORD",     "cognitive2024")
REDIS_URL     = os.getenv("REDIS_URL",          "redis://redis:6379")
POSTGRES_URL  = os.getenv("POSTGRES_URL",       "postgresql://cognitive:cognitive2024@postgres:5432/cognitive")
HAYSTACK_URL  = os.getenv("HAYSTACK_URL",       "http://haystack:8001")
COGNITIVE_URL = os.getenv("COGNITIVE_URL",      "http://cognitive-core:8000")
RAY_URL       = os.getenv("RAY_DASHBOARD_URL",  "http://ray-head:8265")

# ── HTTP Client ────────────────────────────────────────────────────────────────
_http: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _http
    _http = httpx.AsyncClient(timeout=15.0)
    yield
    await _http.aclose()


app = FastAPI(title="Cognitive Admin", version="1.0.0", lifespan=lifespan)


async def _get(url: str, timeout: float = 8.0) -> dict[str, Any]:
    try:
        r = await _http.get(url, timeout=timeout)
        return {"ok": r.status_code < 400, "data": r.json(), "status": r.status_code}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def _post(url: str, body: dict) -> dict[str, Any]:
    try:
        r = await _http.post(url, json=body)
        return {"ok": r.status_code < 400, "data": r.json(), "status": r.status_code}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ── Santé globale ─────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health_all():
    """Vérifie l'état de tous les services en parallèle."""
    http_checks = await asyncio.gather(
        _get(f"{OLLAMA_URL}/api/version"),
        _get(f"{QDRANT_URL}/health"),
        _get(f"{HAYSTACK_URL}/health"),
        _get(f"{COGNITIVE_URL}/health"),
        _get(f"{RAY_URL}/api/cluster_status", timeout=3.0),
    )
    http_names = ["ollama", "qdrant", "haystack", "cognitive-core", "ray"]
    result: dict[str, Any] = {
        name: {"status": "up" if r["ok"] else "down", **({"error": r["error"]} if not r["ok"] else {})}
        for name, r in zip(http_names, http_checks)
    }
    if not result["ray"]["status"] == "up":
        result["ray"]["status"] = "optionnel"

    # Neo4j
    try:
        from neo4j import AsyncGraphDatabase
        drv = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        await drv.verify_connectivity()
        await drv.close()
        result["neo4j"] = {"status": "up"}
    except Exception as exc:
        result["neo4j"] = {"status": "down", "error": str(exc)}

    # Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(REDIS_URL)
        await r.ping()
        await r.aclose()
        result["redis"] = {"status": "up"}
    except Exception as exc:
        result["redis"] = {"status": "down", "error": str(exc)}

    # PostgreSQL
    try:
        import asyncpg
        conn = await asyncpg.connect(dsn=POSTGRES_URL)
        await conn.fetchval("SELECT 1")
        await conn.close()
        result["postgres"] = {"status": "up"}
    except Exception as exc:
        result["postgres"] = {"status": "down", "error": str(exc)}

    return result


# ── Ollama — Gestion des modèles ──────────────────────────────────────────────
@app.get("/api/ollama/models")
async def ollama_list_models():
    r = await _get(f"{OLLAMA_URL}/api/tags")
    if not r["ok"]:
        raise HTTPException(503, r.get("error", "Ollama indisponible"))
    models = r["data"].get("models", [])
    return [
        {
            "name": m["name"],
            "size_gb": round(m.get("size", 0) / 1e9, 2),
            "modified_at": m.get("modified_at", ""),
        }
        for m in models
    ]


class PullRequest(BaseModel):
    model: str


@app.post("/api/ollama/pull")
async def ollama_pull(req: PullRequest):
    r = await _post(f"{OLLAMA_URL}/api/pull", {"name": req.model, "stream": False})
    if not r["ok"]:
        raise HTTPException(503, r.get("error", "Échec du téléchargement"))
    return {"ok": True, "model": req.model}


@app.delete("/api/ollama/models/{name:path}")
async def ollama_delete(name: str):
    try:
        await _http.delete(f"{OLLAMA_URL}/api/delete", json={"name": name})
        return {"ok": True, "deleted": name}
    except Exception as exc:
        raise HTTPException(503, str(exc))


# ── Qdrant — Gestion des collections ──────────────────────────────────────────
@app.get("/api/qdrant/collections")
async def qdrant_collections():
    r = await _get(f"{QDRANT_URL}/collections")
    if not r["ok"]:
        raise HTTPException(503, r.get("error", "Qdrant indisponible"))
    raw = r["data"].get("result", {}).get("collections", [])
    details = []
    for col in raw:
        name = col["name"]
        info = await _get(f"{QDRANT_URL}/collections/{name}")
        count = info["data"].get("result", {}).get("vectors_count", "?") if info["ok"] else "?"
        details.append({"name": name, "vectors_count": count})
    return details


@app.delete("/api/qdrant/collections/{name}")
async def qdrant_delete_collection(name: str):
    try:
        await _http.delete(f"{QDRANT_URL}/collections/{name}")
        return {"ok": True, "deleted": name}
    except Exception as exc:
        raise HTTPException(503, str(exc))


# ── Neo4j — Statistiques et requêtes ──────────────────────────────────────────
@app.get("/api/neo4j/stats")
async def neo4j_stats():
    try:
        from neo4j import AsyncGraphDatabase
        drv = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        async with drv.session() as s:
            node_count = (await (await s.run("MATCH (n) RETURN count(n) AS c")).single())["c"]
            rel_count  = (await (await s.run("MATCH ()-[r]->() RETURN count(r) AS c")).single())["c"]
            label_rec  = await (await s.run("CALL db.labels() YIELD label RETURN collect(label) AS l")).single()
            labels     = label_rec["l"]
        await drv.close()
        return {"nodes": node_count, "relations": rel_count, "labels": labels}
    except Exception as exc:
        raise HTTPException(503, str(exc))


class CypherRequest(BaseModel):
    query: str


@app.post("/api/neo4j/query")
async def neo4j_query(req: CypherRequest):
    q = req.query.strip().upper()
    if not any(q.startswith(kw) for kw in ("MATCH", "RETURN", "CALL", "SHOW")):
        raise HTTPException(400, "Seules les requêtes en lecture sont autorisées (MATCH, RETURN, CALL, SHOW)")
    try:
        from neo4j import AsyncGraphDatabase
        drv = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        async with drv.session() as s:
            result  = await s.run(req.query)
            records = await result.data()
        await drv.close()
        return {"records": records[:50]}
    except Exception as exc:
        raise HTTPException(503, str(exc))


@app.delete("/api/neo4j/clear")
async def neo4j_clear():
    try:
        from neo4j import AsyncGraphDatabase
        drv = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        async with drv.session() as s:
            await s.run("MATCH (n) DETACH DELETE n")
        await drv.close()
        return {"ok": True, "message": "Toutes les données Neo4j supprimées"}
    except Exception as exc:
        raise HTTPException(503, str(exc))


# ── Mémoire épisodique — Redis + PostgreSQL ────────────────────────────────────
@app.get("/api/episodic/stats")
async def episodic_stats():
    result: dict[str, Any] = {}

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(REDIS_URL)
        keys = await r.keys("episode:*")
        info = await r.info("memory")
        result["redis"] = {
            "episodes": len(keys),
            "memory": info.get("used_memory_human", "?"),
        }
        await r.aclose()
    except Exception as exc:
        result["redis"] = {"error": str(exc)}

    try:
        import asyncpg
        conn = await asyncpg.connect(dsn=POSTGRES_URL)
        ep_count  = await conn.fetchval("SELECT COUNT(*) FROM episodes")
        ses_count = await conn.fetchval("SELECT COUNT(*) FROM cognitive_sessions")
        await conn.close()
        result["postgres"] = {"episodes": ep_count, "sessions": ses_count}
    except Exception as exc:
        result["postgres"] = {"error": str(exc)}

    return result


@app.get("/api/episodic/recent")
async def episodic_recent():
    try:
        import asyncpg
        conn = await asyncpg.connect(dsn=POSTGRES_URL)
        rows = await conn.fetch(
            "SELECT id::text, query, answer, session_id, timestamp::text "
            "FROM episodes ORDER BY timestamp DESC LIMIT 20"
        )
        await conn.close()
        return [dict(r) for r in rows]
    except Exception as exc:
        raise HTTPException(503, str(exc))


@app.delete("/api/episodic/flush-redis")
async def episodic_flush_redis():
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(REDIS_URL)
        keys = await r.keys("episode:*")
        if keys:
            await r.delete(*keys)
        await r.aclose()
        return {"ok": True, "deleted": len(keys)}
    except Exception as exc:
        raise HTTPException(503, str(exc))


# ── Haystack — Gestion documentaire ───────────────────────────────────────────
@app.get("/api/haystack/status")
async def haystack_status():
    return await _get(f"{HAYSTACK_URL}/health")


class DocIndexRequest(BaseModel):
    content: str
    title: str = ""


@app.post("/api/haystack/index")
async def haystack_index(doc: DocIndexRequest):
    r = await _post(f"{HAYSTACK_URL}/index", {
        "content": doc.content,
        "metadata": {"title": doc.title},
    })
    if not r["ok"]:
        raise HTTPException(503, r.get("error", "Haystack indisponible"))
    return r["data"]


# ── Ray — Cluster distribué ────────────────────────────────────────────────────
@app.get("/api/ray/status")
async def ray_status():
    r = await _get(f"{RAY_URL}/api/cluster_status", timeout=5.0)
    if not r["ok"]:
        return {"status": "unavailable", "note": "Démarrez avec : make ray-up"}
    return r["data"]


# ── Cognitive Core — Test et indexation ───────────────────────────────────────
@app.get("/api/cognitive/status")
async def cognitive_status():
    return await _get(f"{COGNITIVE_URL}/api/status")


class QueryRequest(BaseModel):
    query: str
    session_id: str = ""


@app.post("/api/cognitive/query")
async def cognitive_query(req: QueryRequest):
    r = await _post(f"{COGNITIVE_URL}/api/query", req.model_dump())
    if not r["ok"]:
        raise HTTPException(503, r.get("error", "Cognitive Core indisponible"))
    return r["data"]


class IndexRequest(BaseModel):
    content: str
    rag_type: str = "vector"


@app.post("/api/cognitive/index")
async def cognitive_index(req: IndexRequest):
    r = await _post(f"{COGNITIVE_URL}/api/index", req.model_dump())
    if not r["ok"]:
        raise HTTPException(503, r.get("error", "Cognitive Core indisponible"))
    return r["data"]


# ── Frontend statique ──────────────────────────────────────────────────────────
_static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def admin_ui():
    return (_static_dir / "index.html").read_text()
