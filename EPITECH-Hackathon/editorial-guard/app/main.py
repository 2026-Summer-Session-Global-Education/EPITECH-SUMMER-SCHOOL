"""FastAPI application.

Wires the shared core to two analyzer plugins and serves the frontend.

API keys and the active model are managed from the UI and stored locally in the
SQLite database. Several keys can be held at once; one is active at a time, and the
model list is fetched from whichever key is active. A .env key, if present, is
seeded once on first run as a convenience but the UI is the source of truth.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config
from .analyzers.base import Analyzer
from .analyzers.legal_risk import LegalRiskAnalyzer
from .analyzers.relation import RelationAnalyzer
from .core.context import combined_context, extract_text
from .core.llm import LLMClient
from .core.providers import get_provider, provider_list
from .core.runner import Runner
from .core.store import Store

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Editorial Guard", version="0.3.0")

store = Store(config.DB_PATH)
llm: LLMClient
runner: Runner

ANALYZERS: dict[str, Analyzer] = {
    "legal": LegalRiskAnalyzer(),
    "relation": RelationAnalyzer(),
}


# ---- key / model management ---------------------------------------------

def mask(key: str) -> str:
    if not key:
        return ""
    return ("****" + key[-4:]) if len(key) >= 4 else "****"


def _active_key_id() -> str | None:
    aid = store.get_setting("active_key_id")
    keys = store.list_keys()
    if not keys:
        return None
    if aid and any(str(k["id"]) == str(aid) for k in keys):
        return str(aid)
    return str(keys[0]["id"])


def _active_key_value() -> str | None:
    aid = _active_key_id()
    if aid is None:
        return None
    row = store.get_key(int(aid))
    return row["key"] if row else None


def _active_key_row() -> dict | None:
    aid = _active_key_id()
    if aid is None:
        return None
    return store.get_key(int(aid))


def refresh_llm() -> None:
    global llm, runner
    row = _active_key_row()
    model = store.get_setting("active_model") or config.MODEL
    if row:
        provider = get_provider(row.get("provider", "anthropic"))
        llm = LLMClient(provider, row["key"], model)
    else:
        llm = LLMClient(None, None, model)
    runner = Runner(llm)


# bootstrap: seed a .env key once, then build the client
if not store.list_keys() and config.API_KEY:
    _kid = store.add_key("from .env", config.API_KEY)
    store.set_setting("active_key_id", str(_kid))
refresh_llm()


# ---- request models -----------------------------------------------------

class AnalyzeRequest(BaseModel):
    text: str
    analyzer: str = "legal"
    doc_id: str = "draft"


class SettingsRequest(BaseModel):
    model: str


class KeyRequest(BaseModel):
    label: str = ""
    key: str
    provider: str = "anthropic"


# ---- health / config ----------------------------------------------------

@app.get("/api/providers")
def providers() -> dict:
    return {"items": provider_list()}


@app.get("/api/health")
def health() -> dict:
    row = _active_key_row()
    return {
        "configured": llm.configured,
        "mode": "live" if llm.live else "mock",
        "model": llm.model,
        "provider": llm.provider_name,
        "active_key": row["label"] if row else None,
        "has_keys": bool(store.list_keys()),
        "error": None if llm.configured else llm.last_error,
        "analyzers": list(ANALYZERS.keys()),
    }


@app.get("/api/keys")
def get_keys() -> dict:
    aid = _active_key_id()
    return {"items": [
        {"id": k["id"], "label": k["label"], "masked": mask(k["key"]),
         "provider": k.get("provider", "anthropic"),
         "active": str(k["id"]) == str(aid)}
        for k in store.list_keys()
    ]}


@app.post("/api/keys")
def add_key(req: KeyRequest) -> dict:
    key = req.key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="empty key")
    provider_name = req.provider if get_provider(req.provider) else "anthropic"
    if get_provider(provider_name) is None:
        raise HTTPException(status_code=400, detail=f"unknown provider: {req.provider}")
    first = not store.list_keys()
    label = req.label.strip() or f"{provider_name} key {len(store.list_keys()) + 1}"
    kid = store.add_key(label, key, provider_name)
    if first:
        store.set_setting("active_key_id", str(kid))
    refresh_llm()
    # validate immediately by listing this key's models
    temp = LLMClient(get_provider(provider_name), key, llm.model)
    models = temp.list_models()
    # if this key just became active, pick a sensible model it can actually use
    if first and models and llm.model not in {m["id"] for m in models}:
        store.set_setting("active_model", models[0]["id"])
        refresh_llm()
    return {"id": kid, "label": label, "masked": mask(key), "provider": provider_name,
            "active": first, "models": models,
            "error": temp.last_error if not models else None}


@app.post("/api/keys/{key_id}/activate")
def activate_key(key_id: int) -> dict:
    if store.get_key(key_id) is None:
        raise HTTPException(status_code=404, detail="no such key")
    store.set_setting("active_key_id", str(key_id))
    refresh_llm()
    models = llm.list_models()
    # if the stored model is not valid for this provider, switch to its first model
    if models and llm.model not in {m["id"] for m in models}:
        store.set_setting("active_model", models[0]["id"])
        refresh_llm()
        models = llm.list_models()
    return {"ok": True, "model": llm.model, "provider": llm.provider_name,
            "models": models, "error": llm.last_error}


@app.delete("/api/keys/{key_id}")
def delete_key(key_id: int) -> dict:
    was_active = str(_active_key_id()) == str(key_id)
    store.delete_key(key_id)
    if was_active:
        remaining = store.list_keys()
        store.set_setting("active_key_id",
                          str(remaining[0]["id"]) if remaining else "")
    refresh_llm()
    return {"ok": True}


@app.get("/api/models")
def models(key_id: int | None = None) -> dict:
    client = llm
    if key_id is not None:
        row = store.get_key(key_id)
        if row is None:
            raise HTTPException(status_code=404, detail="no such key")
        client = LLMClient(get_provider(row.get("provider", "anthropic")),
                           row["key"], llm.model)
    return {"configured": client.configured, "models": client.list_models(),
            "current": llm.model, "error": client.last_error}


@app.post("/api/settings")
def settings(req: SettingsRequest) -> dict:
    store.set_setting("active_model", req.model)
    refresh_llm()
    ok, err = llm.test() if llm.configured else (False, llm.last_error)
    return {"ok": ok, "model": llm.model, "error": err,
            "mode": "live" if ok else "mock"}


# ---- analysis -----------------------------------------------------------

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    analyzer = ANALYZERS.get(req.analyzer)
    if analyzer is None:
        raise HTTPException(status_code=400, detail=f"unknown analyzer: {req.analyzer}")
    ctx = combined_context(store.list_context())
    result = runner.run(req.doc_id, req.text, analyzer, ctx)
    payload = result.model_dump()
    try:
        store.save(payload, req.text)
    except Exception:
        pass
    return payload


# ---- standards context (multiple files) ---------------------------------

@app.get("/api/context")
def get_context() -> dict:
    docs = store.list_context()
    total = sum(d["chars"] for d in docs)
    return {
        "items": [{"id": d["id"], "filename": d["filename"], "chars": d["chars"]}
                  for d in docs],
        "total_chars": total,
    }


@app.post("/api/context")
async def add_context(files: list[UploadFile] = File(...)) -> dict:
    results = []
    for file in files:
        name = file.filename or "upload.txt"
        if not (name.lower().endswith(".txt") or name.lower().endswith(".pdf")):
            results.append({"filename": name, "error": "only .txt and .pdf supported"})
            continue
        data = await file.read()
        try:
            text = extract_text(name, data)
        except Exception as exc:
            results.append({"filename": name, "error": str(exc)})
            continue
        if not text.strip():
            results.append({"filename": name, "error": "no text could be extracted"})
            continue
        doc_id = store.add_context(name, text)
        results.append({"id": doc_id, "filename": name, "chars": len(text)})
    return {"results": results}


@app.delete("/api/context/{doc_id}")
def remove_context(doc_id: int) -> dict:
    store.delete_context(doc_id)
    return {"ok": True}


@app.get("/api/history")
def history() -> dict:
    return {"items": store.history()}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(WEB_DIR / "index.html"))


app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
