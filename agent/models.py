import base64
import json
import urllib.request
import urllib.error

from .config import OLLAMA_BASE_URL, MODELS


def asks_for_code_or_calculation(prompt: str) -> bool:
    text = prompt.lower()

    code_keywords = [
        "write code",
        "write a program",
        "write python",
        "write java",
        "write javascript",
        "write c++",
        "code for",
        "program for",
        "implement",
        "debug",
        "algorithm",
        "function"
    ]

    calculation_keywords = [
        "calculate",
        "calculation",
        "compute",
        "equation",
        "formula",
        "solve",
        "percentage",
        "average",
        "sum",
        "multiply",
        "divide"
    ]

    for keyword in code_keywords:
        if keyword in text:
            return True

    for keyword in calculation_keywords:
        if keyword in text:
            return True

    return False


def call_ollama(model: str, prompt: str, images: list[str] | None = None) -> str:
    """
    Calls Ollama locally.
    No cloud API is used.
    """

    message = {
        "role": "user",
        "content": prompt
    }

    if images:
        encoded_images = []

        for image_path in images:
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(
                    image_file.read()
                ).decode("utf-8")

            encoded_images.append(image_data)

        message["images"] = encoded_images

    payload = {
        "model": model,
        "messages": [message],
        "stream": False
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/chat",
        data=data,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.loads(response.read().decode("utf-8"))

    return result["message"]["content"] or ""


def ask_model(
    prompt: str,
    images: list[str] | None = None
) -> tuple[str, str, str]:
    """
    Returns exactly:
        (answer, model_used, model_reason)

    Always three strings, always in that order.
    """

    # --------------------------------------------------
    # MODEL ROUTING
    # --------------------------------------------------

    if images:
        model = MODELS["vision"]
        model_reason = "image attached"

    elif asks_for_code_or_calculation(prompt):
        model = MODELS["coding"]
        model_reason = "calculation requested"

    else:
        model = MODELS["general"]
        model_reason = "text question"

    # --------------------------------------------------
    # CALL OLLAMA
    # --------------------------------------------------

    try:
        answer = call_ollama(
            model=model,
            prompt=prompt,
            images=images
        )

        return (
            answer,
            model,
            model_reason
        )

    except Exception as error:
        return (
            f"Local model error: {str(error)}",
            model,
            model_reason
        )
        