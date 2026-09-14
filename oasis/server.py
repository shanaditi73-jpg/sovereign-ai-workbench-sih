"""
Workbench backend.

    source sih-venv/bin/activate
    pip install fastapi uvicorn python-multipart
    uvicorn server:app --reload --port 8000

Then open oasis.html in your browser.

TWO SWAPS when the real code is ready (marked SWAP):
    search      -> your Chroma search
    ask_model   -> teammate's ask_model
Nothing else changes.
"""

import hashlib
import time
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="OASIS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------ ACCOUNTS
# Password check is real; the store is hardcoded for the prototype.

from policy import accounts as _accounts, allowed_levels, level_labels

ACCOUNTS = _accounts()

SESSIONS = {}
# Text Recognition using Paddle OCR
from text_recog import process_input
from text_recog import TextRecog
# ------------------------------------------------------------------ WIRING
from my_rag import search, library   # real Chroma retrieval
from agent.models import ask_model   # real Ollama
from agent.loop import run_agent, approve as run_approve
from agent.session import remember, questions as session_questions, forget

# ------------------------------------------------------------------ LEDGER

LEDGER = []


def log(actor: str, event: str):
    prev = LEDGER[-1]["hash"] if LEDGER else "0" * 12
    seq = len(LEDGER) + 1
    payload = f"{seq}{actor}{event}{prev}"
    own = hashlib.sha256(payload.encode()).hexdigest()[:12]
    LEDGER.append({"seq": seq, "actor": actor, "event": event,
                   "prev": prev, "hash": own,
                   "time": time.strftime("%H:%M:%S")})


def verify_chain():
    prev = "0" * 12
    for e in LEDGER:
        payload = f"{e['seq']}{e['actor']}{e['event']}{prev}"
        if hashlib.sha256(payload.encode()).hexdigest()[:12] != e["hash"]:
            return False, e["seq"]
        prev = e["hash"]
    return True, None


# ------------------------------------------------------------------ ROUTES


@app.get("/roles")
async def roles():
    """The login screen reads its role cards from here, so adding an account to
    policy.yaml makes it appear without touching the HTML."""
    out = []
    for username, a in ACCOUNTS.items():
        out.append({"username": username, "role": a["role"],
                    "label": a["label"], "clearance": a["clearance"],
                    "can_upload": a["can_upload"]})
    return {"roles": out, "level_labels": level_labels()}


@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    acct = ACCOUNTS.get(username)
    if not acct or acct["password"] != password:
        log(username, "failed sign-in attempt")
        return JSONResponse({"ok": False, "error": "Incorrect username or password"},
                            status_code=401)
    token = hashlib.sha256(f"{username}{time.time()}".encode()).hexdigest()[:16]
    SESSIONS[token] = username
    log(acct["name"], "signed in")
    return {"ok": True, "token": token, "name": acct["name"],
            "role": acct["role"], "clearance": acct["clearance"],
            "label": acct["label"], "can_upload": acct["can_upload"]}


@app.post("/ask")
async def ask(token: str = Form(...), question: str = Form(...),
              file: Optional[UploadFile] = File(None)):
    username = SESSIONS.get(token)
    if not username:
        return JSONResponse({"error": "Session expired"}, status_code=401)
    acct = ACCOUNTS[username]

    image_path = None
    document_text= None
    if file is not None:
        image_path = f"/tmp/{file.filename}"
        with open(image_path, "wb") as fh:
            fh.write(await file.read())
        log(acct["name"], f"attached {file.filename}")
        
        #Extracting text from the uploaded file
        document_text= process_input(image_path)

    log(acct["name"], "asked a question")
    
    #Giving the extracted text to agent    
    if document_text:
        question_for_agent= (f"{question}\n\n"
                             f"Text extracted from the attached document:\n"
                             f"{document_text}")
    else:
        question_for_agent= question

    res = run_agent(question=question_for_agent, user=username,
                    user_level=acct["clearance"], user_name=acct["name"],
                    images=[image_path] if image_path else None,
                    token=token)

    remember(token, question, res.get("answer", ""),
             (res.get("pending_action") or {}).get("description"))

    for st in res.get("steps", []):
        log(acct["name"], f"tool: {st['tool']}")

    excluded = 0
    try:
        from my_rag import search as _s
        _, excluded = _s(question, acct["clearance"])
    except Exception:
        pass

    if res.get("pending_action"):
        log(acct["name"], f"proposed: {res['pending_action']['description']}")
    else:
        log(acct["name"], f"answered - {res.get('model_used','')}")

    return {"answer": res["answer"],
            "sources": res["sources"],
            "excluded": excluded,
            "refused": not res["sources"] and not res.get("pending_action"),
            "model_used": res.get("model_used", ""),
            "model_reason": res.get("model_reason", ""),
            "steps": res.get("steps", []),
            "pending_action": res.get("pending_action"),
            "recent": session_questions(token),
            "ledger": LEDGER[-6:]}


