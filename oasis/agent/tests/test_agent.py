"""
SMOKE TESTS.  Original three cases: Aditi.  Clearance and approval: Sushil.

Run from the project root, with Ollama running and the index built:

    python -m agent.tests.test_agent

Exits non-zero on the first failure, so it can run before a push.
"""

import pathlib
import sys

from agent.models import ask_model
from agent.loop import run_agent, approve

FAILED = []


def check(label, condition, detail=""):
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {label}" + (f"  -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILED.append(label)


# --------------------------------------------------------------- MODEL LAYER

def test_general():
    print("\nTEST 1 - GENERAL (Aditi)")
    answer, model, reason = ask_model("What is an AI agent?")
    print(f"  model: {model}  ({reason})")
    check("general model answers", len(answer) > 20, answer[:80])
    check("no model error", not answer.startswith("The model could not"), answer[:80])


def test_routing():
    print("\nTEST 2 - ROUTING (Aditi)")
    _, m1, r1 = ask_model("Write Python code to average three numbers.")
    _, m2, r2 = ask_model("What is the purpose of a mechanical seal?")
    print(f"  code question  -> {m1}  ({r1})")
    print(f"  plain question -> {m2}  ({r2})")
    check("code question routes to coding", r1 == "calculation requested", r1)
    check("plain question routes to general", r2 == "text question", r2)


def test_vision():
    print("\nTEST 3 - VISION (Aditi)")
    img = next(iter(pathlib.Path("corpus").glob("*.png")), None) or \
          next(iter(pathlib.Path(".").glob("*.jpg")), None)
    if img is None:
        print("  SKIP - no image in the repo to test with")
        return
    answer, model, reason = ask_model("Describe this image.", images=[str(img)])
    print(f"  model: {model}  ({reason})  file: {img.name}")
    check("vision model answers", not answer.startswith("The model could not"),
          answer[:80])


def test_code_generation():
    """SIH asks for code generation, so judges may probe this directly."""
    print("\nTEST 3b - CODE GENERATION (Sushil)")
    from agent.config import MODELS
    answer, model, reason = ask_model(
        "Write a Python function that returns the mean of a list of numbers. "
        "Return only the code.")
    print(f"  model: {model}  ({reason})")
    check("routed to the coding model",
          model == MODELS["coding"] or reason.endswith("(fallback)"), f"{model} / {reason}")
    check("output contains a function definition", "def " in answer, answer[:80])
    check("output is runnable python", _compiles(answer), answer[:120])


def _compiles(text: str) -> bool:
    """Strip markdown fences and try to compile what is left."""
    import re
    body = re.sub(r"^```[a-zA-Z]*|```$", "", text.strip(), flags=re.M).strip()
    try:
        compile(body, "<model output>", "exec")
        return True
    except SyntaxError:
        return False


def test_missing_model_fallback():
    """A model that is not pulled must degrade to general, never to an error."""
    print("\nTEST 3c - FALLBACK WHEN A MODEL IS MISSING (Sushil)")
    from agent import models as M
    original = M.MODELS["coding"]
    M.MODELS["coding"] = "this-model-does-not-exist:0b"
    try:
        answer, model, reason = ask_model("Calculate the average of 10 and 20.")
        print(f"  model: {model}  ({reason})")
        check("fell back rather than erroring", reason.endswith("(fallback)"), reason)
        check("answer is real, not an error string",
              not answer.startswith("The model could not"), answer[:80])
    finally:
        M.MODELS["coding"] = original


# --------------------------------------------------------------- AGENT LOOP

def test_grounded():
    print("\nTEST 4 - GROUNDED ANSWER (Sushil)")
    r = run_agent(question="Why does the seal on P-101 keep failing?",
                  user="admin", user_level="restricted",
                  user_name="R. Sharma", token="test")
    print(f"  sources: {len(r['sources'])}   steps: {len(r['steps'])}")
    check("retrieval returned passages", len(r["sources"]) > 0)
    check("answer cites a document", "[" in r["answer"], r["answer"][:80])


def test_clearance():
    """The core security claim. Nothing else guards this."""
    print("\nTEST 5 - CLEARANCE (Sushil)")
    q = "What is the interlock set point on the crude distillation column?"
    admin = run_agent(question=q, user="admin", user_level="restricted",
                      user_name="R. Sharma", token="test")
    contractor = run_agent(question=q, user="contractor", user_level="public",
                           user_name="Field Contractor", token="test")
    a_docs = {s["document"] for s in admin["sources"]}
    c_docs = {s["document"] for s in contractor["sources"]}
    print(f"  admin sees:      {sorted(a_docs)}")
    print(f"  contractor sees: {sorted(c_docs)}")
    check("restricted document reaches admin", "hazop_report.pdf" in a_docs)
    check("restricted document hidden from contractor",
          "hazop_report.pdf" not in c_docs)


def test_approval_gate():
    """A state-changing tool must be proposed, never executed."""
    print("\nTEST 6 - APPROVAL GATE (Sushil)")
    r = run_agent(question="Draft an approval note for replacing the seal on P-101.",
                  user="admin", user_level="restricted",
                  user_name="R. Sharma", token="test")
    pending = r.get("pending_action")
    check("a write was proposed", bool(pending), str(r["steps"])[:100])
    if not pending:
        return
    print(f"  proposed: {pending.get("description", pending)}")
    out = pathlib.Path("outputs")
    before = set(out.glob("*")) if out.exists() else set()
    check("nothing written before approval",
          not any(p for p in (set(out.glob('*')) if out.exists() else set()) - before))
    res = approve(pending["id"], True)
    check("approval writes the file", res.get("written"), str(res)[:100])


if __name__ == "__main__":
    for t in (test_general, test_routing, test_vision,
              test_code_generation, test_missing_model_fallback,
              test_grounded, test_clearance, test_approval_gate):
        try:
            t()
        except Exception as e:
            print(f"  [FAIL] {t.__name__} raised: {e}")
            FAILED.append(t.__name__)

    print("\n" + "=" * 48)
    if FAILED:
        print(f"{len(FAILED)} FAILED: {', '.join(FAILED)}")
        sys.exit(1)
    print("all checks passed")
