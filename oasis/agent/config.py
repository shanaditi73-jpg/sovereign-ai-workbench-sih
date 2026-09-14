"""
MODEL CONFIGURATION.  Author: Aditi.

Model names live here and nowhere else. Swapping a model is a one-line edit to
this file - no logic changes anywhere in the agent.

Everything runs against a local Ollama. No cloud, no external calls.

If a model here is not pulled on the machine, ask_model falls back to the
general model rather than failing - see agent/models.py.
"""

OLLAMA_BASE_URL = "http://localhost:11434"

MODELS = {
    "general": "qwen3-vl:4b",
    "coding":  "qwen2.5-coder:3b",
    "vision":  "qwen3-vl:4b",
}
