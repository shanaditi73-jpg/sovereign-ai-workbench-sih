"""
THE TOOL REGISTRY.

One file per tool in agent/tools_impl/. This file only says which tools exist,
what arguments they take, and - the part that matters - whether each one
CHANGES STATE.

    changes_state: False   runs immediately
    changes_state: True    never executed by the agent; proposed for approval

To add a tool: write agent/tools_impl/<name>.py, import it below, add a row.
Nothing else in the system needs to change.
"""

from agent.tools_impl._common import OUTPUT_DIR                       # noqa: F401
from agent.tools_impl.search import tool_search
from agent.tools_impl.calculate import tool_calculate
from agent.tools_impl.query_data import tool_query_data
from agent.tools_impl.write_docx import tool_write_docx
from agent.tools_impl.write_pptx import tool_write_pptx
from agent.tools_impl.write_xlsx import tool_write_xlsx
from agent.tools_impl.templates import find_template, TEMPLATE_FOR    # noqa: F401


TOOLS = {
    "search_documents": {
        "fn": tool_search,
        "changes_state": False,
        "args": "question (string)",
        "describe": lambda a: f"search the library for \"{a.get('question','')}\"",
        "help": "Find passages in the document library. Use this first, always.",
    },
    "calculate": {
        "fn": tool_calculate,
        "changes_state": False,
        "args": "expression (arithmetic only, e.g. \"(187+246+188+94)/4\")",
        "describe": lambda a: f"calculate {a.get('expression','')}",
        "help": "Do arithmetic exactly. Never compute in your head.",
    },
    "query_data": {
        "fn": tool_query_data,
        "changes_state": False,
        "args": "sql (a SELECT query against the tables listed above)",
        "describe": lambda a: f"query the data: {a.get('sql','')[:60]}",
        "help": ("Query the spreadsheets exactly with SQL. Use this for counts, "
                 "totals, averages and filters over tabular data - never search "
                 "for those, and never add them up yourself."),
    },
    "write_docx": {
        "fn": tool_write_docx,
        "changes_state": True,
        "args": "title (string), body (string), filename (optional)",
        "describe": lambda a: f"write {a.get('filename') or 'a Word document'}"
                              f" titled \"{a.get('title','')}\"",
        "help": "Produce a Word document such as an approval note or report.",
    },
    "write_pptx": {
        "fn": tool_write_pptx,
        "changes_state": True,
        "args": ('title (string), subtitle (string), '
                 'slides (list of {"heading": string, "bullets": [string]})'),
        "describe": lambda a: f"write {a.get('filename') or 'a presentation'}"
                              f" titled \"{a.get('title','')}\"",
        "help": ("Produce a PowerPoint deck, such as a board presentation or a "
                 "briefing. Give each slide a heading and three or four bullets."),
    },
    "write_xlsx": {
        "fn": tool_write_xlsx,
        "changes_state": True,
        "args": "title (string), headers (list), rows (list of lists)",
        "describe": lambda a: f"write {a.get('filename') or 'a spreadsheet'}",
        "help": "Produce a spreadsheet from tabular data.",
    },
}


def catalogue() -> str:
    """The tool list, as text for the model's prompt."""
    out = []
    for name, t in TOOLS.items():
        flag = "  [needs approval]" if t["changes_state"] else ""
        out.append(f"- {name}({t['args']}){flag}\n    {t['help']}")
    return "\n".join(out)
