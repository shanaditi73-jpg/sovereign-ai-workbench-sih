# AI Agent Module

This folder contains the AI + Agent layer of the Sovereign AI Workbench.

The agent is responsible for model selection, task planning, tool execution, and generating the final response.

## Architecture

```text
User Request
     ↓
Agent Planner
     ↓
Choose Action
     ↓
┌────────────┬─────────────┬──────────────┐
│  General   │ Calculator  │    Vision    │
│   Model    │    Tool     │    Model     │
└────────────┴─────────────┴──────────────┘
     ↓
Tool / Model Result
     ↓
Final LLM Response
```

## Components

### `config.py`
Stores the local model configuration.

Current models:

- General: `qwen2.5:3b`
- Coding: `qwen2.5-coder:3b`
- Vision: `qwen3-vl:4b`

### `models.py`
Handles communication with local Ollama models and routes requests to the appropriate model.

### `planner.py`
Uses the local LLM to determine which action is required:

- `GENERAL`
- `CALCULATOR`
- `VISION`

### `tools.py`
Contains tools that the agent can execute.

Currently implemented:

- Calculator

### `loop.py`
Runs the agent workflow:

```text
Request
   ↓
Planner
   ↓
Tool / Model
   ↓
Result
   ↓
Final Response
```

It also provides a `context` parameter for future integration with the RAG module.

## Running the Agent

From the project root:

```bash
python -m agent.test_models
```

To test the agent loop:

```bash
python -m agent.test_loop
```

## Requirements

The agent currently uses:

- Python
- Ollama
- Local Qwen models

Make sure Ollama is running and the required models are installed.

## RAG Integration

The agent is designed to work with the RAG module developed by the RAG/Multimodal team.

The intended interface is:

```python
run_agent(
    prompt=user_query,
    context=retrieved_context
)
```

The RAG implementation remains separate from this module.

The agent will use the retrieved context to generate the final response.

## Future Tools

The agent architecture can later be extended with tools such as:

- Document search
- File reading
- Code execution
- RAG retrieval
- Document generation
- Other task-specific tools

These should be integrated as independent tools rather than tightly coupling them to the agent loop.