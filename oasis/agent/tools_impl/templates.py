"""Finding the organisation's own document templates in the corpus.

Called from agent/loop.py before a write tool runs, so the house format cannot
be forgotten. A document only counts as a template if its filename says so.
"""


TEMPLATE_FOR = {
    "write_docx": {
        "query": "approval note letter report template format structure",
        "tokens": ("approval", "note", "letter", "report", "memo"),
    },
    "write_pptx": {
        "query": "presentation deck briefing template format structure",
        "tokens": ("presentation", "deck", "briefing", "slide"),
    },
    "write_xlsx": {
        "query": "spreadsheet register log template format structure",
        "tokens": ("spreadsheet", "register", "log", "sheet"),
    },
}


def find_template(tool_name: str, user_level: str = "restricted",
                  hint: str = ""):
    """Look in the corpus for the organisation's own template for this kind of
    document. Returns its text, or None if the plant has not supplied one.

    Called in code rather than left to the model, so it cannot be forgotten.
    A document only counts as a template if its filename says so.
    """
    from my_rag import search

    spec = TEMPLATE_FOR.get(tool_name)
    if not spec:
        return None

    query = f"{hint} {spec['query']}".strip()
    try:
        passages, _ = search(query, user_level, k=6)
    except Exception:
        return None

    # Score each candidate template: does the request itself name it?
    # "draft an email" should reach the letter template, not the approval note.
    NAMES = {
        "approval": ("approval", "sanction", "authorise", "authorize"),
        "note": ("note", "memo"),
        "letter": ("letter", "email", "mail", "correspondence", "write to"),
        "report": ("report", "analysis", "study", "findings"),
        "register": ("register", "log", "list", "table"),
        "presentation": ("presentation", "deck", "slide", "ppt", "briefing"),
    }
    low = (hint or "").lower()

    scores = {}
    for p in passages:
        name = p["document"].lower()
        if "template" not in name:
            continue
        if not any(tok in name for tok in spec["tokens"]):
            continue
        score = scores.get(p["document"], 0)
        for key, words in NAMES.items():
            if key in name and any(w in low for w in words):
                score += 10
        score += 1                       # retrieval already ranked it
        scores[p["document"]] = score

    if not scores:
        return None
    best = max(scores, key=scores.get)

    text = "\n".join(p["text"] for p in passages if p["document"] == best)
    return {"document": best, "text": text[:2500]}
