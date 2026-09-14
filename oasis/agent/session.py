"""
SESSION MEMORY - within one sitting only.

Keeps the last few turns so a follow-up question can resolve a reference:
"why does P-101 fail" then "what did that cost".

Deliberately small. Each turn is stored as the question plus a one-line gist of
the answer, and only the last few turns are kept. Storing the whole conversation
would grow the prompt every turn and crowd out the instructions that matter more
on a small model - citing sources, and not guessing.

This is within-session only. Memory across sessions is excluded by design:
knowledge held outside the document store is knowledge the clearance filter does
not govern.
"""

KEEP_TURNS = 3
GIST_CHARS = 160

_MEMORY = {}          # token -> [ {question, gist, file}, ... ]


def remember(token: str, question: str, answer: str, file: str = None):
    if not token:
        return
    gist = " ".join((answer or "").split())
    if len(gist) > GIST_CHARS:
        cut = gist[:GIST_CHARS]
        gist = cut[:cut.rfind(" ")] + "..." if " " in cut else cut + "..."
    turns = _MEMORY.setdefault(token, [])
    turns.append({"question": question, "gist": gist, "file": file})
    del turns[:-KEEP_TURNS]


def recall(token: str) -> str:
    """The last few turns, as text for the top of the transcript."""
    turns = _MEMORY.get(token) or []
    if not turns:
        return ""
    lines = ["Earlier in this session:"]
    for t in turns:
        lines.append(f'  Asked: {t["question"]}')
        lines.append(f'  You answered: {t["gist"]}')
        if t.get("file"):
            lines.append(f'  You produced: {t["file"]}')
    lines.append("Use this only to understand what a follow-up refers to. "
                 "Do not treat it as a source - search the documents again.")
    return "\n".join(lines) + "\n"


def questions(token: str) -> list:
    """This session's questions, newest first. Shown as chips in the composer."""
    return [t["question"] for t in reversed(_MEMORY.get(token) or [])]


def forget(token: str):
    _MEMORY.pop(token, None)
