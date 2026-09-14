from .models import ask_model


def create_plan(prompt: str) -> str:
    """
    Ask the local general model to decide what the agent should do.
    """

    planning_prompt = f"""
You are the planning component of a local AI agent.

User request:
{prompt}

Choose exactly ONE action:

GENERAL
Use this for normal questions.

CALCULATOR
Use this when an exact mathematical calculation is required.

VISION
Use this only when an image is provided.

Return ONLY one word:
GENERAL
CALCULATOR
VISION
"""

    answer, _, _ = ask_model(planning_prompt)

    action = answer.strip().upper()

    if "CALCULATOR" in action:
        return "CALCULATOR"

    if "VISION" in action:
        return "VISION"

    return "GENERAL"
    