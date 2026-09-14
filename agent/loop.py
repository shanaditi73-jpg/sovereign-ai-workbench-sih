from .models import ask_model
from .tools import calculator
from .planner import create_plan


def extract_expression(prompt: str) -> str:
    expression = prompt.lower()

    prefixes = [
        "calculate",
        "compute",
        "what is",
        "solve"
    ]

    for prefix in prefixes:
        if expression.startswith(prefix):
            expression = expression[len(prefix):].strip()
            break

    return expression


def run_agent(prompt: str, images=None, context: str = ""):
    # -----------------------------------------
    # VISION
    # -----------------------------------------

    if images:
        answer, model, reason = ask_model(
            prompt=prompt,
            images=images
        )

        return {
            "answer": answer,
            "model": model,
            "reason": reason,
            "tool": "vision"
        }

    # -----------------------------------------
    # PLANNER
    # -----------------------------------------

    action = create_plan(prompt)

    # -----------------------------------------
    # CALCULATOR TOOL
    # -----------------------------------------

    if action == "CALCULATOR":

        expression = extract_expression(prompt)

        tool_result = calculator(expression)

        # Give the tool result back to the local LLM.
        final_prompt = f"""
You are the final response component of an AI agent.

The user asked:
{prompt}

The calculator tool returned:
{tool_result}

Using the tool result, give the user a clear and concise answer.

Do not recalculate the result yourself.
Do not mention internal agent architecture.
"""

        answer, model, _ = ask_model(final_prompt)

        return {
            "answer": answer,
            "model": model,
            "reason": "planner selected calculator",
            "tool": "calculator"
        }

    # -----------------------------------------
    # GENERAL MODEL
    # -----------------------------------------

    answer, model, reason = ask_model(
        prompt=prompt
    )

    return {
        "answer": answer,
        "model": model,
        "reason": reason,
        "tool": "none"
    }