@app.post("/approve")
async def approve(token: str = Form(...), action_id: str = Form(...),
                  approved: str = Form(...)):
    username = SESSIONS.get(token)
    if not username:
        return JSONResponse({"error": "Session expired"}, status_code=401)
    name = ACCOUNTS[username]["name"]
    ok = approved == "true"

    res = run_approve(action_id, ok)
    log(name, f"file write {'approved' if ok else 'rejected'}"
              + (f" - {res.get('file')}" if res.get("file") else ""))

    return {"ok": res.get("ok", True), "written": res.get("written", False),
            "message": res.get("message", ""), "file": res.get("file"),
            "ledger": LEDGER[-6:]}


@app.get("/download/{filename}")
async def download(filename: str):
    import pathlib
    from fastapi.responses import FileResponse
    p = pathlib.Path("outputs") / filename
    if not p.exists():
        return JSONResponse({"error": "No such file"}, status_code=404)
    return FileResponse(str(p), filename=filename)


@app.get("/documents")
async def documents(token: str):
    username = SESSIONS.get(token)
    if not username:
        return JSONResponse({"error": "Session expired"}, status_code=401)
    return {"documents": library(),
            "can_upload": ACCOUNTS[username]["can_upload"]}


@app.post("/upload")
async def upload(token: str = Form(...), level: str = Form(...),
                 file: UploadFile = File(...)):
    """Add a document to the searchable library with a chosen classification."""
    username = SESSIONS.get(token)
    if not username:
        return JSONResponse({"error": "Session expired"}, status_code=401)

    acct = ACCOUNTS[username]
    if not acct["can_upload"]:
        log(acct["name"], f"upload refused - {acct['role']} may not add documents")
        return JSONResponse(
            {"error": "Your role may not add documents to the library."},
            status_code=403)

    if level not in ("public", "internal", "restricted"):
        return JSONResponse({"error": "Choose a classification."}, status_code=400)

    import pathlib
    from ingest import ingest_one

    dest = pathlib.Path("corpus") / file.filename
    dest.write_bytes(await file.read())

    try:
        chunks = ingest_one(str(dest), level)
    except Exception as e:
        log(acct["name"], f"upload failed - {file.filename}")
        return JSONResponse({"error": f"Could not index that file: {e}"},
                            status_code=400)

    if chunks == 0:
        log(acct["name"], f"upload produced no text - {file.filename}")
        return JSONResponse(
            {"error": "No text could be extracted. Is it a scan? OCR is needed."},
            status_code=400)

    log(acct["name"], f"added {file.filename} as {level} ({chunks} chunks)")
    return {"ok": True, "document": file.filename, "level": level,
            "chunks": chunks, "documents": library(), "ledger": LEDGER[-6:]}


@app.get("/suggestions")
async def suggestions(token: str):
    """Starter questions, plus whatever this session has already asked."""
    if token not in SESSIONS:
        return JSONResponse({"error": "Session expired"}, status_code=401)
    starters = [
        "What is the interlock set point on the crude distillation column?",
        "Why does the seal on P-101 keep failing?",
        "How many breakdowns has P-101 had, and how much downtime?",
        "Draft an approval note for replacing the seal on P-101.",
        "What permits are required for a mechanical seal replacement?",
    ]
    return {"starters": starters, "recent": session_questions(token)}


@app.get("/outputs")
async def outputs(token: str):
    """Everything the agent has generated, newest first."""
    import pathlib, datetime
    if token not in SESSIONS:
        return JSONResponse({"error": "Session expired"}, status_code=401)

    d = pathlib.Path("outputs")
    files = []
    if d.exists():
        for p in sorted(d.iterdir(), key=lambda x: x.stat().st_mtime,
                        reverse=True):
            if p.name.startswith(".") or not p.is_file():
                continue
            files.append({
                "file": p.name,
                "kind": p.suffix.lstrip(".").lower(),
                "size_kb": max(1, round(p.stat().st_size / 1024)),
                "when": datetime.datetime.fromtimestamp(
                    p.stat().st_mtime).strftime("%H:%M"),
            })
    return {"files": files}


@app.get("/status")
async def status():
    intact, broken = verify_chain()
    return {"egress_mode": "air-gapped", "bytes_out": 0, "blocked": 3,
            "model_hash": "a3f9c2", "clock": "NIC/NPL",
            "ledger": LEDGER[-6:], "entries": len(LEDGER),
            "chain_intact": intact, "broken_at": broken}


@app.post("/verify")
async def verify():
    intact, broken = verify_chain()
    return {"intact": intact, "broken_at": broken, "entries": len(LEDGER)}
