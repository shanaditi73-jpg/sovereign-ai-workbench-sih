def calculator(expression: str):
    """
    Safely evaluate basic mathematical expressions.
    """

    allowed = "0123456789+-*/().% "

    if not all(char in allowed for char in expression):
        return "Invalid mathematical expression."

    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception:
        return "Could not calculate the expression."
        