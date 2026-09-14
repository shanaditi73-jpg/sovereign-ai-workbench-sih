"""
THE AGENT LOOP.

    plan -> call a tool -> observe the result -> decide -> repeat

Capped at MAX_STEPS so it cannot run forever.

PROPOSAL MODE. Read-only tools run freely. Anything that changes state is never
executed by the agent - it finishes reasoning, states what it intends to do, and
waits for a person to approve. That is what makes an agent acceptable in a plant.
"""

import json
import re

from agent.models import ask_model
from agent.session import recall, remember
from agent.tools import TOOLS, catalogue, find_template

MAX_STEPS = 7          # small models wander; keep the leash short
MAX_RETRIES = 2        # attempts to recover from truncated json
PENDING = {}           # action_id -> everything needed to run it later


SYSTEM = """You are an assistant working inside a refinery's own document system.

You may call these tools, one at a time:

{tools}

Reply with ONE json object and nothing else:

  {{"tool": "<name>", "args": {{...}}}}          to call a tool
  {{"answer": "<your answer>"}}                  when you are finished

Rules you must follow:
- Call search_documents before answering anything about the plant.
- Answer ONLY from passages the search returned. If they do not contain the
  answer, say so plainly. Never use your own knowledge about equipment.
- Use calculate for arithmetic. Never compute in your head.
- Use query_data for anything counted, totalled or averaged over the tables
  listed below. Never search for a number that a query would answer exactly.
- Cite the document and page for each claim, like [pump_manual_p101.pdf p.88].
- When asked to produce a document, presentation or spreadsheet, call the write
  tool. It will not run immediately - a person will be asked to approve it.
- Keep the arguments to a write tool SHORT. A presentation is three or four
  slides with three short bullets each, never more. A document is a few short
  paragraphs. Long arguments get truncated and the call is wasted.

Finishing:
- Always complete your thought. Never stop mid-sentence.
- Close with a conclusion or a recommendation, not a trailing fragment.
- If there is more to say than fits, say less about each point rather than
  running out of room halfway through.

Shape your writing to what was asked:
- EMAIL or LETTER - a subject line, a greeting, two or three short paragraphs, a
  clear recommendation, and a sign-off.
- APPROVAL NOTE - what was found, what caused it, what is recommended, what it
  costs or how long it takes, then a line requesting sign-off.
- REPORT - a heading, then short sections. Findings before conclusions.
- ANYTHING ELSE - plain prose. Do not impose headings on a simple answer.

Tables you may query with query_data:
{schema}
"""


TEMPLATE_NOTE = """
The organisation's own template for this kind of document was found in the
library ({doc}). Follow its structure and section order. Its content is an
example only - use the facts from the passages above, not from the template.

--- template ---
{text}
--- end template ---
"""


THINK = re.compile(r"<think>.*?</think>|<thinking>.*?</thinking>",
                   re.DOTALL | re.IGNORECASE)


def _strip_reasoning(text: str) -> str:
    """Remove a reasoning model's thinking block.

    qwen3 and similar emit <think>...</think> before the real reply, and that
    block often mentions a tool in json-ish form while considering and
    rejecting it. Parsing before stripping picks up the rejected call instead
    of the real one. An unclosed block means the reply was truncated mid-think,
    so there is no usable json after it either.
    """
    if not text:
        return ""
    text = THINK.sub("", text)
    low = text.lower()
    for tag in ("<think>", "<thinking>"):
        if tag in low:
            text = text[:low.index(tag)]
            low = text.lower()
    return text.strip()


def _looks_like_json(text: str) -> bool:
    """Did the model try to emit json and fail? A fragment starts with a brace
    and a tool key but never closes. That is a truncation, not an answer."""
    t = _strip_reasoning(text)
    t = re.sub(r"^```(?:json)?", "", t, flags=re.M).strip()
    return t.startswith("{") and ('"tool"' in t or '"answer"' in t)


def _json_from(text: str):
    """Small models wrap json in prose or fences. Dig it out.

    Takes the LAST object carrying a "tool" or "answer" key, not the first.
    A model that talks through its options leaves earlier objects behind; the
    decision it settled on is the final one.
    """
    if not text:
        return None
    text = _strip_reasoning(text)
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    found = []
    depth, start = 0, None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    obj = json.loads(text[start:i + 1])
                    if isinstance(obj, dict):
                        found.append(obj)
                except Exception:
                    pass
                start = None

    for obj in reversed(found):
        if "tool" in obj or "answer" in obj:
            return obj
    return found[-1] if found else None


def run_agent(question: str, user: str, user_level: str,
              user_name: str = "", images: list = None,
              token: str = "") -> dict:
    """Returns the standard response dict. Never raises."""
    steps, sources, model_used, model_reason = [], [], "", ""
    used_template = False
    retries = 0
    from structured import schema
    tables = schema(user_level) or "  (none available at your clearance)"

    transcript = SYSTEM.format(tools=catalogue(), schema=tables)
    history = recall(token)
    if history:
        transcript += "\n" + history
    transcript += f"\nRequest from {user_name or user}: {question}\n"

    for _ in range(MAX_STEPS):
        reply, model_used, model_reason = ask_model(transcript, images=images,
                                                    route_on=question)
        images = None                      # only attach on the first pass
        move = _json_from(reply)

        if move is None:
            # An empty reply is not an answer. Reasoning models can burn the
            # whole token budget thinking and return nothing; ask again.
            if not (reply or "").strip() and retries < MAX_RETRIES:
                retries += 1
                transcript += ("\nYou replied with nothing - you spent your "
                               "whole reply thinking. Do NOT reason step by "
                               "step. Output ONE json object immediately, as "
                               "the very first characters of your reply, and "
                               "keep every string short.\n")
                continue

            # Broken json means the model was cut off mid-structure. Ask again,
            # smaller. Only genuine prose counts as a final answer.
            if _looks_like_json(reply) and retries < MAX_RETRIES:
                retries += 1
                transcript += (
                    "\nThat json was incomplete - you ran out of room. Reply "
                    "again with ONE complete json object. Keep it much shorter: "
                    "at most three slides or sections, at most three short "
                    "bullets each, no long strings.\n")
                continue
            return _finish(reply.strip(), steps, sources, model_used, model_reason)

        if "answer" in move and "tool" not in move:
            return _finish(str(move["answer"]), steps, sources,
                           model_used, model_reason)

        name = move.get("tool")
        args = move.get("args") or {}
        spec = TOOLS.get(name)

        if not spec:
            transcript += (f"\nThat tool does not exist. Choose one of: "
                           f"{', '.join(TOOLS)}.\n")
            continue

        # --- state-changing: propose, do not run
        if spec["changes_state"]:
            # Look for the organisation's template for this document type and
            # give the model one more turn to follow it. Done in code so it
            # cannot be forgotten, and only once per request.
            if not used_template:
                used_template = True
                tpl = find_template(name, user_level, hint=question)
                if tpl:
                    steps.append({"tool": "template",
                                  "result": f"following {tpl['document']}"})
                    transcript += TEMPLATE_NOTE.format(doc=tpl["document"],
                                                       text=tpl["text"])
                    transcript += ("\nNow call the write tool again with "
                                   "content shaped to that template.\n")
                    continue

            action_id = f"act_{len(PENDING) + 1}"
            args.setdefault("author", user_name)
            if name == "write_docx":
                args.setdefault("sources", sources)
            PENDING[action_id] = {"tool": name, "args": args, "user": user}
            steps.append({"tool": name, "result": "awaiting approval"})
            return {
                "answer": _draft_summary(args, sources),
                "sources": sources,
                "steps": steps,
                "pending_action": {"tool": name, "id": action_id,
                                   "description": spec["describe"](args)},
                "model_used": model_used, "model_reason": model_reason,
            }

        # --- read-only: run it
        if name == "search_documents":
            args = {"question": args.get("question") or question,
                    "user_level": user_level}
        elif name == "query_data":
            args = {"sql": args.get("sql", ""), "user_level": user_level}
        try:
            result = spec["fn"](**args)
        except Exception as e:
            result = {"error": str(e)}

        if name == "search_documents":
            for p in result.get("passages", []):
                key = (p["document"], p["page"])
                if key not in {(s["document"], s["page"]) for s in sources}:
                    sources.append({"document": p["document"], "page": p["page"]})

        steps.append({"tool": name, "result": _short(result)})
        transcript += (f"\nYou called {name}. Result:\n"
                       f"{json.dumps(result)[:5000]}\n"
                       f"Now reply with the next json object.\n")

    return _finish("I could not complete that within the step limit.",
                   steps, sources, model_used, model_reason)


def approve(action_id: str, approved: bool) -> dict:
    """Run a proposed action, or discard it."""
    item = PENDING.pop(action_id, None)
    if not item:
        return {"ok": False, "message": "That action is no longer pending."}
    if not approved:
        return {"ok": True, "written": False,
                "message": "Rejected - nothing was written."}

    spec = TOOLS[item["tool"]]
    try:
        result = spec["fn"](**item["args"])
    except Exception as e:
        return {"ok": False, "message": f"Could not write the file: {e}"}

    return {"ok": True, "written": True, "file": result.get("file"),
            "message": f"{result.get('file')} written."}


# ---------------------------------------------------------------- helpers

def _finish(answer, steps, sources, model_used, model_reason):
    return {"answer": answer, "sources": sources, "steps": steps,
            "pending_action": None,
            "model_used": model_used, "model_reason": model_reason}


def _draft_summary(args, sources):
    body = (args.get("body") or "").strip()
    head = args.get("title") or "Document"
    if body:
        preview = body if len(body) < 700 else body[:700] + " ..."
        return f"{head}\n\n{preview}"
    return f"A {head.lower()} is ready. Approve to write the file."


def _short(result):
    s = json.dumps(result)
    return s if len(s) < 220 else s[:220] + " ..."
